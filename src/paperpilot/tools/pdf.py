"""PDF evidence extraction for selected papers."""

from __future__ import annotations

import re
from io import BytesIO
from urllib.error import URLError
from urllib.request import Request, urlopen

from paperpilot.models import Paper, PaperEvidence, PaperEvidenceSection


class PdfEvidenceExtractor:
    """Download a selected paper PDF and extract a bounded text sample."""

    def __init__(self, *, timeout: float = 30.0, user_agent: str = "paperpilot/0.1") -> None:
        self.timeout = timeout
        self.user_agent = user_agent

    def fetch(
        self,
        paper: Paper,
        *,
        max_pages: int = 6,
        max_chars: int = 16_000,
    ) -> PaperEvidence:
        if max_pages < 1:
            raise ValueError("max_pages must be at least 1")
        if not paper.pdf_url:
            return PaperEvidence(source="pdf", error="paper has no PDF URL")

        try:
            payload = self._download(paper.pdf_url)
            return extract_pdf_evidence(
                payload,
                max_pages=max_pages,
                max_chars=max_chars,
            )
        except Exception as exc:
            return PaperEvidence(source="pdf", error=f"PDF extraction failed: {exc}")

    def _download(self, url: str) -> bytes:
        request = Request(url, headers={"User-Agent": self.user_agent})
        try:
            with urlopen(request, timeout=self.timeout) as response:
                return response.read()
        except URLError as exc:
            raise RuntimeError(f"PDF request failed: {exc}") from exc
        except OSError as exc:
            raise RuntimeError(f"PDF request failed: {exc}") from exc


def extract_pdf_evidence(
    payload: bytes,
    *,
    max_pages: int = 6,
    max_chars: int = 16_000,
) -> PaperEvidence:
    """Extract text from PDF bytes."""

    try:
        from pypdf import PdfReader
    except ImportError as exc:
        raise RuntimeError("pypdf is required for PDF extraction") from exc

    reader = PdfReader(BytesIO(payload))
    total_pages = len(reader.pages)
    pages_to_read = min(max_pages, total_pages)
    parts: list[str] = []
    for page in reader.pages[:pages_to_read]:
        parts.append(page.extract_text() or "")

    text = clean_pdf_text("\n".join(parts))[:max_chars].strip()
    if not text:
        return PaperEvidence(
            source="pdf",
            pages_read=pages_to_read,
            total_pages=total_pages,
            error="no extractable text found in selected PDF pages",
        )
    return PaperEvidence(
        source="pdf",
        text=text,
        sections=extract_sections(text),
        pages_read=pages_to_read,
        total_pages=total_pages,
    )


