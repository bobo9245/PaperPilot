"""Deterministic query expansion for paper discovery."""

from __future__ import annotations

import re


class QueryPlannerAgent:
    """Create bounded search query variants without calling an LLM."""

    def __init__(self, *, mode: str = "basic", max_variants: int = 6) -> None:
        if mode not in {"off", "basic"}:
            raise ValueError("query_expansion must be one of: off, basic")
        if max_variants < 1:
            raise ValueError("max_query_variants must be at least 1")
        self.mode = mode
        self.max_variants = max_variants

    def plan(self, query: str) -> tuple[str, ...]:
        cleaned = _clean_query(query)
        if not cleaned:
            raise ValueError("query is required")
        if self.mode == "off":
            return (cleaned,)

        candidates = [cleaned]
        for candidate in _domain_variants(cleaned):
            _append_unique(candidates, candidate)
            if len(candidates) >= self.max_variants:
                return tuple(candidates)
        for candidate in _broader_variants(cleaned):
            _append_unique(candidates, candidate)
            if len(candidates) >= self.max_variants:
                break
        return tuple(candidates)


def _domain_variants(query: str) -> tuple[str, ...]:
    normalized = query.lower()
    variants: list[str] = []

    has_rag_phrase = "retrieval augmented generation" in normalized
    has_rag = has_rag_phrase or re.search(r"\brag\b", normalized) is not None
    has_multimodal = "multimodal" in normalized or "multi-modal" in normalized

    if "dllm" in normalized:
        variants.append(re.sub(r"\bdllm\b", "diffusion language model", normalized, flags=re.IGNORECASE))
        if "unlearning" in normalized:
            variants.extend(_dlm_unlearning_variants(query))

    if "diffusion language model" in normalized:
        variants.append(re.sub("diffusion language model", "DLM", query, flags=re.IGNORECASE))
        if "unlearning" in normalized:
            variants.extend(_dlm_unlearning_variants(query))

    if has_rag_phrase:
        variants.append(re.sub("retrieval augmented generation", "RAG", query, flags=re.IGNORECASE))

    if has_multimodal and has_rag:
        variants.extend(
            [
                "multimodal RAG",
                "multi-modal retrieval augmented generation",
                "vision-language RAG",
                "multimodal document retrieval",
                "document question answering retrieval",
                "multimodal RAG benchmark",
            ]
        )
    elif has_rag:
        variants.extend(
            [
                "RAG evaluation",
                "retrieval augmented generation benchmark",
                "document question answering retrieval",
            ]
        )
    elif has_multimodal:
        variants.extend(
            [
                "multimodal document retrieval",
                "vision-language document QA",
                "document VQA",
            ]
        )

    return tuple(variants)


def _dlm_unlearning_variants(query: str) -> tuple[str, ...]:
    return (
        "diffusion language model unlearning",
        "discrete diffusion language model unlearning",
        "language model unlearning",
        "LLM unlearning",
        "machine unlearning language models",
        "diffusion model unlearning text generation",
    )


def _broader_variants(query: str) -> tuple[str, ...]:
    terms = [
        term
        for term in re.findall(r"[A-Za-z0-9]+", query.lower())
        if len(term) > 1 and term not in _STOPWORDS
    ]
    if not terms:
        return ()

    candidates: list[str] = []
    if len(terms) > 3:
        candidates.append(" ".join(terms[:3]))
    if len(terms) > 2:
        candidates.append(" ".join(terms[:2]))
    if terms:
        candidates.append(terms[0])
    return tuple(candidates)


def _append_unique(candidates: list[str], query: str) -> None:
    cleaned = _clean_query(query)
    if not cleaned:
        return
    seen = {_normalize_for_dedupe(candidate) for candidate in candidates}
    if _normalize_for_dedupe(cleaned) not in seen:
        candidates.append(cleaned)


def _clean_query(query: str) -> str:
    return " ".join(query.split())


def _normalize_for_dedupe(query: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", query.lower()).strip()


_STOPWORDS = {
    "a",
    "an",
    "and",
    "are",
    "as",
    "at",
    "for",
    "from",
    "in",
    "into",
    "of",
    "on",
    "or",
    "the",
    "to",
    "with",
}
