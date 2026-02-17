# DOCX LLM Translator & Tagger

A Python engine designed to prepare complex Word documents for LLM translation. 

This tool specializes in preserving original document formatting while identifying trademarked terms and handling intricate branding layouts.

## Key Features

* **"Tag, don't Mask" Strategy**: Replaces risky placeholder injection with an in-place tagging system (e.g., `CDEV [PROT]`). This ensures the LLM recognizes protected terms without the risk of "stuck" placeholders or unmasking failures.
* **Proportional Styling Distribution**: Uses a custom algorithm to distribute processed text across original XML runs. This prevents "formatting flattening," ensuring that bold headers stay bold and normal text stays normal within the same paragraph.
* **Branding & Signature Intelligence**: Custom logic identifies stacked logo words and signature lines to prevent the accidental addition of translation markers (like `[FR]`) to corporate trademarks.
* **XML-Level Precision**: Operates directly on `word/document.xml`, `footers`, and `headers`. It intelligently skips `styles.xml` and `theme` files to maintain 100% theme integrity.

## Tech Stack

* **Python 3.10+**
* **lxml**: High-performance XML parsing for WordprocessingML.
* **Regex**: Sophisticated case-insensitive identification with word-boundary protection.

## Configuration

Customization is handled via two primary lists in the configuration section of the script:

* **`PROTECTED_TERMS`**: Legal entity names or acronyms that should remain unchanged (e.g., "Canada Development Investment Corporation", "IFRS").
* **`PROTECTED_WORDS`**: Individual components of logo blocks used for stacked layouts.

## Usage

1.  **Install Dependencies**:
    ```bash
    pip install lxml
    ```
2.  **Setup**: Place your source file named `document.docx` in the root directory.
3.  **Run**:
    ```bash
    python main.py
    ```
4.  **Output**: The tagged and style-preserved file will be generated as `document_translated.docx`.

## Workflow Logic

1.  **Extract**: The `.docx` archive is unzipped into a temporary directory.
2.  **Parse**: Content is grouped into `w:p` units, maintaining references to all underlying `w:t` nodes.
3.  **Tag**: 
    * Logic checks for logo/trademark-only paragraphs to skip marking.
    * Sentences are scanned for protected terms and tagged with `[PROT]`.
    * The `[FR]` marker is appended to signal required translation.
4.  **Inject**: The engine calculates the character ratio of original runs and slices the new text accordingly to maintain bolding/italics.
5.  **Rebuild**: XML trees are serialized and the directory is re-zipped into a valid Word archive.