# Direction log

Updated after every completed phase. Current milestone: Part 1 complete (phases 1–5). Current local ports: frontend 5179, API 8019.

## Part 2 planning checkpoint

We are starting Part 2 with a phased approach so each build step stays small and reviewable. Planned phases and goals:

- Phase 6 — SQLite document records and upload API scaffolding.
- Phase 7 — Document list and metadata screen in the browser.
- Phase 8 — PDF extraction and fact storage grounded in evidence.
- Phase 9 — Comparison workflow and context-aware summary experience.

This pause is intentional: after each phase we will update the three learning logs, verify the change, and stop so the user can review the progress before continuing to the next stage.

## Phase 6 — SQLite document records and upload API

Added the first persistent layer: a SQLite-backed document table and upload/list routes in the backend. The upload endpoint writes the file to a local data/uploads directory, records filename, size, type, storage path, timestamp, and status, and exposes a GET /documents list for later UI rendering. This comes before browser document screens so storage is proven before the frontend depends on it.

Verification: the targeted backend test passes with pytest. It uploads a sample file and confirms the document appears in the list response. The endpoint is now ready for the next phase’s document display work.

## Phase 1 — Project foundation
Created separate frontend and backend folders, Git ignore rules, and a persistent documentation agreement in AGENTS.md.
This comes first so browser code and Python processing have clear homes and generated files, credentials, and large reference PDFs do not enter Git accidentally. The supplied PDFs and ZIP stay on disk.
Verification: both folders and all three learning logs exist. Git initialized and this foundation committed.

## Phase 2 — React homepage
Created the React/TypeScript entry point, a small homepage, and Vite build configuration. A working browser foundation comes before API integration so frontend setup errors are isolated.
Verification: TypeScript and production build pass; Vite serves on http://127.0.0.1:5173. Downloads and localhost binding required sandbox permission.

## Phase 3 — Health API
Created the FastAPI application and typed GET /health response. A minimal endpoint proves the Python server works before introducing browser networking, storage, or PDF parsing.
Verification: live HTTP request returned 200 with {"status":"ok","service":"fact-layer-api"}. Backend runs on port 8000.

## Phase 4 — Browser/API connection
Added a health component with loading, success, offline, timeout, and retry behavior. Allowed the two exact local frontend origins in FastAPI. This verifies the network boundary before building feature screens.
Verification: production build passes; live CORS response allows the frontend origin; headless Chrome renders “Backend connected” after a real API request.

## Phase 5 — Navigable application shell
Built a responsive sidebar/top navigation, breadcrumb, page heading, reusable section metadata, and distinct Documents/Facts/Comparisons empty states. Added clear future-feature labels; upload is disabled and metrics use dashes because no database exists yet. This phase establishes where later document, fact, and relationship features will live after both runtime foundations and the API boundary have been verified.

Hash navigation preserves the section across refresh and browser Back without introducing routing infrastructure for three placeholders. Added focus indicators, a skip link, current-page semantics, live connection status, and reduced-motion handling. Reviewed desktop/mobile screenshots and removed decorative artwork on small screens to keep text clear.

A live check discovered port 5173 serving another local project. Current defaults are **frontend 5178 and backend 8018**; CORS, API config, and README were updated together. Earlier log entries retain the ports used at those checkpoints. Existing unrelated project processes were not stopped.

Verification: TypeScript/production build; real Chrome navigation across all three views; Back and reload; disabled upload; mobile navigation and no horizontal overflow at 390px; simulated failed health request followed by successful retry; no browser exceptions. Added local run instructions in README.md. Part 1 is complete; next is Phase 6, SQLite document records.
