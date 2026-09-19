import sqlite3
import uuid
from datetime import datetime, timezone
from pathlib import Path

from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from pypdf import PdfReader

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
UPLOADS_DIR = DATA_DIR / "uploads"
DB_PATH = DATA_DIR / "factlayer.db"


def init_db() -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    UPLOADS_DIR.mkdir(parents=True, exist_ok=True)

    with sqlite3.connect(DB_PATH) as connection:
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS documents (
                id TEXT PRIMARY KEY,
                filename TEXT NOT NULL,
                size_bytes INTEGER NOT NULL,
                content_type TEXT,
                stored_path TEXT NOT NULL,
                created_at TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'uploaded'
            )
            """
        )
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS facts (
                id TEXT PRIMARY KEY,
                document_id TEXT NOT NULL,
                claim TEXT NOT NULL,
                source_page INTEGER NOT NULL,
                source_text TEXT NOT NULL,
                created_at TEXT NOT NULL,
                FOREIGN KEY (document_id) REFERENCES documents (id)
            )
            """
        )
        connection.commit()


def get_connection() -> sqlite3.Connection:
    connection = sqlite3.connect(DB_PATH)
    connection.row_factory = sqlite3.Row
    return connection


init_db()

app = FastAPI(title="Fact Layer API", version="0.1.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5179", "http://127.0.0.1:5179"],
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)


class HealthResponse(BaseModel):
    status: str
    service: str


class DocumentResponse(BaseModel):
    id: str
    filename: str
    size_bytes: int
    content_type: str | None
    stored_path: str
    created_at: str
    status: str


class FactResponse(BaseModel):
    id: str
    document_id: str
    claim: str
    source_page: int
    source_text: str
    created_at: str


@app.get("/health", response_model=HealthResponse)
def health() -> HealthResponse:
    return HealthResponse(status="ok", service="fact-layer-api")


def extract_facts(file_path: Path, document_id: str) -> list[FactResponse]:
    reader = PdfReader(str(file_path))
    extracted: list[FactResponse] = []
    created_at = datetime.now(timezone.utc).isoformat()

    for page_number, page in enumerate(reader.pages, start=1):
        text = page.extract_text() or ""
        for line in text.splitlines():
            claim = " ".join(line.split())
            if not claim:
                continue
            extracted.append(
                FactResponse(
                    id=str(uuid.uuid4()),
                    document_id=document_id,
                    claim=claim,
                    source_page=page_number,
                    source_text=claim,
                    created_at=created_at,
                )
            )

    return extracted


@app.post("/documents", response_model=DocumentResponse)
async def upload_document(file: UploadFile = File(...)) -> DocumentResponse:
    if not file.filename:
        raise HTTPException(status_code=400, detail="A file is required")

    safe_name = file.filename.replace("/", "_")
    document_id = str(uuid.uuid4())
    file_path = UPLOADS_DIR / f"{document_id}_{safe_name}"

    content = await file.read()
    file_path.write_bytes(content)

    created_at = datetime.now(timezone.utc).isoformat()
    status = "uploaded"
    facts: list[FactResponse] = []
    if file_path.suffix.lower() == ".pdf":
        try:
            facts = extract_facts(file_path, document_id)
            status = "processed"
        except Exception:
            status = "extraction_failed"

    with get_connection() as connection:
        connection.execute(
            """
            INSERT INTO documents (id, filename, size_bytes, content_type, stored_path, created_at, status)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                document_id,
                safe_name,
                len(content),
                file.content_type,
                str(file_path),
                created_at,
                status,
            ),
        )
        connection.executemany(
            """
            INSERT INTO facts (id, document_id, claim, source_page, source_text, created_at)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            [
                (fact.id, fact.document_id, fact.claim, fact.source_page, fact.source_text, fact.created_at)
                for fact in facts
            ],
        )
        connection.commit()

    return DocumentResponse(
        id=document_id,
        filename=safe_name,
        size_bytes=len(content),
        content_type=file.content_type,
        stored_path=str(file_path),
        created_at=created_at,
        status=status,
    )


@app.get("/documents", response_model=list[DocumentResponse])
def list_documents() -> list[DocumentResponse]:
    with get_connection() as connection:
        rows = connection.execute(
            "SELECT id, filename, size_bytes, content_type, stored_path, created_at, status FROM documents ORDER BY created_at DESC"
        ).fetchall()

    return [
        DocumentResponse(
            id=row["id"],
            filename=row["filename"],
            size_bytes=row["size_bytes"],
            content_type=row["content_type"],
            stored_path=row["stored_path"],
            created_at=row["created_at"],
            status=row["status"],
        )
        for row in rows
    ]


@app.get("/facts", response_model=list[FactResponse])
def list_facts(document_id: str | None = None) -> list[FactResponse]:
    query = "SELECT id, document_id, claim, source_page, source_text, created_at FROM facts"
    parameters: tuple[str, ...] = ()
    if document_id:
        query += " WHERE document_id = ?"
        parameters = (document_id,)
    query += " ORDER BY created_at DESC, source_page ASC"

    with get_connection() as connection:
        rows = connection.execute(query, parameters).fetchall()

    return [
        FactResponse(
            id=row["id"],
            document_id=row["document_id"],
            claim=row["claim"],
            source_page=row["source_page"],
            source_text=row["source_text"],
            created_at=row["created_at"],
        )
        for row in rows
    ]
