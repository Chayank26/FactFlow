from fastapi.testclient import TestClient

from app.main import app
from tests.test_facts import make_pdf

client = TestClient(app)


def test_upload_and_list_documents():
    response = client.post(
        "/documents",
        files={"file": ("sample.pdf", make_pdf("A meaningful claim."), "application/pdf")},
    )

    assert response.status_code == 200, response.text
    payload = response.json()
    assert payload["filename"] == "sample.pdf"
    assert payload["status"] == "processed"

    list_response = client.get("/documents")
    assert list_response.status_code == 200, list_response.text
    docs = list_response.json()
    assert any(doc["filename"] == "sample.pdf" for doc in docs)
