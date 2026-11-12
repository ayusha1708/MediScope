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

The first document-processing step supports PDF and UTF-8 TXT files up to 25 MB. It checks the file and extracts selectable text page by page. A conservative preprocessing step normalizes Unicode and whitespace and removes soft hyphens/control characters; it does not strip headers, references, or medical terms. Scanned/image-only PDFs are reported as not extractable; OCR is not included. The command reports a character count and file hash, but does not save the extracted text or create an index.

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

After approval, the chunking command checks the approval gate, extracts text page by page, and splits each page into overlapping passages. Each PDF passage keeps its source page number; TXT passages have no page number. The initial defaults are 250 words per passage and 40 shared words between neighboring passages on the same page; these are starting values to evaluate later, not a claim that they are optimal. Chunks stay in memory and are not saved or embedded.

```powershell
python chunk_document.py "C:\path\to\document.pdf" "..\data\document_reviews\document-id.json"
```

You can change the starting settings with `--chunk-size-words` and `--overlap-words`.

## Create local TF-IDF vectors

The vectorization step uses scikit-learn, which is already in `requirements.txt`. It builds a vocabulary from approved page-aware chunks and gives each chunk a sparse vector of term weights. A search query must later use the same fitted vocabulary and weights. TF-IDF matches terms and short phrases; it is not a neural embedding model and will not understand synonyms as well. It creates the vectors locally and does not save them yet.

```powershell
python vectorize_document.py "C:\path\to\document.pdf" "..\data\document_reviews\document-id.json"
```

## Save the local index

After reviewing the in-memory vector counts, build the persistent local index:

```powershell
python index_document.py "C:\path\to\document.pdf" "..\data\document_reviews\document-id.json"
```

The index is saved under `data/tfidf_index/<document-id>/`. It contains `vectorizer.joblib` (the fitted vocabulary and term weights), `vectors.npz` (the sparse chunk vectors), and `chunks.json` (chunk text, page numbers, and citation metadata). This generated index is local and ignored by Git. Add all approved documents to one shared TF-IDF vocabulary in a later corpus-indexing step before comparing retrieval scores across documents.

## Search for relevant passages

After saving an index, search it by document ID and question:

```powershell
python search_document.py "document-id" "What symptoms does the article describe?"
```

The command prints the three closest passages, their source page numbers, and TF-IDF cosine similarity scores from 0 to 1. It transforms the question with the same saved vectorizer used for the passage vectors, then ranks by cosine similarity. Scores measure word overlap, not medical certainty. This command retrieves evidence only.

## Generate an answer with local Ollama

Install Ollama for Windows, then download a local model once:

```powershell
ollama pull qwen3:4b
ollama list
```

Ollama runs locally at `http://localhost:11434`. MediScope calls its `/api/chat` endpoint using Python's standard library, so no extra Python package or API key is required. Keep Ollama running while asking questions. The model name and local address can be configured in the current PowerShell session:

```powershell
$env:OLLAMA_MODEL = "qwen3:4b"
$env:OLLAMA_BASE_URL = "http://localhost:11434"
```

From this `ai-service` folder, ask a question using the approved document's ID:

```powershell
python ask_document.py "PMC12560063" "What does the article say about medical education?"
```

The command shows all three closest references with their document title, page, passage ID, similarity score, source, and a short excerpt. It then asks Ollama to combine relevant information into a plain-language answer that is as long as needed to fully answer the question, without padding or repetition. The answer cites references as `[R1]`, `[R2]`, or `[R3]`; MediScope maps each marker to the actual retrieved passage. It will not force an irrelevant passage into the answer. If evidence is insufficient, no passage matches, Ollama returns an invalid citation, or the service is unavailable, the command shows a safe fallback while keeping the references visible. Scores measure word overlap, not answer confidence. This grounding reduces unsupported answers but cannot guarantee the model is always correct; verify the cited passage in the source.

No API keys are used for local Ollama. If configuration is needed again in a new PowerShell window, set the two environment variables there too. Never put credentials in frontend code or commit them to Git.
