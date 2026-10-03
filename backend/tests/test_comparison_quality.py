import pytest
from fastapi.testclient import TestClient

from app.main import app
from tests.test_comparisons import upload_pdf

client = TestClient(app)


@pytest.mark.parametrize(
    "left,right,expected",
    [
        ("Revenue increased 20 percent.", "REVENUE increased 20 percent!", "agreement"),
        ("Revenue increased 20 percent.", "Revenue   increased 20 percent.", "agreement"),
        ("Company A acquired Company B.", "Company B acquired Company A.", "difference"),
        ("Revenue increased 20 percent.", "Revenue did not increase 20 percent.", "difference"),
        ("Revenue increased 20 percent.", "Revenue increased 30 percent.", "difference"),
        ("The dose was 5 mg.", "The dose was 5 g.", "difference"),
        ("The balance changed by +20 dollars.", "The balance changed by -20 dollars.", "difference"),
        ("Revenue rose very significantly.", "Revenue rose very very significantly.", "difference"),
        ("The cat is on the mat.", "The report is in the office.", None),
        ("Revenue increased 20 percent.", "Rainfall reached record levels.", None),
    ],
)
def test_comparison_classification_preserves_meaningful_wording(left, right, expected):
    first = upload_pdf("first.pdf", left)
    second = upload_pdf("second.pdf", right)
    response = client.get("/comparisons")
    assert response.status_code == 200
    pairs = response.json()["items"]
    if expected is None:
        assert pairs == []
        return
    assert len(pairs) == 1
    pair = pairs[0]
    assert pair["relationship"] == expected
    assert {pair["left_document_id"], pair["right_document_id"]} == {first, second}
    assert pair["left_page"] == pair["right_page"] == 1
    assert {pair["left_claim"], pair["right_claim"]} == {pair["left_source_text"], pair["right_source_text"]}
    assert client.get("/comparisons", params={"relationship": expected, "document_id": first}).json()["items"] == pairs
    other = "difference" if expected == "agreement" else "agreement"
    assert client.get("/comparisons", params={"relationship": other}).json()["items"] == []
    assert client.get("/comparisons").json()["items"] == pairs


def test_similar_claims_in_one_document_are_not_compared():
    upload_pdf("single.pdf", "Revenue increased 20 percent. Revenue increased 30 percent.")
    assert client.get("/comparisons").json()["items"] == []
