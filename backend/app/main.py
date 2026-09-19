import sqlite3
import re
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
MAX_UPLOAD_BYTES = 10 * 1024 * 1024
SCHEMA_VERSION = 1


def init_db() -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    UPLOADS_DIR.mkdir(parents=True, exist_ok=True)

    with sqlite3.connect(DB_PATH) as connection:
        connection.execute("PRAGMA foreign_keys = ON")
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
        connection.execute("CREATE INDEX IF NOT EXISTS idx_facts_document_id ON facts (document_id)")
        connection.execute("CREATE INDEX IF NOT EXISTS idx_facts_created_at ON facts (created_at)")
        connection.execute("CREATE INDEX IF NOT EXISTS idx_documents_created_at ON documents (created_at)")
        current_version = connection.execute("PRAGMA user_version").fetchone()[0]
        if current_version < SCHEMA_VERSION:
            connection.execute(f"PRAGMA user_version = {SCHEMA_VERSION}")
        connection.commit()


def get_connection() -> sqlite3.Connection:
    connection = sqlite3.connect(DB_PATH)
    connection.execute("PRAGMA foreign_keys = ON")
    connection.row_factory = sqlite3.Row
    return connection


init_db()

app = FastAPI(title="Fact Layer API", version="0.1.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5179", "http://127.0.0.1:5179"],
    allow_methods=["DELETE", "GET", "POST"],
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


class ComparisonResponse(BaseModel):
    id: str
    relationship: str
    summary: str
    left_document_id: str
    left_document_name: str
    left_claim: str
    left_page: int
    left_source_text: str
    right_document_id: str
    right_document_name: str
    right_claim: str
    right_page: int
    right_source_text: str


@app.get("/health", response_model=HealthResponse)
def health() -> HealthResponse:
    return HealthResponse(status="ok", service="fact-layer-api")


def split_claims(text: str) -> list[str]:
    claims: list[str] = []
    for line in text.splitlines():
        normalized_line = " ".join(line.split())
        if not normalized_line:
            continue
        for sentence in re.split(r"(?<=[.!?])\s+", normalized_line):
            claim = sentence.strip()
            words = re.findall(r"[A-Za-z0-9]+", claim)
            if len(words) < 3 or sum(character.isalpha() for character in claim) < 5:
                continue
            claims.append(claim)
    return claims


def extract_facts(file_path: Path, document_id: str) -> list[FactResponse]:
    reader = PdfReader(str(file_path))
    extracted: list[FactResponse] = []
    seen_claims: set[str] = set()
    created_at = datetime.now(timezone.utc).isoformat()

    for page_number, page in enumerate(reader.pages, start=1):
        text = page.extract_text() or ""
        for claim in split_claims(text):
            normalized_claim = claim.casefold()
            if normalized_claim in seen_claims:
                continue
            seen_claims.add(normalized_claim)
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


def document_from_row(row: sqlite3.Row) -> DocumentResponse:
    return DocumentResponse(
        id=row["id"],
        filename=row["filename"],
        size_bytes=row["size_bytes"],
        content_type=row["content_type"],
        stored_path=row["stored_path"],
        created_at=row["created_at"],
        status=row["status"],
    )


def get_document_row(document_id: str) -> sqlite3.Row:
    with get_connection() as connection:
        row = connection.execute(
            "SELECT id, filename, size_bytes, content_type, stored_path, created_at, status FROM documents WHERE id = ?",
            (document_id,),
        ).fetchone()
    if row is None:
        raise HTTPException(status_code=404, detail="Document not found")
    return row


def process_document(document_id: str, file_path: Path) -> list[FactResponse]:
    if file_path.suffix.lower() != ".pdf":
        raise HTTPException(status_code=415, detail="Only PDF documents can be processed")

    try:
        facts = extract_facts(file_path, document_id)
    except Exception as error:
        with get_connection() as connection:
            connection.execute(
                "UPDATE documents SET status = 'extraction_failed' WHERE id = ?",
                (document_id,),
            )
            connection.commit()
        raise HTTPException(status_code=422, detail="The PDF could not be processed") from error

    with get_connection() as connection:
        connection.execute("DELETE FROM facts WHERE document_id = ?", (document_id,))
        connection.executemany(
            "INSERT INTO facts (id, document_id, claim, source_page, source_text, created_at) VALUES (?, ?, ?, ?, ?, ?)",
            [
                (fact.id, fact.document_id, fact.claim, fact.source_page, fact.source_text, fact.created_at)
                for fact in facts
            ],
        )
        connection.execute(
            "UPDATE documents SET status = 'processed' WHERE id = ?",
            (document_id,),
        )
        connection.commit()
    return facts


