from fastapi.testclient import TestClient

from app.main import app
from tests.test_facts import make_pdf

client = TestClient(app)


def test_facts_support_search_and_pagination_metadata():
    response = client.post(
        "/documents",
        files={
            "file": (
                "search.pdf",
                make_pdf("Revenue increased 20 percent. Costs decreased 5 percent."),
                "application/pdf",
            )
        },
    )
    assert response.status_code == 200, response.text

    document_id = response.json()["id"]
    search_response = client.get(
        "/facts",
        params={"document_id": document_id, "search": "revenue", "limit": 1, "offset": 0},
    )

    assert search_response.status_code == 200, search_response.text
    payload = search_response.json()
    assert payload["total"] == 1
    assert payload["limit"] == 1
    assert payload["offset"] == 0
    assert len(payload["items"]) == 1
    assert "Revenue" in payload["items"][0]["claim"]


def test_facts_reject_invalid_pagination():
    assert client.get("/facts", params={"limit": 0}).status_code == 422
    assert client.get("/facts", params={"offset": -1}).status_code == 422
