# User and data flow log

Updated after every completed phase. Current milestone: Phase 4 complete.

## Phase 1 — Project foundation
User flow: no website runs yet; the developer opens the frontend and backend folders.
Data flow: reference PDFs remain local files. There is no browser request, server, database, or document processing yet.

## Phase 2 — React homepage
User flow: open localhost:5173 and see the Fact Layer introduction.
Data flow: browser requests index.html and frontend modules from Vite; React mounts App into the root element. All displayed text is static. No API call or persistent data exists.

## Phase 3 — Health API
User flow: the homepage still shows static content. A developer can separately open localhost:8000/health or /docs.
Data flow: HTTP GET /health → Uvicorn → FastAPI route → Pydantic response serialization → JSON response. React is not connected yet. No data is stored.

## Phase 4 — Browser/API connection
User flow: open the homepage → see “Checking connection…” → “Backend connected” if healthy. If unavailable, see an offline state and a Retry connection button.
Data flow: React effect → browser fetch to VITE_API_BASE_URL/health (default http://127.0.0.1:8000) → FastAPI → JSON and CORS header → runtime shape check → React state update → status label rerenders. Requests abort after five seconds or component cleanup. Retry starts a new request. Status is a point-in-time check, not continuous monitoring. Nothing is persisted.
