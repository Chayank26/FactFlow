# Fact Layer

A practice project for extracting grounded facts from PDFs and comparing their context. **Part 2 is complete and Part 3 is in progress.** The app supports PDF upload and local storage, deterministic text extraction with evidence references, document management, and filtered cross-document comparisons. OCR for image-only PDFs and the fact-browser view remain planned.

## Run locally

Requirements: Node.js 22.12+ (tested with 24.18), Python 3.13 (tested with 3.13.9).

### Backend — terminal 1

```sh
cd /Users/chayankbhargava/Projects/FactFlow/backend
python3.13 -m venv .venv
.venv/bin/python -m pip install -r requirements.lock.txt
.venv/bin/python -m uvicorn app.main:app --host 127.0.0.1 --port 8019 --reload
```

On this machine Python 3.13 is at `/opt/anaconda3/bin/python3.13`; use that full path if `python3.13` is not on PATH. The existing `.venv` is already installed, so you can skip the first two setup commands when returning to this workspace.

### Frontend — terminal 2

```sh
cd /Users/chayankbhargava/Projects/FactFlow/frontend
npm ci
npm run dev
```

Open http://127.0.0.1:5179. API health: http://127.0.0.1:8019/health. Interactive API docs: http://127.0.0.1:8019/docs. Stop each server with Ctrl+C in its terminal.

The dedicated ports avoid another project running on 5173. Strict port mode makes a collision explicit. To use another API address, copy frontend/.env.example to frontend/.env.local, change VITE_API_BASE_URL, and restart Vite. This value is public browser configuration, never a secret. If the frontend port changes, update the allowed origins in backend/app/main.py as well.

## Verify

```sh
cd /Users/chayankbhargava/Projects/FactFlow/backend
.venv/bin/python -m pytest -q tests

cd ../frontend
npm run build
```

Then open the website with both servers running. Upload a PDF, inspect its extracted facts, reprocess or delete it, and open Comparisons to filter relationships by source and type. Check the connected indicator, each navigation item, browser Back and refresh. Stop the backend and refresh to see the offline message; restart it and select Retry connection.

The backend suite covers upload, PDF extraction, evidence references, document lifecycle, comparison filters, and failure paths. The frontend build is a compile-time check; browser interaction coverage remains a future improvement. This is not a full accessibility audit.

## Learning logs

- [direction.md](direction.md): why each phase's steps came at that point and how completion was verified.
- [flow.md](flow.md): user journey and data/request flow after each phase.
- [tech.md](tech.md): tool choices, alternatives, and trade-offs by phase.

AGENTS.md requires updates to all three files after every completed phase. Earlier entries remain as history; the latest entry describes current behavior.

## Structure

```text
frontend/src/App.tsx           Navigation and page shell
frontend/src/BackendStatus.tsx Health request, timeout, and retry
frontend/src/index.css         Responsive visual styling
backend/app/main.py            FastAPI API, SQLite storage, extraction, and comparisons
backend/tests/                  Focused backend regression tests
```

Original reference PDFs and ZIP remain untouched and are ignored by Git. Runtime SQLite data and uploaded files live under backend/data and are ignored by Git. No model service or credentials are needed for local development.
