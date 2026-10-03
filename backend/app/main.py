import os
import sqlite3
import re
import uuid
from datetime import datetime, timezone
from pathlib import Path

from fastapi import FastAPI, File, HTTPException, Query, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel
from app.extraction import extract_pages
from app.admission import MutationGate
from app.upload_storage import store_upload, UploadTooLarge
from app.storage import InvalidSource, resolve_source, migrate_source_references
from app.comparison_candidates import candidate_pairs, claim_tokens, normalized_claim

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = Path(os.environ.get("FACTFLOW_DATA_DIR", str(BASE_DIR / "data"))).resolve()
UPLOADS_DIR = DATA_DIR / "uploads"
DB_PATH = DATA_DIR / "factlayer.db"
MAX_UPLOAD_BYTES = 10 * 1024 * 1024
MAX_FILENAME_LENGTH = 120
SCHEMA_VERSION = 3
mutation_gate = MutationGate()


def init_db() -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    UPLOADS_DIR.mkdir(parents=True, exist_ok=True)

    with sqlite3.connect(DB_PATH) as connection:
        connection.execute("PRAGMA foreign_keys = ON")
        connection.execute("BEGIN IMMEDIATE")
        current_version = connection.execute("PRAGMA user_version").fetchone()[0]
        if current_version > SCHEMA_VERSION:
            raise ValueError("Database schema is newer than this application; use compatible code.")
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
        document_columns = {row[1] for row in connection.execute("PRAGMA table_info(documents)")}
        if "extraction_error" not in document_columns:
            connection.execute("ALTER TABLE documents ADD COLUMN extraction_error TEXT")
        fact_columns = {row[1] for row in connection.execute("PRAGMA table_info(facts)")}
        if "extraction_method" not in fact_columns:
            connection.execute("ALTER TABLE facts ADD COLUMN extraction_method TEXT NOT NULL DEFAULT 'native'")
        connection.execute("CREATE INDEX IF NOT EXISTS idx_facts_document_id ON facts (document_id)")
        connection.execute("CREATE INDEX IF NOT EXISTS idx_facts_created_at ON facts (created_at)")
        connection.execute("CREATE INDEX IF NOT EXISTS idx_documents_created_at ON documents (created_at)")
        if current_version < SCHEMA_VERSION:
            migrate_source_references(connection, UPLOADS_DIR)
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
    extraction_error: str | None = None


class DocumentPageResponse(BaseModel):
    items: list[DocumentResponse]
    total: int
    limit: int
    offset: int


class FactResponse(BaseModel):
    id: str
    document_id: str
    claim: str
    extraction_method: str = "native"
    document_status: str | None = None
    source_page: int
    source_text: str
    created_at: str


class FactPageResponse(BaseModel):
    items: list[FactResponse]
    total: int
    limit: int
    offset: int


class ComparisonResponse(BaseModel):
    id: str
    relationship: str
    summary: str
    left_document_id: str
    left_document_name: str
    left_document_status: str | None = None
    left_extraction_method: str = "native"
    left_claim: str
    left_page: int
    left_source_text: str
    right_document_id: str
    right_document_name: str
    right_document_status: str | None = None
    right_extraction_method: str = "native"
    right_claim: str
    right_page: int
    right_source_text: str


class ComparisonPageResponse(BaseModel):
    items: list[ComparisonResponse]
    total: int
    limit: int
    offset: int


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
    pages = extract_pages(file_path)
    extracted: list[FactResponse] = []
    seen_claims: set[str] = set()
    created_at = datetime.now(timezone.utc).isoformat()

    for page_number, page in enumerate(pages, start=1):
        claims = split_claims(page['text'])
        if not claims and page["method"] == "ocr":
            raise ValueError(f"Page {page_number} contains no usable claims; extraction is incomplete.")
        for claim in claims:
            normalized_claim = claim.casefold()
            if normalized_claim in seen_claims:
                continue
            seen_claims.add(normalized_claim)
            extracted.append(
                FactResponse(
                    id=str(uuid.uuid4()),
                    document_id=document_id,
                    claim=claim,
                    extraction_method=page["method"],
                    source_page=page_number,
                    source_text=claim,
                    created_at=created_at,
                )
            )

    if not extracted:
        raise ValueError("The PDF contains no extractable text")
    return extracted


def document_from_row(row: sqlite3.Row) -> DocumentResponse:
    try:
        stored_path = str(resolve_source(row["stored_path"], UPLOADS_DIR))
    except InvalidSource:
        stored_path = ""
    return DocumentResponse(
        id=row["id"],
        filename=row["filename"],
        size_bytes=row["size_bytes"],
        content_type=row["content_type"],
        stored_path=stored_path,
        created_at=row["created_at"],
        status=row["status"],
        extraction_error=row["extraction_error"],
    )


