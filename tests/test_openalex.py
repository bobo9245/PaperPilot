from __future__ import annotations

from datetime import datetime, timezone

from paperpilot.tools.openalex import parse_openalex_response


def test_parse_openalex_response_normalizes_works() -> None:
    payload = {
        "results": [
            {
                "id": "https://openalex.org/W123",
                "doi": "https://doi.org/10.1234/openalex",
                "display_name": "OpenAlex Multimodal Retrieval Study",
                "publication_date": "2026-06-07",
                "authorships": [
                    {"author": {"display_name": "Ada Lovelace"}},
                    {"author": {"display_name": "Grace Hopper"}},
                ],
                "abstract_inverted_index": {
                    "We": [0],
                    "study": [1],
                    "multimodal": [2],
                    "retrieval": [3],
                },
                "best_oa_location": {
                    "pdf_url": "https://example.com/openalex.pdf",
                    "landing_page_url": "https://example.com/openalex",
                    "source": {"display_name": "ICLR"},
                },
                "cited_by_count": 12,
                "topics": [{"display_name": "Information Retrieval"}],
            }
        ]
    }

    papers = parse_openalex_response(
        payload,
        days=7,
        max_results=10,
        now=datetime(2026, 6, 9, tzinfo=timezone.utc),
    )

    assert len(papers) == 1
    paper = papers[0]
    assert paper.source == "openalex"
    assert paper.title == "OpenAlex Multimodal Retrieval Study"
    assert paper.summary == "We study multimodal retrieval"
    assert paper.authors == ("Ada Lovelace", "Grace Hopper")
    assert paper.pdf_url == "https://example.com/openalex.pdf"
    assert paper.doi == "10.1234/openalex"
    assert paper.citation_count == 12
    assert paper.venue == "ICLR"
