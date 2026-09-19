from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def make_pdf(text: str) -> bytes:
    objects = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Contents 4 0 R /Resources << /Font << /F1 5 0 R >> >> >>",
        f"<< /Length {len(text) + 38} >>\nstream\nBT /F1 12 Tf 72 720 Td ({text}) Tj ET\nendstream".encode(),
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
    ]
    pdf = bytearray(b"%PDF-1.4\n")
    offsets = [0]
    for number, body in enumerate(objects, start=1):
        offsets.append(len(pdf))
        pdf.extend(f"{number} 0 obj\n".encode())
        pdf.extend(body)
        pdf.extend(b"\nendobj\n")
    xref_offset = len(pdf)
    pdf.extend(f"xref\n0 {len(objects) + 1}\n".encode())
    pdf.extend(b"0000000000 65535 f \n")
    for offset in offsets[1:]:
        pdf.extend(f"{offset:010d} 00000 n \n".encode())
    pdf.extend(
        f"trailer\n<< /Size {len(objects) + 1} /Root 1 0 R >>\nstartxref\n{xref_offset}\n%%EOF\n".encode()
    )
    return bytes(pdf)


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
    facts = facts_response.json()
    assert len(facts) == 1
    assert facts[0]["document_id"] == document["id"]
    assert facts[0]["source_page"] == 1
    assert "Revenue increased 20 percent." in facts[0]["source_text"]
