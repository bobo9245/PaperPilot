from __future__ import annotations

from datetime import datetime, timezone

import pytest

from paperpilot.models import Paper


@pytest.fixture
def make_paper():
    def factory(
        title: str = "Adaptive Retrieval Augmented Generation",
        summary: str = "A novel retrieval augmented generation method with experiments on 5 datasets.",
        source_id: str = "paper-1",
        source: str = "arxiv",
        doi: str | None = None,
        citation_count: int | None = None,
        venue: str | None = None,
    ) -> Paper:
        return Paper(
            title=title,
            authors=("Ada Lovelace", "Grace Hopper"),
            summary=summary,
            published=datetime(2026, 1, 10, tzinfo=timezone.utc),
            updated=datetime(2026, 1, 11, tzinfo=timezone.utc),
            url=f"https://arxiv.org/abs/{source_id}",
            pdf_url=f"https://arxiv.org/pdf/{source_id}",
            categories=("cs.CL",),
            source_id=source_id,
            source=source,
            doi=doi,
            citation_count=citation_count,
            venue=venue,
        )

    return factory
