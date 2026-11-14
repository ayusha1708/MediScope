# MediScope frontend

This is a small browser interface built with plain HTML, CSS, and JavaScript. It does not need Node.js, npm, React, or a separate frontend server.

## Run it

Start the FastAPI backend using the setup instructions in `backend/README.md`, then open:

```text
http://127.0.0.1:8000/
```

FastAPI serves these files from this folder and the API from the same address. Keeping them on one origin lets the browser use the backend's signed login cookie without extra CORS configuration.

## What the screens do

- **Sign in / Create account:** registers regular users and signs in existing accounts. Admin accounts are created separately by the backend command.
- **Ask a question:** sends only the question to `POST /api/questions`, then displays the generated answer, fallback/safety status, and the retrieved references with page, passage, source, excerpt, and similarity score.
- **Submit a document:** sends a PDF or TXT file for review. The user explicitly chooses whether the admin sees their identity or sees “Anonymous.” The backend keeps the submission privately linked to the user's account either way.
- **My submissions:** shows the signed-in user's submission status and any decision reason.
- **Admin review:** shown only to admins. It shows dashboard counts, an admin queue, the original upload, submitter identity choice, and a review form. Full metadata and evidence are required to approve; the form converts three understandable review groups into the six checks expected by the existing backend. Only approval sends the file through extraction, chunking, and indexing.

The frontend displays server errors as messages and uses text-only DOM updates for answers, excerpts, and metadata.
