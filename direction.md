# Direction log

Updated after every completed phase. Current milestone: Phase 2 complete.

## Phase 1 — Project foundation
Created separate frontend and backend folders, Git ignore rules, and a persistent documentation agreement in AGENTS.md.
This comes first so browser code and Python processing have clear homes and generated files, credentials, and large reference PDFs do not enter Git accidentally. The supplied PDFs and ZIP stay on disk.
Verification: both folders and all three learning logs exist. Git initialized and this foundation committed.

## Phase 2 — React homepage
Created the React/TypeScript entry point, a small homepage, and Vite build configuration. A working browser foundation comes before API integration so frontend setup errors are isolated.
Verification: TypeScript and production build pass; Vite serves on http://127.0.0.1:5173. Downloads and localhost binding required sandbox permission.
