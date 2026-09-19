from fastapi.testclient import TestClient

from app.main import app
from tests.test_comparisons import upload_pdf

client = TestClient(app)


def test_comparisons_filter_by_document_and_relationship():
    first_id = upload_pdf("filter-a.pdf", "Revenue increased 20 percent.")
    second_id = upload_pdf("filter-b.pdf", "Revenue increased 30 percent.")

    document_response = client.get("/comparisons", params={"document_id": first_id})
    assert document_response.status_code == 200, document_response.text
    document_results = document_response.json()
    assert document_results
    assert all(
        first_id in {item["left_document_id"], item["right_document_id"]}
        for item in document_results
    )

    relationship_response = client.get("/comparisons", params={"relationship": "agreement"})
    assert relationship_response.status_code == 200, relationship_response.text
    assert all(item["relationship"] == "agreement" for item in relationship_response.json())

    invalid_response = client.get("/comparisons", params={"relationship": "unknown"})
    assert invalid_response.status_code == 400
