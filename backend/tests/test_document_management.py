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
    assert client.get("/facts", params={"document_id": document_id}).json()["items"] == []


def test_upload_validation_rejects_non_pdf_files():
    response = client.post(
        "/documents",
        files={"file": ("notes.txt", b"not a PDF", "text/plain")},
    )

    assert response.status_code == 415, response.text


def test_failed_reprocessing_preserves_evidence_until_successful_retry():
    from pathlib import Path

    document = upload_pdf()
    document_id = document['id']
    path = Path(document['stored_path'])
    original_bytes = path.read_bytes()
    before = client.get('/facts', params={'document_id': document_id}).json()
    path.write_bytes(b'broken PDF')
    assert client.post(f'/documents/{document_id}/process').status_code == 422
    assert client.get(f'/documents/{document_id}').json()['status'] == 'extraction_failed'
    assert client.get('/facts', params={'document_id': document_id}).json() == before
    path.write_bytes(original_bytes)
    assert client.post(f'/documents/{document_id}/process').json()['status'] == 'processed'
    after = client.get('/facts', params={'document_id': document_id}).json()
    assert after['total'] == before['total']
    assert after['items'][0]['claim'] == before['items'][0]['claim']
    assert after['items'][0]['id'] != before['items'][0]['id']
