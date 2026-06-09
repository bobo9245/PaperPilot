"""Reviewer agent for ranking paper candidates."""

from __future__ import annotations

import re
from datetime import datetime, timezone

from paperpilot.models import Paper, ReviewedPaper, ReviewScore


class ReviewerAgent:
    """Score papers for relevance, novelty, and experimental strength."""

    def rank(
        self,
        papers: tuple[Paper, ...] | list[Paper],
        *,
        query: str,
        min_relevance: float = 0.0,
        now: datetime | None = None,
    ) -> tuple[ReviewedPaper, ...]:
        if not 0 <= min_relevance <= 1:
            raise ValueError("min_relevance must be between 0 and 1")

        reviewed = [ReviewedPaper(paper=paper, score=self.score(paper, query=query, now=now)) for paper in papers]
        eligible = [item for item in reviewed if item.score.relevance >= min_relevance]
        return tuple(
            sorted(
                eligible,
                key=lambda item: (item.score.total, item.score.relevance, item.paper.published),
                reverse=True,
            )
        )

    def score(self, paper: Paper, *, query: str, now: datetime | None = None) -> ReviewScore:
        text = _paper_text(paper)
        relevance = _score_relevance(text, query)
        novelty = _score_novelty(text, paper, now=now)
        experimental_strength = _score_experiments(text)
        total = round((0.60 * relevance) + (0.20 * novelty) + (0.20 * experimental_strength), 3)
        reason = _reason(relevance, novelty, experimental_strength)
        return ReviewScore(
            relevance=relevance,
            novelty=novelty,
            experimental_strength=experimental_strength,
            total=total,
            reason=reason,
        )


def _paper_text(paper: Paper) -> str:
    return " ".join([paper.title, paper.summary, " ".join(paper.categories)]).lower()


def _score_relevance(text: str, query: str) -> float:
    query_terms = [
        term
        for term in re.findall(r"[a-z0-9]+", query.lower())
        if len(term) > 2 and term not in _STOPWORDS
    ]
    if not query_terms:
        return 0.5

    text_terms = set(re.findall(r"[a-z0-9]+", text))
    hits = sum(1 for term in query_terms if term in text_terms)
    base_score = hits / len(query_terms)

    normalized_text = " ".join(re.findall(r"[a-z0-9]+", text))
    phrase = " ".join(query_terms)
    phrase_bonus = 0.15 if len(query_terms) > 1 and phrase in normalized_text else 0.0
    return round(min(1.0, base_score + phrase_bonus), 3)


def _score_novelty(text: str, paper: Paper, *, now: datetime | None) -> float:
    signals = sum(1 for token in _NOVELTY_SIGNALS if token in text)
    signal_score = min(0.85, 0.25 + signals * 0.15)

    reference = _as_utc(now)
    age_days = max(0, (reference - paper.published.astimezone(timezone.utc)).days)
    recency_bonus = 0.15 if age_days <= 90 else 0.08 if age_days <= 365 else 0.0
    return round(min(1.0, signal_score + recency_bonus), 3)


def _score_experiments(text: str) -> float:
    signals = sum(1 for token in _EXPERIMENT_SIGNALS if token in text)
    has_number = bool(re.search(r"\b\d+(\.\d+)?\b|%", text))
    score = 0.2 + signals * 0.12 + (0.2 if has_number else 0.0)
    return round(min(1.0, score), 3)


def _reason(relevance: float, novelty: float, experimental_strength: float) -> str:
    reasons: list[str] = []
    if relevance >= 0.75:
        reasons.append("query terms are strongly represented")
    elif relevance >= 0.4:
        reasons.append("partially matches the query")
    else:
        reasons.append("weak query match")

    if novelty >= 0.6:
        reasons.append("contains novelty or recent-contribution signals")
    else:
        reasons.append("novelty is not explicit from the abstract")

    if experimental_strength >= 0.6:
        reasons.append("reports evaluation or quantitative evidence")
    else:
        reasons.append("experimental evidence looks limited from the abstract")

    return "; ".join(reasons)


def _as_utc(value: datetime | None) -> datetime:
    if value is None:
        return datetime.now(timezone.utc)
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


_STOPWORDS = {
    "and",
    "for",
    "from",
    "into",
    "the",
    "this",
    "that",
    "with",
}

_NOVELTY_SIGNALS = {
    "new",
    "novel",
    "introduce",
    "introduces",
    "propose",
    "proposes",
    "first",
    "state-of-the-art",
    "framework",
    "benchmark",
}

_EXPERIMENT_SIGNALS = {
    "ablation",
    "benchmark",
    "dataset",
    "datasets",
    "evaluation",
    "experiment",
    "experiments",
    "f1",
    "human evaluation",
    "latency",
    "results",
    "accuracy",
}
