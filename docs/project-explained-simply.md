# FactFlow explained in very simple words

## 1. What is this website?

FactFlow is a place to **read, organize, and compare statements from PDF files**.

Imagine you have several reports. You want to find what they say about revenue, costs, or another subject, without repeatedly searching through every page yourself.

You upload the reports. FactFlow pulls out readable statements, lets you search them, and shows some statements from different reports next to each other. You can open the original PDF to check the source.

**Its main purpose is to help you review information with its source close by.**

The project is also called “Fact Layer” in some files. These names refer to the same application here.

## 2. What can a user achieve?

A user can:

- Keep a local collection of PDFs.
- Find extracted statements containing particular words.
- See which document and page a statement came from.
- Read text extracted from supported scanned PDFs.
- Spot matching wording or possible differences across documents.
- Open the source PDF and decide what a statement means in context.
- Process a document again, or delete it and its extracted statements.
- Back up the collection and restore it using the documented procedure.

For example, suppose Report A says **“Revenue increased 20 percent.”** and Report B says **“Revenue increased 30 percent.”**

FactFlow can show this pair as a possible difference. You can then open both PDFs to check whether they refer to the same year, company, or region. The difference might be meaningful, or the reports might simply be discussing different things.

The result is a more organized review of the documents. The website does not make the final judgment for you.

## 3. What does “fact” mean here?

In this app, a “fact” is an **extracted statement from a document**.

It is not a promise that the statement is true. A PDF can contain an error, an opinion, or an outdated number. Scanned text can also be read incorrectly.

The app does not search the internet to verify statements. It does not call ChatGPT or another language-model service. Its comparisons use programmed text rules.

“Matching wording” means the words match after small changes such as ignoring capital letters and extra spaces. It does not mean two independent sources proved something.

“Possible difference” means the statements share enough words to be worth inspecting together. It does not prove a contradiction. The app can miss related statements that use very different words, and it can pair unrelated statements that happen to share words.

## 4. What are the main screens?

| Screen | What you do there |
| --- | --- |
| Documents | Upload PDFs, see their status, inspect extracted evidence, process again, or delete. |
| Facts | Search extracted statements, filter by document, and inspect page references and source links. |
| Comparisons | See related-looking statements from different documents side by side; filter by document or relationship. |

Lists are split into pages so the browser does not display everything at once. The browser normally shows 20 results per page.

## 5. What happens when I upload a PDF?

1. **The browser sends the file** to the Python part of the app.
2. **The app checks it.** It checks the filename/type and applies its file-size limit.
3. **The app saves the original file.** It copies small pieces into a temporary file, then makes the finished file available. This avoids creating one large copy in the upload handler's memory.
4. **The app records the document.** A small database stores its name, ID, size, status, and source-file reference.
5. **The app reads the pages.** It reads existing PDF text, or uses OCR when a page contains an image or has no readable native text.
6. **The app keeps useful-looking statements.** It splits text, filters some noise, and removes repeated statements within that document.
7. **The app stores the statements with their source information.** This includes the document, page number, and whether OCR was used.
8. **The browser shows the result.** You can search the statements and open the original PDF.

The source text shown with a statement is extracted text. It is not always a full paragraph around that statement. Opening the PDF gives you the wider context.

The stored PDF is not rewritten into a new OCR document. Source links open the original bytes; jumping directly to a page depends on your browser's PDF viewer.

## 6. What happens when something goes wrong?

If a new PDF cannot be read, it can remain in Documents with an extraction-failed status.

If processing an existing document again fails, its earlier extracted statements remain available with a warning. A successful retry replaces the old statements.

Only one upload, reprocess, or delete operation is allowed at a time in the supported single API process. If another operation is running, the website tells you to wait and retry manually. It does not secretly add your request to a queue.

You can continue browsing during processing. Closing the page does not necessarily stop work already running on the server. If you lose the connection, check Documents before uploading again—the first request might have succeeded.

## 7. The basic building blocks

These words describe roles, not competing products:

| Word | Very simple meaning |
| --- | --- |
| Frontend | The part you see and click in the browser. |
| Backend | The part that receives requests, processes files, and stores results. |
| API | The set of requests the frontend can send to the backend, such as “give me the documents.” |
| Database | Organized storage for records, such as document names and extracted statements. |
| Language | A way of writing instructions for a computer. Python and TypeScript are examples. |
| Library | Ready-made code your own code can use. |
| Framework | A larger set of ready-made pieces and conventions for building an application. |
| Package | A bundle of code that can be installed. A package may contain a library or a tool. |
| Dependency | A package that some other code needs to work. |

