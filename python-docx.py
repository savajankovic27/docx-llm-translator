import zipfile
import os
import tempfile
from lxml import etree
import re
import shutil
from dotenv import load_dotenv
from openai import OpenAI

from snowflake_utils import get_snowflake_terms, log_token_usage

#Setup 
load_dotenv()
api_key = os.environ.get("OPENAI_API_KEY")

# IMPORTANT: We point the client to the GitHub/Copilot inference endpoint
# This is why your previous attempt showed an error—the default was api.openai.com
# Updated for Netlight Codepilot
client = OpenAI(
    api_key=api_key, 
    base_url="https://llm.netlight.ai/v1" # Netlight's custom gateway
)
## PROTECTED TERMS HAS BEEN PHASED OUT. 
# Instead, we're using a dynamic fetch from Snowflake, which is more maintainable and scalable.

# PROTECTED_TERMS = [
#     "Canada Development Investment Corporation", "CDEV", "CEI", "CEEFC", 
#     "CGF", "CGFIM", "CHHC", "CILGC", "CIC", "TMP Finance", "TMC", "IFRS", 
#     "GAAP", "IAS", "IASB", "ESG", "CEO", "CFO", "Trans Mountain Corporation", 
#     "Trans Mountain Pipeline", "Government of Canada", "16342451 CANADA INC."
# ]

PROTECTED_TERMS = get_snowflake_terms()
# Protected words stay for the time being, still to be phased out
PROTECTED_WORDS = {"CANADA", "DEVELOPMENT", "INVESTMENT", "CORPORATION"}
NAMESPACE = {"w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main"}
EXCLUDED_FILES = {"styles.xml", "settings.xml", "fontTable.xml", "webSettings.xml"}

#Translation engine. 

#Ideally, in the future, this would be a more complex query, where the user would be able to change the prompt more easily and dynamically. For now, we keep it simple and hardcoded for the sake of the prototype.
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
            model="gpt-4o",
            messages=[{"role": "user", "content": prompt}]
        ) 
        # Capture total tokens (prompt + completion)
        tokens = response.usage.total_tokens 
        return response.choices[0].message.content.strip(), tokens
    except Exception as e:
        return text, 0
    
    # In the try statement, we return both the translated text, and the token count. 
    
    
    
#Processing Logic and Injection
def translate_chunk(paragraph_list):
    translated_results = []
    total_tokens_used = 0

    for para in paragraph_list:
        text = para["full_text"]

        # 1. Skip translation if the paragraph is just a protected term/word
        if text.upper() in PROTECTED_WORDS or any(text == term for term in PROTECTED_TERMS):
            translated_results.append(text)
            continue

        # 2. Tag protected terms
        tagged_text = text
        for term in PROTECTED_TERMS:
            pattern = re.compile(rf"\b({re.escape(term)})\b", re.IGNORECASE)
            tagged_text = pattern.sub(r"\1 [PROT]", tagged_text)

        # 3. Call LLM (Now returning text and tokens)
        french_translation, tokens = call_llm(tagged_text)
        translated_results.append(french_translation)
        total_tokens_used += tokens
            
    return translated_results, total_tokens_used

def inject_translated_chunk(chunk):
    """
    Re-injects text using Proportional Distribution to preserve bold/italics.
    """
    translated_paragraphs, total_tokens = translate_chunk(chunk)
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

    return total_tokens

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
    
    all_units = [] ## Run_Pipeline extracts text nodes into the flat list all_units. To batch by paragraph, we will modify the loop to keep text nodes group by their current paragraph. 
    trees = {}

    all_paragraphs = [] ## Paragraph list. 

    for f_path in xml_files:
        tree = etree.parse(f_path)
        trees[f_path] = tree
        for p in tree.getroot().xpath("//w:p", namespaces=NAMESPACE):
            nodes = p.xpath(".//w:t", namespaces=NAMESPACE) ## We use these as delimeters to split the paragraphs up. These paragraphs will be units that will be sent to the LLM calls, henceforth limiting the number of calls, and furthermore reducing costs. 
            if not nodes: continue
                
            full_txt = "".join(n.text for n in nodes if n.text).strip()

            if full_txt:
                all_paragraphs.append({
                    "text_nodes": nodes, 
                    "full_text": full_txt
                })


    # for f_path in xml_files:
    #     tree = etree.parse(f_path)
    #     trees[f_path] = tree
    #     for p in tree.getroot().xpath("//w:p", namespaces=NAMESPACE):
    #         nodes = p.xpath(".//w:t", namespaces=NAMESPACE)
    #         if not nodes: continue
    #         full_txt = "".join(n.text for n in nodes if n.text).strip()
    #         if full_txt:
    #             all_units.append({"text_nodes": nodes, "full_text": full_txt})

    # Process and Inject
    total_tokens = inject_translated_chunk(all_paragraphs)
    log_token_usage(total_tokens)
    print(f"Total tokens used: {total_tokens}")

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