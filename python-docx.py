import zipfile
import os
import tempfile
from lxml import etree
import re
import shutil
from dotenv import load_dotenv
from openai import OpenAI
from snowflake_utils import get_snowflake_terms, log_token_usage

# 1. SETUP
load_dotenv()
client = OpenAI(
    api_key=os.environ.get("OPENAI_API_KEY"), 
    base_url="https://llm.netlight.ai/v1"
)

PROTECTED_TERMS = get_snowflake_terms()
PROTECTED_WORDS = {"CANADA", "DEVELOPMENT", "INVESTMENT", "CORPORATION"}
NAMESPACE = {"w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main",
             "xml": "http://www.w3.org/XML/1998/namespace"}
EXCLUDED_FILES = {"styles.xml", "settings.xml", "fontTable.xml", "webSettings.xml"}

# 2. TRANSLATION ENGINE
def call_llm(text):
    # System/User structure reduces prompt overhead and cost
    prompt = f"System: Professional CA-FR translator for gov investment corp. Rules: 1. Keep [PROT] terms, remove tag. 2. Formal. 3. Translation ONLY.\nUser: {text}"
    try:
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[{"role": "user", "content": prompt}]
        ) 
        return response.choices[0].message.content.strip(), response.usage.total_tokens
    except Exception as e:
        print(f"API Error: {e}")
        return text, 0

# 3. CORE LOGIC: BATCHED PARAGRAPHS
def process_paragraphs(paragraph_list):
    total_tokens = 0
    for para in paragraph_list:
        original_text = para["full_text"]
        
        # Skip if only protected words
        if original_text.upper() in PROTECTED_WORDS or any(original_text == t for t in PROTECTED_TERMS):
            continue

        # Tag terms for AI
        tagged = original_text
        for term in PROTECTED_TERMS:
            pattern = re.compile(rf"\b({re.escape(term)})\b", re.IGNORECASE)
            tagged = pattern.sub(r"\1 [PROT]", tagged)

        translation, tokens = call_llm(tagged)
        total_tokens += tokens
        
        # Re-inject using whitespace preservation
        inject_text(para["text_nodes"], translation)
    
    return total_tokens

def inject_text(nodes, translated_text):
    """
    Distributes text while preserving 'xml:space=preserve' to prevent word sticking.
    """
    total_orig_len = sum(len(n.text) for n in nodes if n.text) or 1
    cursor = 0
    
    for i, node in enumerate(nodes):
        if not node.text and i < len(nodes) - 1: continue
        
        # Proportional slicing
        prop = len(node.text) / total_orig_len
        slice_len = int(round(len(translated_text) * prop))
        
        content = translated_text[cursor:] if i == len(nodes)-1 else translated_text[cursor:cursor+slice_len]
        node.text = content
        cursor += slice_len

        # CRITICAL: Preserve leading/trailing spaces in XML
        if content.startswith(" ") or content.endswith(" "):
            node.set("{http://www.w3.org/XML/1998/namespace}space", "preserve")

# 4. PIPELINE
def run_pipeline(input_docx, output_docx):
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
            nodes = p.xpath(".//w:t", namespaces=NAMESPACE)
            if nodes:
                txt = "".join(n.text for n in nodes if n.text).strip()
                if txt: all_paras.append({"text_nodes": nodes, "full_text": txt})

    # Single pass processing to save $$$
    total_tokens = process_paragraphs(all_paras)
    log_token_usage(total_tokens)
    print(f"Logged {total_tokens} tokens to Snowflake.")

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