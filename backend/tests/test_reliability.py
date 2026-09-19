import sqlite3

import pytest
from fastapi.testclient import TestClient

from app.main import MAX_UPLOAD_BYTES, app, get_connection

client = TestClient(app)


def test_missing_document_operations_return_not_found():
    missing_id = "missing-document"

    assert client.get(f"/documents/{missing_id}").status_code == 404
    assert client.post(f"/documents/{missing_id}/process").status_code == 404
    assert client.delete(f"/documents/{missing_id}").status_code == 404


def test_malformed_pdf_is_retained_with_failed_status():
    response = client.post(
        "/documents",
        files={"file": ("broken.pdf", b"not a real PDF", "application/pdf")},
    )

    assert response.status_code == 200, response.text
    document = response.json()
    assert document["status"] == "extraction_failed"
    assert client.get(f"/documents/{document['id']}").json()["status"] == "extraction_failed"


def test_oversized_upload_is_rejected_before_storage():
    response = client.post(
        "/documents",
        files={"file": ("large.pdf", b"x" * (MAX_UPLOAD_BYTES + 1), "application/pdf")},
    )

    assert response.status_code == 413, response.text


def test_database_enforces_document_fact_relationship():
    with get_connection() as connection:
        with pytest.raises(sqlite3.IntegrityError):
            connection.execute(
                "INSERT INTO facts (id, document_id, claim, source_page, source_text, created_at) VALUES (?, ?, ?, ?, ?, ?)",
                ("orphan", "missing-document", "claim", 1, "claim", "now"),
            )
