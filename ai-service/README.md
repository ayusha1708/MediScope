# MediScope AI service

## Set up

From this folder, create and activate the Python environment, then install the listed dependencies:

```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

## Check and extract a document

```powershell
python process_document.py "C:\path\to\document.pdf"
python process_document.py "C:\path\to\document.txt"
```

The first document-processing step supports PDF and UTF-8 TXT files up to 25 MB. It checks the file and extracts selectable text. Scanned/image-only PDFs are reported as not extractable; OCR is not included. The command reports a character count and file hash, but does not save the extracted text, create embeddings, or add anything to ChromaDB.

Only process source files after their free-access and reuse terms have been reviewed under `docs/document-approval-policy.md`.
