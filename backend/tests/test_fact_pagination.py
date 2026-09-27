from fastapi.testclient import TestClient

from app.main import app, get_connection
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
    assert client.get("/facts", params={"limit": 101}).status_code == 422
    assert client.get("/facts", params={"offset": -1}).status_code == 422


def test_all_document_evidence_is_reachable_in_stable_pages():
    claims = [f"Revenue metric {index} increased significantly." for index in range(65)]
    response = client.post(
        "/documents",
        files={"file": ("many-facts.pdf", make_pdf(" ".join(claims)), "application/pdf")},
    )
    assert response.status_code == 200, response.text
    document_id = response.json()["id"]
    # Every extracted fact has the same timestamp and page. Insert in reverse ID
    # order so the test distinguishes an explicit tie-breaker from insertion order.
    with get_connection() as connection:
        rows = connection.execute("SELECT * FROM facts WHERE document_id = ? ORDER BY id DESC", (document_id,)).fetchall()
        assert len(rows) == 65
        connection.execute("DELETE FROM facts WHERE document_id = ?", (document_id,))
        connection.executemany(
            "INSERT INTO facts (id, document_id, claim, source_page, source_text, created_at) VALUES (?, ?, ?, ?, ?, ?)",
            [tuple(row) for row in rows],
        )

    pages = []
    for offset in range(0, 65, 20):
        params = {"document_id": document_id, "limit": 20, "offset": offset}
        page = client.get("/facts", params=params).json()
        assert page["total"] == 65
        assert page["offset"] == offset
        assert page["limit"] == 20
        assert len(page["items"]) == min(20, 65 - offset)
        assert client.get("/facts", params=params).json() == page
        pages.extend(page["items"])

    ids = [fact["id"] for fact in pages]
    assert ids == sorted(row["id"] for row in rows)
    assert len(set(ids)) == 65
    assert {fact["claim"] for fact in pages} == set(claims)
    beyond = client.get("/facts", params={"document_id": document_id, "offset": 80}).json()
    assert beyond["items"] == []
    assert beyond["total"] == 65
