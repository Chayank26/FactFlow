from fastapi.testclient import TestClient

from app.main import app
from tests.test_facts import make_pdf

client = TestClient(app)


def test_pdf_without_extractable_text_has_explicit_status():
    response = client.post(
        "/documents",
        files={"file": ("empty.pdf", make_pdf(""), "application/pdf")},
    )

    assert response.status_code == 200, response.text
    document = response.json()
    assert document["status"] == "extraction_failed"
    assert client.get("/facts", params={"document_id": document["id"]}).json()["items"] == []
