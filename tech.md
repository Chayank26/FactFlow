# Technology decision log

Updated after every completed phase. Current milestone: Part 1 complete (phases 1–5). Current local ports: frontend 5178, API 8018.

## Phase 1 — Project foundation
**One Git repository with frontend/ and backend/:** one history keeps application changes and learning notes together. Separate repositories would add coordination overhead for this solo practice project. A monorepo orchestrator would add machinery before we have shared packages or complex build dependencies.
**Git:** local checkpoints make each phase inspectable and reversible. Manual folder backups do not provide useful diffs or coherent history. No hosted service is required to run locally.
**Markdown:** these logs are readable in the IDE and versioned alongside code. An external notes application would separate explanations from the changes they describe.

## Phase 2 — React, TypeScript, Vite
**React:** component composition will let the document list, evidence panel, and comparison views share UI patterns. Vue and Svelte are valid alternatives; React matches the agreed learning stack and avoids switching ecosystems during this project. The trade-off is explicit state/effect handling and more boilerplate than some alternatives.
**TypeScript:** catches inconsistent props and API shapes during development; plain JavaScript has less setup but fewer static checks. Types do not replace runtime validation.
**Vite:** provides a focused client dev server and production build. Next.js adds server-rendering conventions we do not currently need with our separate Python API. A manual Webpack setup adds configuration work. The installed dependency graph is recorded in package-lock.json.
Reference: https://vite.dev/guide/

## Phase 3 — Python API
**Python 3.13 + venv:** a project-local environment isolates dependencies from other projects. The machine default is Python 3.9, so this setup explicitly uses the installed 3.13 interpreter. A Conda environment could work but is unnecessary for this small web service.
**FastAPI:** typed request/response handling and generated /docs suit the future extraction API. Flask is smaller but requires more choices for validation and API documentation. Django includes useful full-site features, such as its ORM and admin, which this phase does not need. Express would keep one language across the app but move processing away from the planned Python PDF tooling.
**Pydantic:** validates and serializes the health response and will later validate claims. Plain dictionaries are simpler but do not enforce the response contract.
**Uvicorn:** serves the ASGI application locally; its reload mode aids development. A production process manager is premature here.
**requirements.lock.txt:** records exact installed versions for repeatable setup; requirements.txt expresses direct dependencies. Regenerate the lock after intentional dependency changes.

## Phase 4 — Fetch, effects, and CORS
**Browser fetch + AbortController:** enough for one GET with cancellation and timeout. Axios adds a dependency without a current need for interceptors. A query library becomes useful when we have cached document/fact lists; local component state is adequate now.
**React effect:** ties the connection check to mounting and retry, with cleanup to prevent stale updates. No global state library is needed for one isolated status component.
**FastAPI CORSMiddleware:** browsers treat ports 5173 and 8000 as different origins. Explicit local origins let the browser read the response. A wildcard is unnecessary; CORS is not authentication. A Vite proxy is an alternative but would hide the cross-origin boundary we want to learn here. GET is the only allowed method for now; extend this deliberately when uploads arrive.
**VITE_API_BASE_URL:** makes the API location configurable without editing components. Vite embeds this value in public browser code, so it must never contain secrets.
**Temporary Playwright + installed Chrome:** verifies actual browser fetch/CORS behavior that curl alone cannot prove. Kept outside application dependencies because this is a small smoke check.
Reference: https://fastapi.tiangolo.com/tutorial/cors/

## Phase 5 — Layout and navigation
**Tailwind CSS via its Vite plugin:** integrates the agreed styling stack and provides a shared baseline plus utilities for later components. This shell mostly uses named CSS classes so a learner can inspect layout rules together in one stylesheet. Plain CSS alone would be enough for this phase; Tailwind is a consistency choice, not a runtime requirement for facts. Bootstrap would provide more preset components but impose a visual style; CSS-in-JS would add component styling machinery we do not need.

**Lucide React:** named SVG icon imports give the navigation and evidence concepts a consistent visual vocabulary. Hand-drawn icons take maintenance time; emoji have inconsistent appearance and semantics across platforms. Icons accompanying text are decorative and the text supplies the label.

**Native hash links + React state:** support direct section URLs, Back/Forward, refresh, and keyboard navigation for three views. React Router becomes worthwhile with nested document detail URLs, route loading, or more complex navigation. A state-only switch would lose URL/history behavior. No Redux or global store is justified at this scale.

**CSS flex/grid and media queries:** adapt the same document structure to desktop and mobile. Separate mobile pages would duplicate state and markup. System fonts avoid external font requests. Decorative document artwork uses CSS and SVG icons; raster image generation is unnecessary for these simple shapes.

**Dedicated ports 5178/8018 and strict frontend port:** avoid a discovered conflict with another project. Silently choosing a new frontend port could break the explicit CORS origins, so a collision should be visible. CORS still allows only the two intended local frontend origins.

**Retained tools:** React, TypeScript, Vite, FastAPI, Pydantic, fetch, local component state, and Git remain appropriate. No database, PDF parser, LLM, or authentication tool was added in Part 1 because no implemented task requires them yet.

Reference: https://tailwindcss.com/docs/installation/using-vite
