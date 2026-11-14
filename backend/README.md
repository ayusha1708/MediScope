# MediScope backend

The API exposes health, authentication, question, user document-submission, and admin review-queue routes. The question route calls the same reusable safety, classifier, MongoDB retrieval, and Ollama service as `ai-service/answer_question.py`; retrieval logic is not copied into the API. Authentication uses MongoDB accounts and a signed HttpOnly session cookie. Passwords are stored as scrypt hashes, never as plain text.

Regular users can submit readable PDF/TXT files (up to 25 MB). The original file is stored in MongoDB GridFS, and a metadata record is added to `document_submissions` with `PENDING_ADMIN_REVIEW`. Submission only checks file type, size, and technical readability; it does not approve, chunk, vectorize, or make the file searchable. On upload, the user must choose whether to reveal their name and email to admins or appear as anonymous. Anonymous submissions remain privately linked to the signed-in account so the user can track their status, but admin API responses show them as `Anonymous`. An admin can inspect submission details and download the original for review. The admin decision route validates the existing review checklist. Only an `APPROVED` record proceeds to the existing extraction, page-aware chunking, approved catalog storage, and a refreshed shared TF-IDF index.

## Install and run locally

Use the separate Python 3.12 backend environment so the earlier Windows policy issue in the Python 3.14 environment does not affect the API. It installs the AI service requirements too, so both use the same MongoDB and Ollama code. From the project root:

```powershell
py -3.12 -m venv .\backend\.venv
.\backend\.venv\Scripts\Activate.ps1
python -m pip install -r .\ai-service\requirements.txt -r .\backend\requirements.txt
Set-Location .\backend
python -m uvicorn mediscope_api.main:app --reload --host 127.0.0.1 --port 8000
```

Open `http://127.0.0.1:8000/` for the MediScope browser interface, or `http://127.0.0.1:8000/docs` for the interactive API page. The plain HTML/CSS/JavaScript frontend lives in `frontend/` and is served by FastAPI from the same origin. It needs no Node.js or npm setup. This development server is bound to the local computer. Authentication is required for question and document-submission requests. The API is still a local development service; keep it bound to 127.0.0.1 for now.

## Routes

- `GET /health` returns the API process status.
- `POST /api/auth/register` creates a regular user account. Public registration cannot set the role.
- `POST /api/auth/login` signs in an account and sets the session cookie.
- `POST /api/auth/logout` clears the session.
- `GET /api/auth/me` returns the signed-in account and role.
- `POST /api/documents/submissions` requires a signed-in user and multipart fields `file`, `title`, `reveal_identity` (`true` or `false`), optional `source_url`, and optional `scope_reason`. `false` shows the user as Anonymous to admins while preserving the private account link for status tracking. It returns a pending submission ID and basic extraction details.
- `GET /api/documents/submissions` lists only the signed-in user's submissions and review status.
- `GET /api/admin/dashboard` returns protected document, submission, user, passage, and index counts.
- `GET /api/admin/document-submissions?status=PENDING_ADMIN_REVIEW` lists submissions for the signed-in admin.
- `GET /api/admin/document-submissions/{submission_id}` shows one submission record.
- `GET /api/admin/document-submissions/{submission_id}/file` downloads the original submission for admin inspection.
- `POST /api/admin/document-submissions/{submission_id}/decision` accepts the existing JSON review-record shape. The server supplies the signed-in admin ID, review date, and actual uploaded-file hash. `APPROVED` requires the complete checklist and document metadata; `NEEDS_REVISION` and `REJECTED` follow the existing checklist rules.
- `POST /api/questions` requires a signed-in account and accepts JSON such as `{"question":"What are the three key areas to consider when evaluating OERs?"}` and returns the classifier route, answer, references, scores, and fallback/safety flags. Optionally include `document_id` to restrict retrieval.

## Create the first administrator

The first admin is created from the backend command line, not public registration. From the project root, with the backend virtual environment active:

```powershell
Set-Location .\backend
python -m mediscope_api.create_admin
```

The command asks for the email and password without echoing the password. It never promotes an existing regular user. Admin-only dashboard and review-queue routes are available after sign-in.

## Session secret

Add a private, random `MEDISCOPE_SESSION_SECRET` line to `ai-service/.env`. From the `backend` folder, you can create and append one without displaying it:

```powershell
$sessionSecret = python -c "import secrets; print(secrets.token_urlsafe(48))"
Add-Content -LiteralPath ..\ai-service\.env -Value "MEDISCOPE_SESSION_SECRET=$sessionSecret"
Remove-Variable sessionSecret
```

If the setting is missing, a temporary secret is generated and existing sessions stop working when the API restarts. The real value belongs in the ignored `.env`, never in Git.

MongoDB Atlas and local Ollama must be reachable, and the query-classifier model must exist under `ai-service/models/`.
