from fastapi.testclient import TestClient

from app.main import app
from tests.test_facts import make_pdf

client = TestClient(app)


def upload_pdf(filename: str = "managed.pdf") -> dict:
    response = client.post(
        "/documents",
        files={"file": (filename, make_pdf("A documented claim."), "application/pdf")},
    )
    assert response.status_code == 200, response.text
    return response.json()


def test_document_detail_reprocess_and_delete():
    document = upload_pdf()
    document_id = document["id"]

    detail_response = client.get(f"/documents/{document_id}")
    assert detail_response.status_code == 200, detail_response.text
    assert detail_response.json()["id"] == document_id

    reprocess_response = client.post(f"/documents/{document_id}/process")
    assert reprocess_response.status_code == 200, reprocess_response.text
    assert reprocess_response.json()["status"] == "processed"

    delete_response = client.delete(f"/documents/{document_id}")
    assert delete_response.status_code == 204
    assert client.get(f"/documents/{document_id}").status_code == 404
    assert client.get("/facts", params={"document_id": document_id}).json() == []


def test_upload_validation_rejects_non_pdf_files():
    response = client.post(
        "/documents",
        files={"file": ("notes.txt", b"not a PDF", "text/plain")},
    )

    assert response.status_code == 415, response.text
