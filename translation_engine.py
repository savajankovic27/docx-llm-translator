import zipfile
import os
import tempfile
from lxml import etree
import re
import shutil
from dotenv import load_dotenv
from openai import OpenAI
# from rds_utils import get_rds_terms as get_snowflake_terms, log_token_usage

# 1. SETUP
load_dotenv()
client = OpenAI(
    api_key=os.environ.get("OPENAI_API_KEY"), 
    base_url="https://llm.netlight.ai/v1"
)

# PROTECTED_TERMS = get_snowflake_terms()
PROTECTED_TERMS = [
    "Canada Development Investment Corporation", "CDEV", "CEI", "CEEFC", "CGF",
    "CGFIM", "CHHC", "CILGC", "CIC", "TMP Finance", "TMC", "IFRS", "GAAP",
    "IAS", "IASB", "ESG", "CEO", "CFO", "Trans Mountain Corporation",
    "Trans Mountain Pipeline", "Government of Canada", "16342451 CANADA INC."
] # TODO: restore from RDS
PROTECTED_WORDS = set()
NAMESPACE = {"w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main",
             "xml": "http://www.w3.org/XML/1998/namespace"}
EXCLUDED_FILES = {"styles.xml", "settings.xml", "fontTable.xml", "webSettings.xml"}
BATCH_SIZE = 5
W_NS = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"

def get_translatable_nodes(paragraph):
    """Returns only w:t nodes that are outside field characters (excludes page numbers, TOC fields etc.)"""
    in_field = 0
    text_nodes = []
    for elem in paragraph.iter():
        if elem.tag == f"{{{W_NS}}}fldChar":
            fld_type = elem.get(f"{{{W_NS}}}fldCharType")
            if fld_type == "begin":
                in_field += 1
            elif fld_type == "end":
                in_field -= 1
        elif elem.tag == f"{{{W_NS}}}t" and in_field == 0:
            text_nodes.append(elem)
    return text_nodes

# 2. TRANSLATION ENGINE
SEPARATOR = "|||"

def call_llm_batch(texts):
    joined = f"\n{SEPARATOR}\n".join(texts)
    try:
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": f"Professional Canadian-French translator. Rules: 1. Keep [PROT] terms, remove tag. 2. Formal. 3. Translate each segment separated by '{SEPARATOR}' and return them separated by '{SEPARATOR}' in the same order. Do not add or remove separators."},
                {"role": "user", "content": joined}
            ]
        )
        content = response.choices[0].message.content.strip()
        total_tokens = response.usage.total_tokens
        translations = [t.strip() for t in content.split(SEPARATOR)]
        # Fallback if count doesn't match
        if len(translations) != len(texts):
            print(f"Warning: expected {len(texts)} translations, got {len(translations)}")
            return texts, total_tokens
        return translations, total_tokens
    except Exception as e:
        print(f"API Error: {e}")
        return texts, 0