For this project, the basic connection is:

**Browser → Python API → PDF processing and local storage → Python API → Browser**

## 8. Tools used for the visible website

| Tool | What it generally does | How FactFlow uses it |
| --- | --- | --- |
| HTML | Describes page elements such as headings, inputs, and buttons. | Provides the page structure rendered in the browser. |
| CSS | Controls appearance: colors, spacing, size, and layout. | Styles the sidebar, cards, messages, mobile layout, and focus indicators. Much of this is custom CSS in index.css. |
| JavaScript | Makes web pages respond to actions. | The browser runs JavaScript produced from the project's TypeScript code. |
| TypeScript | Adds checks to JavaScript code so some mistakes are caught before running it. | Describes document/fact data and checks component code during the build. It does not itself prove API data is correct at runtime. |
| React | Builds interactive pages from reusable pieces called components. | Manages the Documents, Facts, and Comparisons screens, loading states, filters, messages, and updates after actions. |
| React DOM | Connects React components to an actual browser page. | Places the main App component into the page in main.tsx. |
| Tailwind CSS | Provides styling tools and ready-made CSS utility classes. | Is imported into the project's styling and built through its Vite plugin, alongside custom CSS. |
| lucide-react | Supplies icons that can be used in React. | Provides icons for navigation and actions such as upload, refresh, and delete. |
| Browser fetch | Sends network requests from browser code. | Calls the API to upload files and load or change records. No separate Axios library is used. |
| Browser AbortController | Can stop waiting for a browser request. | Cancels obsolete read requests when views or filters change. It is not a server-side “cancel extraction” feature. |
| URL hash and browser history | Track the part of a page after `#` and allow Back/Forward navigation. | Keep track of the selected screen without a separate routing library. |

## 9. Tools that build and run the frontend

| Tool | What it generally does | How FactFlow uses it |
| --- | --- | --- |
| Node.js | Runs JavaScript outside a browser. | Runs the frontend development tools and browser-test tools. It is not the PDF-processing backend. |
| npm | Installs JavaScript packages and runs named commands. | Runs commands such as `npm run dev`, `npm run build`, and the browser tests. |
| Vite | Serves a website during development and prepares files for a finished build. | Runs the local frontend server and creates the dist folder for a production build. A successful build does not deploy the site. |
| @vitejs/plugin-react | Helps Vite work with React. | Connects React development/build support to Vite. |
| @tailwindcss/vite | Helps Vite build Tailwind styling. | Connects Tailwind's CSS processing to the frontend build. |
| @types/react and @types/react-dom | Describe React's APIs for TypeScript's checks. | Help TypeScript check React code. They do not add visible features. |
| package.json and package-lock.json | List packages, commands, and resolved package versions. | Describe frontend dependencies and help repeat installations. They are project files, not running services. |

## 10. Tools used by the backend

| Tool | What it generally does | How FactFlow uses it |
| --- | --- | --- |
| Python | A programming language often used for servers and file processing. | Implements uploads, extraction, storage, comparisons, and backend tests. |
| FastAPI | A framework for building Python APIs. | Defines requests such as upload, list facts, reprocess, and delete. Also supplies interactive API documentation. |
| Uvicorn | Runs a Python web application so it can receive HTTP requests. | Starts the FastAPI backend on a local port. FastAPI defines behavior; Uvicorn runs the server. |
| Pydantic | Checks and describes structured data. | Defines response shapes for documents, facts, comparison cards, and result pages. |
| Starlette | Provides underlying web features used by FastAPI. | Supports requests, file responses, browser-origin rules, and running blocking work in a worker thread. |
| python-multipart | Reads uploads sent in multipart form format. | Helps the API receive the file sent by the browser's upload form. |
| SQLite | Stores records in a local database file without a separate database server. | Stores document metadata, extracted statements, and schema version information in factlayer.db. Original PDFs stay in the uploads folder. |
| Python sqlite3 | Python's built-in way to communicate with SQLite. | Runs database queries and transactions. No separate ORM such as SQLAlchemy is used. |
| CORS middleware | Controls which browser origins may read API responses. | Allows the configured local frontend addresses to communicate with the API. This is not a login or authentication system. |

A database **transaction** groups database changes so they can succeed together or be rolled back together. FactFlow uses this for storage upgrades and other database changes. It does not make file changes and database changes one crash-proof operation.

