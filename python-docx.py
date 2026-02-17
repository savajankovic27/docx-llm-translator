import zipfile
import os
import tempfile
from lxml import etree
import re
import shutil

# 1. Configuration & Protected Terms
# These are official names and acronyms that must remain exactly as-is [cite: 715-747, 860-880].
PROTECTED_TERMS = [
    "Canada Development Investment Corporation", "CDEV", "CEI", "CEEFC", 
    "CGF", "CGFIM", "CHHC", "CILGC", "CIC", "TMP Finance", "TMC", "IFRS", 
    "GAAP", "IAS", "IASB", "ESG", "CEO", "CFO", "Trans Mountain Corporation", 
    "Trans Mountain Pipeline", "Government of Canada", "16342451 CANADA INC."
]

# Words that make up the logo block on the first page [cite: 638-641].
PROTECTED_WORDS = {"CANADA", "DEVELOPMENT", "INVESTMENT", "CORPORATION"}

NAMESPACE = {"w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main"}
EXCLUDED_FILES = {"styles.xml", "settings.xml", "fontTable.xml", "webSettings.xml"}

# 2. Translation & Tagging Logic
def translate_chunk(chunk):
    """
    Identifies protected terms, tags them with [PROT], 
    and adds the [FR] marker to the paragraph .
    """
    translated = []
    for pu in chunk:
        text = pu["full_text"]
        text_stripped = text.strip()

        # A. Handle stacked logo word protection (Return original exactly)
        if text_stripped.upper() in PROTECTED_WORDS:
            translated.append(text)
            continue

        # B. Handle Trademark-only lines (e.g., in footers/signatures)
        # If the whole paragraph is just the company name, don't add [FR]
        if any(text_stripped == term for term in PROTECTED_TERMS):
            translated.append(text)
            continue

        # C. Tag protected terms within mixed paragraphs
        tagged_text = text
        for term in PROTECTED_TERMS:
            # Captures the word and adds [PROT] while maintaining original casing
            pattern = re.compile(rf"\b({re.escape(term)})\b", re.IGNORECASE)
            tagged_text = pattern.sub(r"\1 [PROT]", tagged_text)

        # D. Append [FR] marker to indicate 'To be translated'
        final_text = tagged_text + " [FR]"
        translated.append(final_text)
    return translated

def inject_translated_chunk(chunk):
    """
    Distributes text back into original runs proportionally to preserve styles like bolding .
    """
    translated_paragraphs = translate_chunk(chunk)

    for pu, translated_text in zip(chunk, translated_paragraphs):
        text_nodes = pu["text_nodes"]
        if not text_nodes:
            continue

        # Calculate original character counts to maintain ratio of formatting runs
        original_lengths = [len(node.text) if node.text else 0 for node in text_nodes]
        total_original_chars = sum(original_lengths)

        if total_original_chars == 0:
            text_nodes[0].text = translated_text
            continue

        # Distribute the tagged/translated text across existing XML nodes
        cursor = 0
        for i, node in enumerate(text_nodes):
            proportion = original_lengths[i] / total_original_chars
            slice_length = int(round(len(translated_text) * proportion))

            if i == len(text_nodes) - 1:
                # Ensure the last node gets everything remaining
                node.text = translated_text[cursor:]
            else:
                node.text = translated_text[cursor:cursor + slice_length]
                cursor += slice_length

# 3. XML & File Handling
def extract_docx(docx_path):
    temp_dir = tempfile.mkdtemp()
    with zipfile.ZipFile(docx_path, 'r') as zip_ref:
        zip_ref.extractall(temp_dir)
    return temp_dir

def collect_content_xml_files(root_dir):
    word_dir = os.path.join(root_dir, "word")
    xml_files = []
    for root, dirs, files in os.walk(word_dir):
        for file in files:
            # Process main body, headers, footers, but skip styles and theme [cite: 715-747].
            if file.endswith(".xml") and file not in EXCLUDED_FILES and "theme" not in root:
                xml_files.append(os.path.join(root, file))
    return xml_files

def extract_paragraph_units(xml_path):
    tree = etree.parse(xml_path)
    root = tree.getroot()
    paragraphs = root.xpath("//w:p", namespaces=NAMESPACE)
    units = []
    for p in paragraphs:
        text_nodes = p.xpath(".//w:t", namespaces=NAMESPACE)
        if not text_nodes: continue
        full_text = "".join(node.text for node in text_nodes if node.text).strip()
        if not full_text: continue
        units.append({"xml_path": xml_path, "text_nodes": text_nodes, "full_text": full_text})
    return tree, units

# 4. Main Execution Pipeline
def run_pipeline(input_docx, output_docx):
    temp_dir = extract_docx(input_docx)
    xml_files = collect_content_xml_files(temp_dir)
    
    all_units = []
    trees = {}

    # Step 1: Extract text units and store XML trees in memory
    for xml_file in xml_files:
        tree, units = extract_paragraph_units(xml_file)
        trees[xml_file] = tree
        all_units.extend(units)

    # Step 2: Tag and Re-inject (Styles are preserved via proportional slicing)
    inject_translated_chunk(all_units)

    # Step 3: Write modified XML back to temp folder
    for xml_path, tree in trees.items():
        tree.write(xml_path, xml_declaration=True, encoding="UTF-8", standalone="yes")

    # Step 4: Final Re-zip into new DOCX
    if os.path.exists(output_docx): os.remove(output_docx)
    with zipfile.ZipFile(output_docx, 'w', zipfile.ZIP_DEFLATED) as docx_zip:
        for foldername, subfolders, filenames in os.walk(temp_dir):
            for filename in filenames:
                f_path = os.path.join(foldername, filename)
                docx_zip.write(f_path, os.path.relpath(f_path, temp_dir))
    
    shutil.rmtree(temp_dir)
    print(f"Refactor complete! File saved as {output_docx}")

# Execute the pipeline
run_pipeline("document.docx", "document_translated.docx")