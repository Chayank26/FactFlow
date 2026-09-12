import sqlite3
import uuid
from datetime import datetime, timezone
from pathlib import Path

from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

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


@app.get("/health", response_model=HealthResponse)
def health() -> HealthResponse:
    return HealthResponse(status="ok", service="fact-layer-api")


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
    with get_connection() as connection:
        connection.execute(
            """
            INSERT INTO documents (id, filename, size_bytes, content_type, stored_path, created_at, status)
            VALUES (?, ?, ?, ?, ?, ?, 'uploaded')
            """,
            (
                document_id,
                safe_name,
                len(content),
                file.content_type,
                str(file_path),
                created_at,
            ),
        )
        connection.commit()

    return DocumentResponse(
        id=document_id,
        filename=safe_name,
        size_bytes=len(content),
        content_type=file.content_type,
        stored_path=str(file_path),
        created_at=created_at,
        status="uploaded",
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