# 3. CORE LOGIC: BATCHED PARAGRAPHS
def process_paragraphs(paragraph_list, progress_callback=None):
    total_tokens = 0
    to_translate = []

    for para in paragraph_list:
        original_text = para["full_text"]

        # Skip if only protected words
        if original_text.upper() in PROTECTED_WORDS or any(original_text == t for t in PROTECTED_TERMS):
            continue

        # Tag protected terms
        tagged = original_text
        for term in PROTECTED_TERMS:
            pattern = re.compile(rf"\b({re.escape(term)})\b", re.IGNORECASE)
            tagged = pattern.sub(r"\1 [PROT]", tagged)

        to_translate.append((para, tagged))

    total_batches = max(1, -(-len(to_translate) // BATCH_SIZE))  # ceiling division

    # Send in batches instead of one call per paragraph
    for batch_idx, i in enumerate(range(0, len(to_translate), BATCH_SIZE)):
        batch = to_translate[i:i + BATCH_SIZE]
        texts = [tagged for _, tagged in batch]
        translations, tokens = call_llm_batch(texts)
        total_tokens += tokens
        for (para, _), translation in zip(batch, translations):
            translation = re.sub(r'\s*\[PROT\]', '', translation)
            inject_text(para["text_nodes"], translation)

        if progress_callback:
            progress_callback(batch_idx + 1, total_batches)

    return total_tokens

def _run_fmt_key(node):
    """Returns bold status of the run — the meaningful formatting boundary for distribution."""
    run = node.getparent()
    if run is None:
        return False
    rpr = run.find(f"{{{W_NS}}}rPr")
    if rpr is None:
        return False
    return rpr.find(f"{{{W_NS}}}b") is not None

def inject_text(nodes, translated_text):
    """
    Groups consecutive nodes by run formatting, distributes translated text
    proportionally at the group level (not per-node), snapping to word boundaries.
    Within each group the first node gets all the text, the rest are cleared.
    This prevents bold/color from bleeding across formatting boundaries.
    """
    if not nodes:
        return

    # Build formatting groups
    groups = []
    cur_nodes = [nodes[0]]
    cur_key = _run_fmt_key(nodes[0])
    for node in nodes[1:]:
        key = _run_fmt_key(node)
        if key == cur_key:
            cur_nodes.append(node)
        else:
            groups.append(cur_nodes)
            cur_nodes = [node]
            cur_key = key
    groups.append(cur_nodes)

    # Single formatting group — everything into first node, clear the rest
    if len(groups) == 1:
        nodes[0].text = translated_text
        if translated_text.startswith(" ") or translated_text.endswith(" "):
            nodes[0].set("{http://www.w3.org/XML/1998/namespace}space", "preserve")
        for node in nodes[1:]:
            node.text = ""
        return

    # Multiple groups — proportional distribution at group level, snapped to word boundary
    total_orig = sum(sum(len(n.text) for n in g if n.text) for g in groups) or 1
    cursor = 0
    for i, grp in enumerate(groups):
        if i == len(groups) - 1:
            content = translated_text[cursor:]
        else:
            grp_len = sum(len(n.text) for n in grp if n.text)
            cut = cursor + int(round(len(translated_text) * grp_len / total_orig))
            # Snap to nearest word boundary (forward or backward) to avoid splitting words
            fwd = cut
            while fwd < len(translated_text) and translated_text[fwd] not in (" ", "\n"):
                fwd += 1
            bwd = cut
            while bwd > cursor and translated_text[bwd - 1] not in (" ", "\n"):
                bwd -= 1
            cut = fwd if abs(fwd - cut) <= abs(cut - bwd) else bwd
            content = translated_text[cursor:cut]
            cursor = cut

        grp[0].text = content
        if content.startswith(" ") or content.endswith(" "):
            grp[0].set("{http://www.w3.org/XML/1998/namespace}space", "preserve")
        for node in grp[1:]:
            node.text = ""

# 4. PIPELINE
def run_pipeline(input_docx, output_docx, progress_callback=None):
    temp_dir = tempfile.mkdtemp()
    with zipfile.ZipFile(input_docx, 'r') as z:
        z.extractall(temp_dir)
    
    xml_files = []
    for r, _, fs in os.walk(os.path.join(temp_dir, "word")):
        for f in fs:
            if f.endswith(".xml") and f not in EXCLUDED_FILES and "theme" not in r:
                xml_files.append(os.path.join(r, f))
    
    trees = {}
    all_paras = []
    for f_path in xml_files:
        tree = etree.parse(f_path)
        trees[f_path] = tree
        for p in tree.xpath("//w:p", namespaces=NAMESPACE):
            nodes = get_translatable_nodes(p)
            if nodes:
                txt = "".join(n.text for n in nodes if n.text).strip()
                if txt: all_paras.append({"text_nodes": nodes, "full_text": txt})

    # Single pass processing to save $$$
    total_tokens = process_paragraphs(all_paras, progress_callback=progress_callback)
    # log_token_usage(total_tokens)  # TODO: restore when RDS is back
    print(f"Total tokens used: {total_tokens}")

    # Save XMLs using binary write to prevent corruption
    for path, tree in trees.items():
        with open(path, "wb") as f:
            f.write(etree.tostring(tree, xml_declaration=True, encoding="UTF-8", standalone="yes"))

    if os.path.exists(output_docx): os.remove(output_docx)
    with zipfile.ZipFile(output_docx, 'w', zipfile.ZIP_DEFLATED) as docx_zip:
        for root, _, files in os.walk(temp_dir):
            for f in files:
                abs_p = os.path.join(root, f)
                docx_zip.write(abs_p, os.path.relpath(abs_p, temp_dir))
    
    shutil.rmtree(temp_dir)
    print(f"Success! Output: {output_docx}")

if __name__ == "__main__":
    run_pipeline("document.docx", "document_translated.docx")
