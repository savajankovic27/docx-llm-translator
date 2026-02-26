import zipfile
import os
import tempfile
from lxml import etree
import re
import shutil
from dotenv import load_dotenv
from openai import OpenAI

# 1. SETUP & CONFIGURATION
# This loads your key from the .env file you created
load_dotenv()
api_key = os.environ.get("OPENAI_API_KEY")

# IMPORTANT: We point the client to the GitHub/Copilot inference endpoint
# This is why your previous attempt showed an error—the default was api.openai.com
# Updated for Netlight Codepilot
client = OpenAI(
    api_key=api_key, 
    base_url="https://llm.netlight.ai/v1" # Netlight's custom gateway
)
# ... [The rest of the PROTECTED_TERMS and pipeline logic follows] ...

PROTECTED_TERMS = [
    "Canada Development Investment Corporation", "CDEV", "CEI", "CEEFC", 
    "CGF", "CGFIM", "CHHC", "CILGC", "CIC", "TMP Finance", "TMC", "IFRS", 
    "GAAP", "IAS", "IASB", "ESG", "CEO", "CFO", "Trans Mountain Corporation", 
    "Trans Mountain Pipeline", "Government of Canada", "16342451 CANADA INC."
]

PROTECTED_WORDS = {"CANADA", "DEVELOPMENT", "INVESTMENT", "CORPORATION"}
NAMESPACE = {"w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main"}
EXCLUDED_FILES = {"styles.xml", "settings.xml", "fontTable.xml", "webSettings.xml"}

# 2. AI TRANSLATION ENGINE (Targeting GPT-4o via Copilot)
def call_llm(text):
    prompt = f"""
    You are a professional translator for a Canadian government investment corporation.
    Translate the following English text into professional Canadian French.
    STRICT RULES:
    1. Any word or phrase immediately followed by "[PROT]" is a protected trademark. Keep the word EXACTLY as it is, but REMOVE the "[PROT]" tag in the final output.
    2. Maintain a formal, institutional tone.
    3. Output ONLY the translated text. No commentary.

    TEXT:
    {text}
    """
    try:
        response = client.chat.completions.create(
        model="gpt-4o", # OR try "openai/gpt-4o" if plain "gpt-4o" fails
        messages=[{"role": "user", "content": prompt}]
        ) 
        return response.choices[0].message.content.strip()
    except Exception as e:
        print(f"AI Translation Error: {e}")
        return text + " [TRANSLATION_FAILED]"

# 3. PROCESSING LOGIC
def translate_chunk(chunk):
    translated = []
    for pu in chunk:
        text = pu["full_text"]
        text_stripped = text.strip()

        # Handle logo words & protected terms without AI
        if text_stripped.upper() in PROTECTED_WORDS or any(text_stripped == term for term in PROTECTED_TERMS):
            translated.append(text)
            continue

        # Tag protected terms for the AI
        tagged_text = text
        for term in PROTECTED_TERMS:
            pattern = re.compile(rf"\b({re.escape(term)})\b", re.IGNORECASE)
            tagged_text = pattern.sub(r"\1 [PROT]", tagged_text)

        # Call the AI
        french_translation = call_llm(tagged_text)
        
        # WE REMOVE THE + " [FR]" HERE
        # The AI already removes [PROT] based on our prompt instructions
        translated.append(french_translation) 
            
    return translated

def inject_translated_chunk(chunk):
    """
    Re-injects text using Proportional Distribution to preserve bold/italics.
    """
    translated_paragraphs = translate_chunk(chunk)
    for pu, translated_text in zip(chunk, translated_paragraphs):
        text_nodes = pu["text_nodes"]
        if not text_nodes: continue

        original_lengths = [len(node.text) if node.text else 0 for node in text_nodes]
        total_chars = sum(original_lengths)
        
        if total_chars == 0:
            text_nodes[0].text = translated_text
            continue

        cursor = 0
        for i, node in enumerate(text_nodes):
            proportion = original_lengths[i] / total_chars
            slice_len = int(round(len(translated_text) * proportion))
            if i == len(text_nodes) - 1:
                node.text = translated_text[cursor:]
            else:
                node.text = translated_text[cursor:cursor + slice_len]
                cursor += slice_len

# 4. FILE & PIPELINE MANAGEMENT
def run_pipeline(input_docx, output_docx):
    # Setup temp workspace
    temp_dir = tempfile.mkdtemp()
    with zipfile.ZipFile(input_docx, 'r') as zip_ref:
        zip_ref.extractall(temp_dir)
    
    # Collect all text-bearing XMLs (Body, Footers, Headers)
    xml_files = []
    for root, _, files in os.walk(os.path.join(temp_dir, "word")):
        for f in files:
            if f.endswith(".xml") and f not in EXCLUDED_FILES and "theme" not in root:
                xml_files.append(os.path.join(root, f))
    
    all_units = []
    trees = {}
    for f_path in xml_files:
        tree = etree.parse(f_path)
        trees[f_path] = tree
        for p in tree.getroot().xpath("//w:p", namespaces=NAMESPACE):
            nodes = p.xpath(".//w:t", namespaces=NAMESPACE)
            if not nodes: continue
            full_txt = "".join(n.text for n in nodes if n.text).strip()
            if full_txt:
                all_units.append({"text_nodes": nodes, "full_text": full_txt})

    # Process and Inject
    inject_translated_chunk(all_units)

    # Save XMLs back to disk
    for path, tree in trees.items():
        tree.write(path, xml_declaration=True, encoding="UTF-8", standalone="yes")

    # Re-package DOCX
    if os.path.exists(output_docx): os.remove(output_docx)
    with zipfile.ZipFile(output_docx, 'w', zipfile.ZIP_DEFLATED) as docx_zip:
        for foldername, _, filenames in os.walk(temp_dir):
            for filename in filenames:
                f_path = os.path.join(foldername, filename)
                docx_zip.write(f_path, os.path.relpath(f_path, temp_dir))
    
    shutil.rmtree(temp_dir)
    print(f"Translation Complete! File saved: {output_docx}")

if __name__ == "__main__":
    run_pipeline("document.docx", "document_translated.docx")