from pathlib import Path

from app.main import extract_facts
from tests.test_facts import make_pdf


def test_extraction_splits_sentences_skips_noise_and_deduplicates(tmp_path: Path):
    pdf_path = tmp_path / "quality.pdf"
    pdf_path.write_bytes(
        make_pdf(
            "Revenue increased 20 percent. Revenue increased 20 percent.\n"
            "--\n"
            "Revenue increased 30 percent."
        )
    )

    facts = extract_facts(pdf_path, "document-1")

    assert [fact.claim for fact in facts] == [
        "Revenue increased 20 percent.",
        "Revenue increased 30 percent.",
    ]
    assert all(fact.source_page == 1 for fact in facts)
    assert all(fact.source_text == fact.claim for fact in facts)
