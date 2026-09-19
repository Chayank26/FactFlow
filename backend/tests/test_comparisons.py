from fastapi.testclient import TestClient

from app.main import app
from tests.test_facts import make_pdf

client = TestClient(app)


def upload_pdf(filename: str, text: str) -> str:
    response = client.post(
        "/documents",
        files={"file": (filename, make_pdf(text), "application/pdf")},
    )
    assert response.status_code == 200, response.text
    return response.json()["id"]


def test_comparisons_relate_similar_claims_with_source_context():
    first_id = upload_pdf("source-a.pdf", "Revenue increased 20 percent.")
    second_id = upload_pdf("source-b.pdf", "Revenue increased 30 percent.")

    response = client.get("/comparisons")

    assert response.status_code == 200, response.text
    comparison = next(
        item for item in response.json()
        if {item["left_document_id"], item["right_document_id"]} == {first_id, second_id}
    )
    assert comparison["relationship"] == "difference"
    assert comparison["left_page"] == 1
    assert comparison["right_page"] == 1
    assert comparison["left_source_text"]
    assert comparison["right_source_text"]
