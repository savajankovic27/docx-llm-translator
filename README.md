# DocTranslate

A full-stack application that translates `.docx` Word documents from English to Canadian French using GPT-4o, while preserving the original document's formatting with XML-level precision.

---

## What It Does

Upload a `.docx` file through the web interface. The engine translates every paragraph of body text, headers, and footers into Canadian French, then returns a translated `.docx` that is structurally identical to the original — same fonts, same bold/italic/colour styling, same layout. A side-by-side PDF preview lets you visually compare the original and translated documents before downloading.

Certain terms (legal entity names, acronyms, financial standards) are protected and left untranslated. The LLM is instructed to recognise and preserve them.

---

## Architecture

```
frontend/        React + Vite + Tailwind — upload UI, split-pane PDF preview
backend/
  main.py        FastAPI server — job queue, file handling, PDF conversion
translation_engine.py   Core XML processing and LLM translation logic
```

The frontend communicates with the FastAPI backend over HTTP. Translation jobs run as background tasks so the server stays responsive. The frontend polls `/status/{job_id}` every 2 seconds and displays a progress bar during processing.

---

## How the Translation Engine Works

### DOCX as a ZIP Archive

A `.docx` file is a ZIP archive. Inside it, `word/document.xml` contains the document body, alongside `word/header1.xml`, `word/footer1.xml`, etc. The engine extracts all of these, processes them, then re-zips the directory into a valid Word file. Files like `styles.xml`, `fontTable.xml`, and `theme/` directories are skipped entirely — touching them would corrupt the visual theme.

### WordprocessingML XML Structure

Word documents use the **WordprocessingML** (OOXML) schema. The key elements are:

| Element | Meaning |
|---|---|
| `w:p` | Paragraph — the top-level unit of text |
| `w:r` | Run — a contiguous span of text with uniform formatting |
| `w:t` | Text node — holds the actual string content |
| `w:rPr` | Run Properties — contains all formatting for the run |

A paragraph with mixed formatting (e.g. a bold coloured label followed by normal body text) looks like this in XML:

```xml
<w:p>
  <w:r>
    <w:rPr>
      <w:b/>
      <w:bCs/>
      <w:color w:val="0F4761" w:themeColor="accent1"/>
    </w:rPr>
    <w:t>Strategic Priority:</w:t>
  </w:r>
  <w:r>
    <w:rPr/>
    <w:t xml:space="preserve"> deliver value across the portfolio.</w:t>
  </w:r>
</w:p>
```

The engine collects all `w:t` nodes within a paragraph, strips their text, sends it for translation, then writes the translated text back — without touching `w:rPr` at all, so formatting is never modified.

### Field Character Exclusion

Paragraphs can contain **field characters** (`w:fldChar`) which wrap dynamic content like page numbers, table-of-contents entries, and cross-references. The engine tracks `fldCharType="begin"` and `fldCharType="end"` markers and skips any `w:t` nodes found between them. Translating field instructions would corrupt the document structure.

### Formatting Groups and Text Distribution

The central challenge is that a single translated string must be distributed back across multiple `w:r` runs with different formatting. The engine:

1. Groups consecutive `w:t` nodes by their parent run's complete `w:rPr` fingerprint — a tuple of every formatting child element and its attributes. Two runs are only in the same group if their formatting is byte-for-byte identical.
2. For paragraphs with a **single formatting group**, the translated text goes entirely into the first `w:t` node and all others are cleared.
3. For **multiple formatting groups** (e.g. bold label + normal body), the engine detects whether the original group ends with a colon (`:`) and uses the colon position in the translated text as the split point — this reliably handles the common `Bold label: normal body` bullet pattern. For other cases it falls back to a character-ratio proportional split snapped to the nearest word boundary.

### Protected Terms

Terms that must remain in English (legal entity names, acronyms, financial standards) are tagged in-place before the LLM call:

```
Canada Development Investment Corporation [PROT] was established...
```

The LLM is instructed to keep tagged terms verbatim and remove the `[PROT]` marker. After translation, any remaining `[PROT]` tags are stripped by regex as a safety net.

### Batched LLM Calls

Paragraphs are sent to GPT-4o in batches of 5, joined by a `|||` separator. The model returns translations in the same format. If the number of returned segments doesn't match the input, the original text is used as a fallback for that batch to prevent data loss.

---

## Running Locally

### Prerequisites

- Python 3.10+
- Node.js 18+
- Microsoft Word (macOS) — required for PDF preview only
- An OpenAI-compatible API key

### 1. Clone and set up the Python environment

```bash
git clone <repo-url>
cd Mini-project
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requriements.txt
pip install fastapi "uvicorn[standard]" python-multipart docx2pdf
```

### 2. Configure environment variables

Create a `.env` file in the project root:

```
OPENAI_API_KEY=your_api_key_here
```

The engine defaults to `https://llm.netlight.ai/v1` as the API base URL. To use OpenAI directly, open `translation_engine.py` and remove the `base_url` argument from the `OpenAI(...)` client constructor.

### 3. Start the backend

```bash
source venv/bin/activate
uvicorn backend.main:app --reload
```

The API will be available at `http://localhost:8000`.

### 4. Start the frontend

```bash
cd frontend
npm install
npm run dev
```

The UI will be available at `http://localhost:5173`.

### 5. Translate a document

Open `http://localhost:5173`, drag and drop a `.docx` file, and wait for the translation to complete. The progress bar updates in real time. When done, use the **Download** button to save the translated `.docx`.

---

## Configuration

| Variable | Location | Purpose |
|---|---|---|
| `OPENAI_API_KEY` | `.env` | API key for the LLM |
| `PROTECTED_TERMS` | `translation_engine.py` | Terms to leave untranslated |
| `BATCH_SIZE` | `translation_engine.py` | Paragraphs per LLM call (default: 5) |
| `EXCLUDED_FILES` | `translation_engine.py` | XML files to skip during processing |
