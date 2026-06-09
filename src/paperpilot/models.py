"""Shared data models for the PaperPilot workflow."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path


@dataclass(frozen=True)
class Paper:
    """A normalized paper candidate."""

    title: str
    authors: tuple[str, ...]
    summary: str
    published: datetime
    updated: datetime | None
    url: str
    pdf_url: str | None = None
    categories: tuple[str, ...] = ()
    source_id: str | None = None

    @property
    def authors_text(self) -> str:
        return ", ".join(self.authors) if self.authors else "Unknown authors"


@dataclass(frozen=True)
class SearchAttempt:
    """One search observation from the search/replanning loop."""

    query: str
    status: str
    results_count: int
    message: str


@dataclass(frozen=True)
class SearchResult:
    """The output of a search agent run."""

    original_query: str
    papers: tuple[Paper, ...]
    attempts: tuple[SearchAttempt, ...]


@dataclass(frozen=True)
class ReviewScore:
    """Reviewer scores for a paper candidate."""

    relevance: float
    novelty: float
    experimental_strength: float
    total: float
    reason: str


@dataclass(frozen=True)
class ReviewedPaper:
    """A paper paired with its reviewer score."""

    paper: Paper
    score: ReviewScore


@dataclass(frozen=True)
class ReflectionResult:
    """Quality gate result for a generated summary."""

    passed: bool
    issues: tuple[str, ...] = ()


@dataclass(frozen=True)
class PaperSummary:
    """Korean five-part paper summary."""

    problem: str
    contribution: str
    method: str
    experiments: str
    limitations: str
    reflection: ReflectionResult = field(
        default_factory=lambda: ReflectionResult(passed=True)
    )

    def as_markdown(self) -> str:
        sections = [
            ("1. 왜 중요한가", self.problem),
            ("2. 핵심 기여", self.contribution),
            ("3. 방법", self.method),
            ("4. 실험/결과", self.experiments),
            ("5. 한계와 확인 필요", self.limitations),
        ]
        return "\n".join(f"### {title}\n\n{body}" for title, body in sections)


@dataclass(frozen=True)
class PaperEvidenceSection:
    """A normalized section extracted from PDF text."""

    label: str
    heading: str
    text: str


@dataclass(frozen=True)
class PaperEvidence:
    """Additional evidence extracted from a paper PDF."""

    source: str
    text: str = ""
    sections: tuple[PaperEvidenceSection, ...] = ()
    pages_read: int = 0
    total_pages: int | None = None
    error: str | None = None

    @property
    def available(self) -> bool:
        return bool(self.text.strip()) and self.error is None


@dataclass(frozen=True)
class SelectedPaper:
    """A fully curated paper entry."""

    reviewed: ReviewedPaper
    summary: PaperSummary
    evidence: PaperEvidence | None = None


@dataclass(frozen=True)
class CurationReport:
    """The final curation report."""

    query: str
    generated_at: datetime
    attempts: tuple[SearchAttempt, ...]
    selected: tuple[SelectedPaper, ...]
    output_path: Path | None = None
    min_relevance: float | None = None
    categories: tuple[str, ...] = ()
    strict_search: bool | None = None
    with_pdf: bool = False
    pdf_max_pages: int | None = None
    pdf_max_chars: int | None = None
    summary_backend: str = "heuristic"
    summary_model: str | None = None
    summary_detail: str = "standard"
    summary_fallback_reason: str | None = None