def clean_pdf_text(text: str) -> str:
    """Normalize common PDF extraction whitespace noise."""

    lines = [" ".join(line.split()) for line in text.splitlines()]
    compact_lines = [line for line in lines if line]
    compact = "\n".join(compact_lines)
    compact = re.sub(r"(?<=[a-z])-\s+([a-z][A-Za-z-]*)", _repair_lowercase_hyphen, compact)
    compact = re.sub(r"(?<=\w)-\s+(?=\w)", "-", compact)
    compact = re.sub(r"\s+([,.;:])", r"\1", compact)
    compact = re.sub(r"([:;])(?=\S)", r"\1 ", compact)
    compact = re.sub(r"(?<=[a-z])\.(?=[A-Z])", ". ", compact)
    compact = re.sub(r"(RAG|LLM|MLLM|VQA|QA|OCR)(?=[a-z])", r"\1 ", compact)
    compact = re.sub(r"\b(introduce|introduces|introduced|propose|proposes|present|presents)(?=[A-Z])", r"\1 ", compact)
    compact = re.sub(r"\b(study)(?=(?:comprising|that)\b)", r"\1 ", compact, flags=re.IGNORECASE)
    compact = re.sub(r"\b(The|This|These|Those)(?=[A-Z][a-z])", r"\1 ", compact)
    compact = re.sub(r"\b(within|up to|by)(?=\d)", r"\1 ", compact)
    compact = re.sub(r"\b(attracted|reach|includes?|contains?|relevant)(?=\d)", r"\1 ", compact, flags=re.IGNORECASE)
    compact = re.sub(r"\brelevant(?=pages?)", "relevant ", compact, flags=re.IGNORECASE)
    compact = re.sub(r"\b(pages?|documents?|items?)(of|that|with)\b", r"\1 \2", compact, flags=re.IGNORECASE)
    compact = re.sub(r"\b(\d+(?:\.\d+)?)(point|points|percent)\b", r"\1 \2", compact)
    compact = re.sub(r"\b(\d+(?:\.\d+)?)(teams?|participants?|submissions?|items?)\b", r"\1 \2", compact)
    compact = re.sub(r"\bLLM s\b", "LLMs", compact)
    compact = re.sub(
        r"\b(split|reports?|pipelines?)(?=(?:that|every|text)\b)",
        r"\1 ",
        compact,
        flags=re.IGNORECASE,
    )
    compact = re.sub(
        r"\ba(?=(?:single|document|controlled|layout|page|table|text|vision|retrieval)\b)",
        "a ",
        compact,
    )
    compact = re.sub(
        r"\b(layout|structure|vision|text|image)aware\b",
        r"\1-aware",
        compact,
        flags=re.IGNORECASE,
    )
    return compact


def extract_sections(text: str) -> tuple[PaperEvidenceSection, ...]:
    """Extract coarse paper sections from normalized PDF text."""

    markers = _section_markers(text)
    if not markers:
        return ()

    sections: list[PaperEvidenceSection] = []
    for index, (start, heading, label) in enumerate(markers):
        end = markers[index + 1][0] if index + 1 < len(markers) else len(text)
        body = text[start:end].strip()
        if len(body) < 40:
            continue
        sections.append(
            PaperEvidenceSection(
                label=label,
                heading=heading,
                text=body,
            )
        )
    return tuple(sections)


def _section_markers(text: str) -> list[tuple[int, str, str]]:
    markers: list[tuple[int, str, str]] = []
    for match in re.finditer(r"(?m)(?:^|\n)\s*(?:\d+(?:\.\d+)?\s+)?([A-Z][A-Za-z][A-Za-z /&-]{2,60})\s*(?=\n|$)", text):
        heading = " ".join(match.group(1).split())
        label = _section_label(heading)
        if not label:
            continue
        markers.append((match.start(), heading, label))
    return _dedupe_markers(markers)


def _section_label(heading: str) -> str | None:
    normalized = re.sub(r"[^a-z0-9]+", " ", heading.lower()).strip()
    if normalized in {"abstract"}:
        return "abstract"
    if normalized in {"introduction", "background"}:
        return "introduction"
    if any(token in normalized for token in ("method", "approach", "architecture", "system", "model", "framework")):
        return "method"
    if any(token in normalized for token in ("experiment", "evaluation", "result", "benchmark")):
        return "experiments"
    if any(token in normalized for token in ("discussion", "limitation", "future work", "conclusion")):
        return "limitations"
    if any(token in normalized for token in ("task", "dataset", "challenge")):
        return "benchmark"
    return None


def _dedupe_markers(markers: list[tuple[int, str, str]]) -> list[tuple[int, str, str]]:
    deduped: list[tuple[int, str, str]] = []
    seen_positions: set[int] = set()
    for marker in sorted(markers, key=lambda item: item[0]):
        position, heading, label = marker
        if position in seen_positions:
            continue
        if deduped and deduped[-1][2] == label and position - deduped[-1][0] < 120:
            continue
        seen_positions.add(position)
        deduped.append((position, heading, label))
    return deduped


def _repair_lowercase_hyphen(match: re.Match[str]) -> str:
    token = match.group(1)
    return f"-{token}" if "-" in token else token