def get_document_row(document_id: str) -> sqlite3.Row:
    with get_connection() as connection:
        row = connection.execute(
            "SELECT id, filename, size_bytes, content_type, stored_path, created_at, status, extraction_error FROM documents WHERE id = ?",
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
                "UPDATE documents SET status = 'extraction_failed', extraction_error = ? WHERE id = ?",
                (str(error) if isinstance(error, ValueError) else "The PDF could not be processed.", document_id),
            )
            connection.commit()
        raise HTTPException(status_code=422, detail=str(error) if isinstance(error, ValueError) else "The PDF could not be processed") from error

    with get_connection() as connection:
        connection.execute("DELETE FROM facts WHERE document_id = ?", (document_id,))
        connection.executemany(
            "INSERT INTO facts (id, document_id, claim, source_page, source_text, created_at, extraction_method) VALUES (?, ?, ?, ?, ?, ?, ?)",
            [
                (fact.id, fact.document_id, fact.claim, fact.source_page, fact.source_text, fact.created_at, fact.extraction_method)
                for fact in facts
            ],
        )
        connection.execute(
            "UPDATE documents SET status = 'processed', extraction_error = NULL WHERE id = ?",
            (document_id,),
        )
        connection.commit()
    return facts


def safe_filename(filename: str) -> str:
    name = filename.replace("\\", "/").rsplit("/", 1)[-1].strip()
    if not name or name in {".", ".."}:
        raise HTTPException(status_code=400, detail="A valid filename is required")
    if len(name) > MAX_FILENAME_LENGTH:
        raise HTTPException(status_code=400, detail="The filename is too long")
    return name


@app.post("/documents", response_model=DocumentResponse)
async def upload_document(file: UploadFile = File(...)) -> DocumentResponse:
    with mutation_gate.reserve() as lease:
        if not file.filename:
            raise HTTPException(status_code=400, detail="A file is required")

        if not file.filename.lower().endswith(".pdf") or file.content_type != "application/pdf":
            raise HTTPException(status_code=415, detail="Only PDF documents are supported")

        safe_name = safe_filename(file.filename)
        document_id = str(uuid.uuid4())
        try:
            file_path = resolve_source(f"{document_id}_{safe_name}", UPLOADS_DIR)
        except InvalidSource as error:
            raise HTTPException(status_code=400, detail="Invalid filename") from error

        try:
            size_bytes = await store_upload(file, file_path, MAX_UPLOAD_BYTES)
        except UploadTooLarge as error:
            raise HTTPException(status_code=413, detail=str(error)) from error
        except OSError as error:
            raise HTTPException(status_code=500, detail="The uploaded PDF could not be stored. Please retry.") from error

        created_at = datetime.now(timezone.utc).isoformat()
        status = "uploaded"

        try:
            with get_connection() as connection:
                connection.execute(
                    """
                    INSERT INTO documents (id, filename, size_bytes, content_type, stored_path, created_at, status)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                    """,
                    (document_id, safe_name, size_bytes, file.content_type, file_path.name, created_at, status),
                )
                connection.commit()
        except sqlite3.Error as error:
            file_path.unlink(missing_ok=True)
            raise HTTPException(status_code=500, detail="The uploaded PDF could not be registered. Please retry.") from error

        return await lease.run_sync(finish_upload, document_id, file_path)


def finish_upload(document_id: str, file_path: Path) -> DocumentResponse:
    try:
        process_document(document_id, file_path)
    except HTTPException:
        with get_connection() as connection:
            connection.execute("UPDATE documents SET status = 'extraction_failed' WHERE id = ?", (document_id,))
            connection.commit()
    return document_from_row(get_document_row(document_id))


@app.get("/documents", response_model=DocumentPageResponse)
def list_documents(
    search: str = "",
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
) -> DocumentPageResponse:
    where = " WHERE filename LIKE ?" if search.strip() else ""
    parameters = [f"%{search.strip()}%"] if where else []
    with get_connection() as connection:
        total = connection.execute(f"SELECT COUNT(*) FROM documents{where}", parameters).fetchone()[0]
        rows = connection.execute(
            "SELECT id, filename, size_bytes, content_type, stored_path, created_at, status, extraction_error "
            f"FROM documents{where} ORDER BY created_at DESC, id ASC LIMIT ? OFFSET ?",
            [*parameters, limit, offset],
        ).fetchall()
    return DocumentPageResponse(items=[document_from_row(row) for row in rows], total=total, limit=limit, offset=offset)


@app.get("/documents/{document_id}", response_model=DocumentResponse)
def get_document(document_id: str) -> DocumentResponse:
    return document_from_row(get_document_row(document_id))


@app.post("/documents/{document_id}/process", response_model=DocumentResponse)
def reprocess_document(document_id: str) -> DocumentResponse:
    with mutation_gate.reserve():
        row = get_document_row(document_id)
        process_document(document_id, source_path(row))
        return document_from_row(get_document_row(document_id))