## 11. Tools that read PDFs and scans

OCR means **Optical Character Recognition**. In simple words, it tries to turn a picture of words into text.

| Tool | What it generally does | How FactFlow uses it |
| --- | --- | --- |
| pypdf | Reads and works with PDF files. | Extracts text already stored as text in native PDF pages. Also helps create or combine test PDFs. |
| pypdfium2 | Gives Python access to a PDF engine that can draw PDF pages as images. | Turns pages into images for the OCR path. |
| Pillow | Opens, creates, and changes images in Python. | Handles images used for OCR and creates synthetic scanned documents for tests. |
| Tesseract | An OCR program that recognizes printed text in images. | Reads English text from rendered PDF pages. It is a separate installed program, not a language-model API. |
| Tesseract English data (`eng`) | Supplies the OCR engine's English recognition data. | Lets the configured OCR worker read supported English scans. |

These tools do different jobs: **draw the page as an image → prepare the image → recognize its words**.

OCR can get words or numbers wrong. The app rejects some low-quality results and labels OCR evidence for review, but those checks are not a guarantee of accuracy.

## 12. Built-in Python tools used behind the scenes

These come with Python; they are not separate services to buy or install.

| Tool or group | General job | Use here |
| --- | --- | --- |
| pathlib | Works with paths to files and folders. | Resolves source filenames inside the configured uploads folder and helps reject unsafe paths. |
| tempfile | Creates temporary files and folders. | Holds incomplete upload copies, OCR scratch files, and isolated test collections. |
| os and shutil | Work with the operating system and files. | Read settings, publish finished uploads, find the OCR executable, and copy test storage. |
| subprocess and signal | Start other programs and control processes. | Run disposable extraction workers and stop a worker group when its time limit is reached. |
| sys | Gives information about the current Python process. | Starts child workers using the same Python interpreter. |
| threading.Lock | Lets one piece of work hold exclusive access. | Gives upload/reprocess/delete one shared operation slot per API process. |
| asyncio | Coordinates work that waits for other work. | Keeps ownership of the upload extraction slot until the worker finishes, even if the requesting task is cancelled. |
| contextlib | Helps arrange setup and cleanup around work. | Ensures the operation slot is released on the appropriate exit paths. |
| re | Finds text patterns. | Helps split statements and extract words for comparisons. |
| collections.defaultdict | Builds grouped lookup tables conveniently. | Helps index words to find candidate comparison pairs without checking every unrelated pair. |
| uuid | Creates unique identifiers. | Gives documents and extracted statements IDs. |
| datetime and timezone | Work with dates and times. | Record when documents and statements were created. |
| json | Reads/writes a common structured data format. | Exchanges extraction results and saves evaluation reports. The API also sends JSON to the browser. |
| csv and io | Read table-like text and in-memory streams. | Read Tesseract's word/confidence output and handle generated test data. |
| math | Supplies common number operations. | Helps check rendering sizes in the OCR worker. |
| tarfile and hashlib | Create/read archives and calculate file fingerprints. | Test backups and verify restored PDF bytes are unchanged. |
| argparse | Reads options given to a script. | Supports benchmark, evaluation, and recovery test commands. |

## 13. Tools used to test the project

| Tool | What it generally does | How FactFlow uses it |
| --- | --- | --- |
| pytest | Runs automated Python checks. | Tests uploads, database rules, OCR, evidence preservation, recovery, concurrency, and failure handling. |
| FastAPI/Starlette TestClient | Lets a test make API requests without starting a normal network server. | Exercises the backend using temporary data. |
| HTTPX | Makes HTTP requests from Python. | Supports the installed TestClient-based test setup. It is not an external service the website contacts. |
| Playwright / @playwright/test | Controls a real browser automatically. | Clicks buttons, selects files, checks messages, and verifies page behavior. |
| Chromium or installed Google Chrome | Runs the web page. | Serves as the browser used by Playwright checks. |
| Mocked API responses | Replace a real response with a controlled test response. | Test loading, failure, busy, and retry states reliably at desktop/mobile sizes. This is a technique, not a separate paid tool. |
| Real integration tests | Exercise multiple app parts together. | Run the actual frontend and backend against temporary PDFs/storage, including OCR, recovery, and contention. |
| Synthetic fixtures | Small made-up inputs with known expected behavior. | Test scans, PDF statements, backups, and comparison rules without using the user's real documents. |
| Benchmark/evaluation scripts | Measure performance or compare output with expected labels. | Record OCR timing, collection performance, and errors on labeled comparison pairs. Synthetic results do not establish real-world accuracy for every document. |

