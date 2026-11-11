# MediScope

MediScope is an academic project for exploring medical document screening, searchable evidence, and source-grounded answers. It is an educational information system, not a diagnostic or treatment tool.

## How we will build it

We will implement this project in small, reviewable steps. Each step should leave us with something understandable and working before we add the next part. The AI screening process can help a human reviewer, but document approval remains a human decision.

## Project areas

- `frontend/` — user and administrator screens.
- `backend/` — accounts, permissions, document submissions, review decisions, and application APIs.
- `ai-service/` — Python code for ML, document processing, retrieval, and answer generation.
- `data/uploads/` — local copies of submitted source files during development. These files are excluded from Git.
- `data/chroma/` — persistent local ChromaDB data when vector indexing is implemented. This data is excluded from Git.
- `docs/` — architecture decisions, approval criteria, and project notes.

The folders are an agreed outline. We will add code and dependencies only as we reach the relevant implementation step.

## First AI dependency

`ai-service/requirements.txt` currently lists only scikit-learn, which we will need for the first query-classification milestone. More packages will be added only when a later step needs them.

To create a Python virtual environment and install the current AI-service dependencies from the repository root:

```powershell
py -m venv ai-service/.venv
ai-service/.venv/Scripts/Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r ai-service/requirements.txt
```

## Git basics

From this folder, use `git status` to see what changed. After reviewing changes, use `git add <file-or-folder>` and `git commit -m "Describe the change"` to save a local checkpoint. Never commit passwords, API keys, private documents, or local database files.

A GitHub remote has not been connected yet. We will connect this local repository to a private GitHub repository once the initial files and repository visibility are confirmed.