@app.get("/documents/{document_id}/source", response_class=FileResponse)
def get_document_source(document_id: str) -> FileResponse:
    row = get_document_row(document_id)
    path = source_path(row, status_code=404)
    if not path.is_file():
        raise HTTPException(status_code=404, detail="Source PDF not found")
    return FileResponse(
        path,
        media_type="application/pdf",
        filename=row["filename"],
        content_disposition_type="inline",
        headers={"X-Content-Type-Options": "nosniff"},
    )


def source_path(row: sqlite3.Row, status_code: int = 409) -> Path:
    try:
        return resolve_source(row["stored_path"], UPLOADS_DIR)
    except InvalidSource as error:
        raise HTTPException(status_code=status_code, detail="Invalid source reference") from error


@app.delete("/documents/{document_id}", status_code=204)
def delete_document(document_id: str) -> None:
    with mutation_gate.reserve():
        row = get_document_row(document_id)
        path = source_path(row)
        try:
            path.unlink(missing_ok=True)
        except OSError as error:
            raise HTTPException(status_code=409, detail="Source could not be removed; retry after checking file permissions.") from error
        with get_connection() as connection:
            connection.execute("DELETE FROM facts WHERE document_id = ?", (document_id,))
            connection.execute("DELETE FROM documents WHERE id = ?", (document_id,))
            connection.commit()


@app.get("/facts", response_model=FactPageResponse)
def list_facts(
    document_id: str | None = None,
    search: str | None = None,
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
) -> FactPageResponse:
    conditions: list[str] = []
    parameters: list[str | int] = []
    if document_id:
        conditions.append("document_id = ?")
        parameters.append(document_id)
    if search and search.strip():
        conditions.append("(LOWER(claim) LIKE ? OR LOWER(source_text) LIKE ?)")
        search_value = f"%{search.strip().lower()}%"
        parameters.extend([search_value, search_value])

    where_clause = f" WHERE {' AND '.join(conditions)}" if conditions else ""
    count_query = f"SELECT COUNT(*) FROM facts{where_clause}"
    query = (
        "SELECT id, document_id, claim, source_page, source_text, created_at, extraction_method, "
        "(SELECT status FROM documents WHERE documents.id = facts.document_id) AS document_status "
        f"FROM facts{where_clause} ORDER BY created_at DESC, source_page ASC, id ASC LIMIT ? OFFSET ?"
    )

    with get_connection() as connection:
        total = connection.execute(count_query, parameters).fetchone()[0]
        rows = connection.execute(query, [*parameters, limit, offset]).fetchall()

    return FactPageResponse(
        items=[
            FactResponse(
                id=row["id"],
                document_id=row["document_id"],
                claim=row["claim"],
                extraction_method=row["extraction_method"],
                document_status=row["document_status"],
                source_page=row["source_page"],
                source_text=row["source_text"],
                created_at=row["created_at"],
            )
            for row in rows
        ],
        total=total,
        limit=limit,
        offset=offset,
    )


@app.get("/comparisons", response_model=ComparisonPageResponse)
def list_comparisons(
    document_id: str | None = None,
    relationship: str | None = None,
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
) -> ComparisonPageResponse:
    if relationship not in (None, "agreement", "difference"):
        raise HTTPException(status_code=400, detail="Unsupported comparison relationship")

    with get_connection() as connection:
        rows = connection.execute(
            """
            SELECT facts.id, facts.document_id, facts.claim, facts.source_page, facts.source_text, facts.extraction_method,
                   documents.filename AS document_name, documents.status AS document_status
            FROM facts
            JOIN documents ON documents.id = facts.document_id
            ORDER BY facts.created_at DESC, facts.source_page ASC, facts.id ASC
            """
        ).fetchall()

    comparisons: list[ComparisonResponse] = []
    total = 0
    for left_index, right_index, relationship_type in candidate_pairs(rows, claim_tokens, normalized_claim, document_id):
        if relationship and relationship != relationship_type:
            continue
        total += 1
        if total <= offset or len(comparisons) >= limit:
            continue
        left, right = rows[left_index], rows[right_index]
        summary = (
            "Matching wording after normalizing case, spacing, and final sentence punctuation; not independent verification."
            if relationship_type == "agreement" else
            "Shared terms with different wording. Review both passages; this may not be a contradiction."
        )
        comparisons.append(
            ComparisonResponse(
                id=f"{left['id']}:{right['id']}",
                relationship=relationship_type,
                summary=summary,
                left_document_id=left["document_id"],
                left_document_name=left["document_name"],
                left_claim=left["claim"],
                left_document_status=left["document_status"],
                left_extraction_method=left["extraction_method"],
                left_page=left["source_page"],
                left_source_text=left["source_text"],
                right_document_id=right["document_id"],
                right_document_name=right["document_name"],
                right_claim=right["claim"],
                right_document_status=right["document_status"],
                right_extraction_method=right["extraction_method"],
                right_page=right["source_page"],
                right_source_text=right["source_text"],
            )
        )

    return ComparisonPageResponse(items=comparisons, total=total, limit=limit, offset=offset)
