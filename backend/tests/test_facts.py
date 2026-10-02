from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


from tests.pdf_fixtures import make_pdf


def test_pdf_upload_extracts_facts_with_source_reference():
    response = client.post(
        "/documents",
        files={"file": ("evidence.pdf", make_pdf("Revenue increased 20 percent."), "application/pdf")},
    )

    assert response.status_code == 200, response.text
    document = response.json()
    assert document["status"] == "processed"

    facts_response = client.get("/facts", params={"document_id": document["id"]})

    assert facts_response.status_code == 200, facts_response.text
    facts = facts_response.json()["items"]
    assert len(facts) == 1
    assert facts[0]["document_id"] == document["id"]
    assert facts[0]["source_page"] == 1
    assert "Revenue increased 20 percent." in facts[0]["source_text"]
