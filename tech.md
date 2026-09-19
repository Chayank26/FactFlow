# Technology decision log

Updated after every completed phase. Current milestone: Part 3 Phase 3 complete. Current local ports: frontend 5179, API 8019.

## Part 3 Phase 3 — Extraction quality

**Sentence splitting:** a small regular-expression boundary keeps the extractor dependency-free while turning parser lines containing multiple claims into separate facts. It is intentionally conservative and handles common terminal punctuation rather than attempting full natural-language parsing.

**Quality filter:** claims must contain at least three alphanumeric words and five alphabetic characters. This removes separators and empty extraction artifacts without pretending to judge the truth or importance of a claim.

**Document-level deduplication:** case-folded claim strings provide an explainable exact duplicate check. Semantic duplicates remain available for later matching in the comparison layer rather than being discarded here.

**Verification:** 6 backend tests and the frontend production build pass. OCR was not added because scanned-PDF support is a separate capability with different runtime and dependency trade-offs.

## Part 3 Phase 2 — Document management

**Server-side validation:** the upload endpoint now requires a PDF filename and `application/pdf` content type, and enforces a 10 MB limit. Client-side `accept` hints can improve the picker experience, but they are not a security boundary, so validation remains in FastAPI.

**Explicit cleanup:** deletion removes facts, the document row, and the stored file in one application workflow. The database currently uses explicit dependent-row cleanup rather than relying on a migration to alter the existing facts foreign key.

**Reprocessing:** extraction is shared by initial upload and the process endpoint. Reprocessing replaces the document’s prior facts, which avoids duplicate evidence while keeping the document ID stable for future links.

**Verification:** 5 focused backend tests and the frontend production build pass. The suite emits existing Starlette/httpx deprecation warnings, but no test failures.

## Part 2 planning checkpoint

Part 2 keeps the same architecture but introduces the first persistent layer. The planned stages use the tools already present in the stack and defer additional complexity until the data model is proven:

- SQLite for local document metadata and extracted fact records.
- FastAPI endpoints for upload, listing, and retrieval operations.
- React state and fetch calls for document interactions in the browser.
- PDF parsing only when the storage model is stable enough to support evidence linkage.

This staged sequence keeps each change testable and leaves room for a later switch to a richer OCR or extraction pipeline if the project grows.

## Phase 6 — SQLite document records and upload API

**SQLite:** a lightweight embedded database fits this project’s local-first workflow and keeps setup simple. It is enough for document metadata and later extracted fact records without adding another service or running a separate database container. The trade-off is that the local database file becomes part of the app state and should be treated as development data, not shared production infrastructure.

**FastAPI File uploads:** using UploadFile and multipart form parsing keeps the API aligned with browser uploads. This is a good fit for PDF intake and allows the app to validate file type and size at the route boundary before storing content. A more elaborate upload layer would be useful later, but this is enough for the current document persistence step.

**Data directory layout:** storing uploaded files in backend/data/uploads while SQLite keeps metadata in backend/data/factlayer.db keeps the persistence layer easy to inspect and easy to delete during development. The included PDFs and other reference materials remain outside the database and are not automatically imported.

**Verification:** the upload/list test passes in the project venv with pytest, proving the route writes a file and records it in SQLite. This is the foundation for the next phase’s document list UI.

## Phase 7 — Document list and metadata screen

**React fetch and local state:** the Documents screen uses the existing fetch-based approach rather than adding a data-fetching library. The small number of records and one upload action do not yet justify caching or global state. An AbortController prevents a stale list request from updating the component after navigation.

**Multipart browser upload:** a native file input and FormData send the selected file without manually setting the Content-Type header. The browser supplies the multipart boundary, while the FastAPI UploadFile route receives the file and persists it.

**Metadata presentation:** the UI formats byte counts and ISO timestamps at the display boundary, leaving API values structured and stable for later filtering or document detail views. The status is displayed as returned by the backend rather than inferred in the browser.

**Verification:** the frontend production build passes after correcting the new type-only React import. No PDF extraction library was added in this phase; the next phase will introduce it only alongside evidence storage.

## Phase 8 — PDF extraction and evidence-backed facts

**pypdf:** a focused, local PDF parser is sufficient for text-based reference PDFs and avoids adding a model or external service before the evidence schema is established. Scanned PDFs will need OCR in a later phase because text extraction alone cannot recover image-only text.

**Line-based fact records:** the first extractor preserves each non-empty PDF text line as a fact and uses the page number plus source text as its evidence reference. This is deliberately conservative: it avoids inventing claims or silently discarding provenance while giving the next UI phase concrete records to display. More semantic claim segmentation can be introduced after real documents reveal its requirements.

**SQLite relationship:** facts store the parent document ID rather than duplicating document metadata. The API supports an optional document filter so the frontend can load a focused evidence set without adding a separate query layer.

**Verification:** the focused backend suite passes with 2 tests. It covers document upload/list behavior and a real generated PDF upload through extraction, persistence, and filtered retrieval. The lock file records the installed pypdf version for repeatable setup.

## Phase 9 — Comparison workflow and context-aware evidence

**Derived comparisons:** comparison relationships are computed from facts at read time instead of stored in another table. This keeps the first version simple and prevents comparison data from becoming stale when source facts are reprocessed. A persisted comparison model can be introduced later if ranking, review state, or user annotations require it.

**Token overlap heuristic:** normalized token sets provide an explainable baseline for finding same-subject claims without an LLM. Exact token-set matches represent agreement; at least half shared tokens with remaining differences represent a difference. The heuristic is intentionally conservative and should be replaced or augmented with semantic matching when the project has enough real examples to evaluate it.

**Evidence-first UI:** each comparison renders both claims and source text with page numbers and filenames. The interface reports the relationship as derived context rather than presenting a conclusion without the underlying passages.

**Verification:** the focused backend suite passes with 3 tests, including a real two-document comparison, and the frontend production build passes. This completes the planned Part 2 phases.

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