@app.post("/documents", response_model=DocumentResponse)
async def upload_document(file: UploadFile = File(...)) -> DocumentResponse:
    if not file.filename:
        raise HTTPException(status_code=400, detail="A file is required")

    if not file.filename.lower().endswith(".pdf") or file.content_type != "application/pdf":
        raise HTTPException(status_code=415, detail="Only PDF documents are supported")

    safe_name = file.filename.replace("/", "_")
    document_id = str(uuid.uuid4())
    file_path = UPLOADS_DIR / f"{document_id}_{safe_name}"

    content = await file.read()
    if len(content) > MAX_UPLOAD_BYTES:
        raise HTTPException(status_code=413, detail="The PDF exceeds the 10 MB upload limit")
    file_path.write_bytes(content)

    created_at = datetime.now(timezone.utc).isoformat()
    status = "uploaded"

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
        connection.commit()

    try:
        process_document(document_id, file_path)
        status = "processed"
    except HTTPException:
        status = "extraction_failed"
        with get_connection() as connection:
            connection.execute(
                "UPDATE documents SET status = ? WHERE id = ?",
                (status, document_id),
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

    return [document_from_row(row) for row in rows]


@app.get("/documents/{document_id}", response_model=DocumentResponse)
def get_document(document_id: str) -> DocumentResponse:
    return document_from_row(get_document_row(document_id))


@app.post("/documents/{document_id}/process", response_model=DocumentResponse)
def reprocess_document(document_id: str) -> DocumentResponse:
    row = get_document_row(document_id)
    process_document(document_id, Path(row["stored_path"]))
    return document_from_row(get_document_row(document_id))


@app.delete("/documents/{document_id}", status_code=204)
def delete_document(document_id: str) -> None:
    row = get_document_row(document_id)
    with get_connection() as connection:
        connection.execute("DELETE FROM facts WHERE document_id = ?", (document_id,))
        connection.execute("DELETE FROM documents WHERE id = ?", (document_id,))
        connection.commit()

    Path(row["stored_path"]).unlink(missing_ok=True)


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


def claim_tokens(claim: str) -> set[str]:
    return {token.strip(".,:;!?()[]{}").lower() for token in claim.split() if token.strip(".,:;!?()[]{}")}


@app.get("/comparisons", response_model=list[ComparisonResponse])
def list_comparisons(
    document_id: str | None = None,
    relationship: str | None = None,
) -> list[ComparisonResponse]:
    if relationship not in (None, "agreement", "difference"):
        raise HTTPException(status_code=400, detail="Unsupported comparison relationship")

    with get_connection() as connection:
        rows = connection.execute(
            """
            SELECT facts.id, facts.document_id, facts.claim, facts.source_page, facts.source_text,
                   documents.filename AS document_name
            FROM facts
            JOIN documents ON documents.id = facts.document_id
            ORDER BY facts.created_at DESC, facts.source_page ASC
            """
        ).fetchall()

    comparisons: list[ComparisonResponse] = []
    for index, left in enumerate(rows):
        left_tokens = claim_tokens(left["claim"])
        if not left_tokens:
            continue
        for right in rows[index + 1:]:
            if left["document_id"] == right["document_id"]:
                continue
            if document_id and document_id not in (left["document_id"], right["document_id"]):
                continue

            right_tokens = claim_tokens(right["claim"])
            if not right_tokens:
                continue
            shared_tokens = left_tokens & right_tokens
            similarity = len(shared_tokens) / max(len(left_tokens), len(right_tokens))
            if similarity == 1:
                relationship_type = "agreement"
                summary = "Both sources make the same claim."
            elif similarity >= 0.5:
                relationship_type = "difference"
                summary = "The sources discuss the same subject with different details."
            else:
                continue
            if relationship and relationship != relationship_type:
                continue

            comparisons.append(
                ComparisonResponse(
                    id=f"{left['id']}:{right['id']}",
                    relationship=relationship_type,
                    summary=summary,
                    left_document_id=left["document_id"],
                    left_document_name=left["document_name"],
                    left_claim=left["claim"],
                    left_page=left["source_page"],
                    left_source_text=left["source_text"],
                    right_document_id=right["document_id"],
                    right_document_name=right["document_name"],
                    right_claim=right["claim"],
                    right_page=right["source_page"],
                    right_source_text=right["source_text"],
                )
            )

    return comparisons