Some Python packages support other packages rather than features written directly by this project:

- **AnyIO:** async/thread support used underneath the web framework and tests.
- **pydantic_core, annotated-types, typing-inspection, typing_extensions, annotated-doc:** help with data checking, type information, or annotations.
- **h11, httpcore, certifi, idna:** support HTTP communication, certificates, and address handling in the installed server/client stack.
- **click:** helps command-line programs such as the server command understand options.
- **pluggy, iniconfig, packaging, Pygments:** support test plugins, configuration, version handling, or formatted output in the installed tool stack.

These are supporting dependencies, not additional FactFlow screens. Frontend tools also install many supporting packages automatically. The complete resolved lists are in [package-lock.json](../frontend/package-lock.json) and [requirements.lock.txt](../backend/requirements.lock.txt); this guide explains the main tools and groups supporting packages so it stays readable.

## 14. Tools used to manage development

| Tool | General job | Use here |
| --- | --- | --- |
| Git | Records versions of project files. | Tracks code/documentation changes. Runtime PDFs/database files are ignored; Git is not a backup of the document collection. |
| Markdown (`.md`) | A simple text format with headings, lists, and links. | Holds this guide, setup instructions, plans, and learning logs. |
| Python venv | Keeps a project's Python packages in its own environment. | Holds the backend's installed packages in .venv. |
| pip | Installs Python packages. | Installs the backend requirements into that environment. |
| Homebrew | Installs tools on macOS. | Is the documented way to install Tesseract on the development machine. It is not part of a user's PDF processing logic. |
| Environment variables | Settings passed to a program when it starts. | Set the data directory, OCR executable, and frontend API address without rewriting application code. |

The project keeps three learning logs: [direction.md](../direction.md) explains why work was done, [flow.md](../flow.md) explains how the app behaves, and [tech.md](../tech.md) explains tool choices and trade-offs.

## 15. Where are the important pieces of code?

| File | Simple purpose |
| --- | --- |
| [frontend/src/App.tsx](../frontend/src/App.tsx) | Main screens, user actions, and displayed results. |
| [frontend/src/BackendStatus.tsx](../frontend/src/BackendStatus.tsx) | Checks whether the backend can be reached. |
| [frontend/src/SourceSelect.tsx](../frontend/src/SourceSelect.tsx) | Lets users search/page through document choices for filters. |
| [backend/app/main.py](../backend/app/main.py) | API routes, database initialization, statement storage, and response building. |
| [backend/app/upload_storage.py](../backend/app/upload_storage.py) | Copies uploads in small pieces and cleans temporary copies. |
| [backend/app/storage.py](../backend/app/storage.py) | Validates source references and converts older database paths. |
| [backend/app/extraction.py](../backend/app/extraction.py) | Starts and times the separate extraction process. |
| [backend/app/ocr_worker.py](../backend/app/ocr_worker.py) | Reads PDF pages and performs OCR when needed. |
| [backend/app/comparison_candidates.py](../backend/app/comparison_candidates.py) | Finds statement pairs using word-based rules. |
| [backend/app/admission.py](../backend/app/admission.py) | Allows one document-changing operation at a time per API process. |

A **schema version** means the version of the database's layout/rules. Current schema 3 stores source filenames relative to the uploads folder, making whole-collection relocation possible. The API still returns full local paths where needed. Older collections must follow the migration instructions before moving them.

## 16. What are its current limits?

- It is designed for **local, single-user use with one API process**, not public multi-user hosting.
- It has no accounts/login system, chat assistant, or automatic internet fact-checking.
- Uploads are limited to 10 MiB, shown as 10 MB in messages. The web framework receives/parses the upload before the handler checks it, so this is not a limit on every resource used by an incoming request.
- Extraction allows up to 40 pages and a 90-second document deadline. OCR has additional per-page/image limits.
- OCR focuses on upright English printed text. Handwriting, rotated pages, and complex tables are not reliable supported cases.
- Comparison uses shared words, not full understanding of meaning. Human review is necessary.
- There is no durable job queue, automatic retry, or guaranteed recovery from every sudden shutdown.
- Backups must include the database **and** original PDFs. Storing only one of them is incomplete.

Use the [README](../README.md) to run the app and the [operations guide](operations.md) for backup, restore, and troubleshooting. This file explains the project; it does not replace those step-by-step operating instructions.
