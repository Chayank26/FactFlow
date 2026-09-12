from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_upload_and_list_documents():
    response = client.post(
        "/documents",
        files={"file": ("sample.txt", b"hello world", "text/plain")},
    )

    assert response.status_code == 200, response.text
    payload = response.json()
    assert payload["filename"] == "sample.txt"
    assert payload["size_bytes"] == 11
    assert payload["status"] == "uploaded"

    list_response = client.get("/documents")
    assert list_response.status_code == 200, list_response.text
    docs = list_response.json()
    assert any(doc["filename"] == "sample.txt" for doc in docs)
