# Fact Layer

A practice project for extracting grounded facts from PDFs and comparing their context. **Part 1 (phases 1–5) is complete.** Currently supports a responsive application shell, Documents/Facts/Comparisons navigation, and a real backend health check with retry. PDF upload, storage, extraction, and comparison are upcoming; dashes in the cards mean data is not available yet.

## Run locally

Requirements: Node.js 22.12+ (tested with 24.18), Python 3.13 (tested with 3.13.9).

### Backend — terminal 1

```sh
cd /Users/chayankbhargava/Projects/SuperJoin/backend
python3.13 -m venv .venv
.venv/bin/python -m pip install -r requirements.lock.txt
.venv/bin/python -m uvicorn app.main:app --host 127.0.0.1 --port 8018 --reload
```

On this machine Python 3.13 is at `/opt/anaconda3/bin/python3.13`; use that full path if `python3.13` is not on PATH. The existing `.venv` is already installed, so you can skip the first two setup commands when returning to this workspace.

### Frontend — terminal 2

```sh
cd /Users/chayankbhargava/Projects/SuperJoin/frontend
npm ci
npm run dev
```

Open http://127.0.0.1:5178. API health: http://127.0.0.1:8018/health. Interactive API docs: http://127.0.0.1:8018/docs. Stop each server with Ctrl+C in its terminal.

The dedicated ports avoid another project running on 5173. Strict port mode makes a collision explicit. To use another API address, copy frontend/.env.example to frontend/.env.local, change VITE_API_BASE_URL, and restart Vite. This value is public browser configuration, never a secret. If the frontend port changes, update the allowed origins in backend/app/main.py as well.

## Verify

```sh
cd frontend
npm run build
```

Then open the website with the backend running. Check the connected indicator, each navigation item, browser Back and refresh. Stop the backend and refresh to see the offline message; restart it and select Retry connection.

Verified in headless Chrome: live health/CORS, three views, disabled upload, Back/refresh, mobile navigation and no horizontal overflow at 390px, failed-request recovery, and no browser exceptions. Desktop/mobile screenshots were reviewed. This is a smoke check, not a full accessibility audit. No document processing tests exist because processing is not implemented yet.

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
backend/app/main.py            FastAPI health route and local CORS
```

Original reference PDFs and ZIP remain untouched and are ignored by Git. No database, model service, or credentials are needed for Part 1.
