from __future__ import annotations

from datetime import datetime, timezone

from paperpilot.tools.arxiv import build_arxiv_search_query, parse_arxiv_atom


def test_build_arxiv_search_query_uses_strict_title_abstract_terms() -> None:
    query = build_arxiv_search_query(
        "retrieval augmented generation",
        categories=("cs.CL", "cs.IR"),
        strict_search=True,
    )

    assert 'ti:"retrieval augmented generation"' in query
    assert 'abs:"retrieval augmented generation"' in query
    assert "(ti:retrieval OR abs:retrieval)" in query
    assert "(cat:cs.CL OR cat:cs.IR)" in query
    assert "all:retrieval" not in query


def test_build_arxiv_search_query_can_use_broad_and_search() -> None:
    query = build_arxiv_search_query("retrieval augmented generation", strict_search=False)

    assert query == "all:retrieval AND all:augmented AND all:generation"


def test_parse_arxiv_atom_filters_recent_entries() -> None:
    payload = """\
    <feed xmlns="http://www.w3.org/2005/Atom">
      <entry>
        <id>https://arxiv.org/abs/2601.00001</id>
        <updated>2026-01-09T00:00:00Z</updated>
        <published>2026-01-09T00:00:00Z</published>
        <title>Recent RAG Paper</title>
        <summary>Novel retrieval augmented generation benchmark with 10 tasks.</summary>
        <author><name>Ada</name></author>
        <category term="cs.CL" />
        <link href="https://arxiv.org/abs/2601.00001" rel="alternate" />
        <link href="https://arxiv.org/pdf/2601.00001" title="pdf" />
      </entry>
      <entry>
        <id>https://arxiv.org/abs/2501.00001</id>
        <updated>2025-01-01T00:00:00Z</updated>
        <published>2025-01-01T00:00:00Z</published>
        <title>Old RAG Paper</title>
        <summary>Older work.</summary>
        <author><name>Grace</name></author>
        <category term="cs.CL" />
        <link href="https://arxiv.org/abs/2501.00001" rel="alternate" />
      </entry>
    </feed>
    """

    papers = parse_arxiv_atom(
        payload,
        days=7,
        max_results=10,
        now=datetime(2026, 1, 10, tzinfo=timezone.utc),
    )

    assert len(papers) == 1
    assert papers[0].title == "Recent RAG Paper"
    assert papers[0].pdf_url == "https://arxiv.org/pdf/2601.00001"
    assert papers[0].categories == ("cs.CL",)
