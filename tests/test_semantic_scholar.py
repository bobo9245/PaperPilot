from __future__ import annotations

from datetime import datetime, timezone

from paperpilot.tools.semantic_scholar import parse_semantic_scholar_response


def test_parse_semantic_scholar_response_normalizes_papers() -> None:
    payload = {
        "data": [
            {
                "paperId": "abc123",
                "title": "Multimodal RAG for Enterprise QA",
                "abstract": "We introduce a multimodal retrieval augmented generation system.",
                "authors": [{"name": "Ada Lovelace"}, {"name": "Grace Hopper"}],
                "url": "https://www.semanticscholar.org/paper/abc123",
                "publicationDate": "2026-06-08",
                "openAccessPdf": {"url": "https://example.com/paper.pdf"},
                "externalIds": {"DOI": "10.1234/example", "ArXiv": "2606.00001"},
                "citationCount": 7,
                "venue": "ACL",
                "fieldsOfStudy": ["Computer Science"],
            }
        ]
    }

    papers = parse_semantic_scholar_response(
        payload,
        days=7,
        max_results=10,
        now=datetime(2026, 6, 9, tzinfo=timezone.utc),
    )

    assert len(papers) == 1
    paper = papers[0]
    assert paper.source == "semantic-scholar"
    assert paper.title == "Multimodal RAG for Enterprise QA"
    assert paper.authors == ("Ada Lovelace", "Grace Hopper")
    assert paper.pdf_url == "https://example.com/paper.pdf"
    assert paper.doi == "10.1234/example"
    assert paper.citation_count == 7
    assert paper.venue == "ACL"
