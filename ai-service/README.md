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

## Record an admin document review

Copy `document_review_template.json`, fill in the document details, evidence, checklist results, reviewer, date, decision, and reason. The administrator must verify the evidence and choose the decision; this program only checks that the form is complete and that the chosen decision matches the checklist.

```powershell
python review_document.py "C:\path\to\completed-review.json"
```

The review record is saved as JSON under `data/document_reviews/`. `APPROVED` records eligibility under the repository policy; it does not certify medical accuracy. These records contain review metadata only: extracted text and vectors are not stored. Do not submit a document for indexing unless its saved review decision is `APPROVED`.

## Check approval before future indexing

The approval gate checks that the saved review decision is `APPROVED` and that the PDF/TXT file has the same SHA-256 hash recorded during review. A different or changed file is blocked until it has its own review. This command only checks eligibility; it does not extract text, create chunks, or index anything.

```powershell
python check_document_approval.py "C:\path\to\document.pdf" "..\data\document_reviews\document-id.json"
```

## Preview text chunks

After approval, the chunking command checks the approval gate, extracts text, and splits it into overlapping passages. The initial defaults are 250 words per passage and 40 shared words between neighboring passages; these are starting values to evaluate later, not a claim that they are optimal. Chunks stay in memory and are not saved or embedded.

```powershell
python chunk_document.py "C:\path\to\document.pdf" "..\data\document_reviews\document-id.json"
```

You can change the starting settings with `--chunk-size-words` and `--overlap-words`.
