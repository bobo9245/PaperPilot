"""Summarizer agent with a reflection quality gate."""

from __future__ import annotations

import json
import os
import re
from typing import Any, Protocol
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from paperpilot.models import Paper, PaperEvidence, PaperSummary, ReflectionResult, ReviewScore


DEFAULT_OPENAI_MODEL = "gpt-5.2"
DEFAULT_FACTCHAT_MODEL = "auto"
FACTCHAT_BASE_URL = "https://factchat-cloud.mindlogic.ai/v1/gateway"
FACTCHAT_MODEL_PREFERENCES = (
    "claude-sonnet-4-6",
    "claude-sonnet-4-5-20250929",
    "claude-haiku-4-5-20251001",
    "gemini-2.5-flash",
    "gemini-2.5-pro",
    "gemini-3-pro-preview",
    "gpt-5.1-chat-latest",
    "gpt-5.1",
    "gpt-5-mini",
    "gpt-5",
    "accounts/fireworks/models/gpt-oss-120b",
    "grok-3-mini",
    "google/gemma-3-27b-it",
    "accounts/fireworks/models/llama4-maverick-instruct-basic",
    "accounts/fireworks/models/llama4-scout-instruct-basic",
)
SUMMARY_DETAIL_LEVELS = {"standard", "deep", "ultra"}


class SummaryBackendError(RuntimeError):
    """Raised when a summary backend cannot produce a valid summary."""


class SummaryBackend(Protocol):
    """Backend interface for producing paper summaries."""

    name: str
    model: str | None
    fallback_reason: str | None

    def summarize(
        self,
        paper: Paper,
        score: ReviewScore,
        *,
        evidence: PaperEvidence | None = None,
    ) -> PaperSummary:
        """Produce a PaperSummary."""


class HeuristicSummaryBackend:
    """Deterministic offline summary backend."""

    name = "heuristic"
    model = None
    fallback_reason = None

    def summarize(
        self,
        paper: Paper,
        score: ReviewScore,
        *,
        evidence: PaperEvidence | None = None,
    ) -> PaperSummary:
        return _heuristic_summarize(paper, score, evidence=evidence)


class AutoSummaryBackend:
    """Use a configured LLM provider, otherwise fall back to deterministic summaries."""

    name = "auto"

    def __init__(
        self,
        *,
        openai_model: str,
        factchat_model: str,
        detail: str,
        openai_backend: SummaryBackend | None = None,
        factchat_backend: SummaryBackend | None = None,
        heuristic_backend: SummaryBackend | None = None,
    ) -> None:
        self.openai_model = openai_model
        self.factchat_model = factchat_model
        self.detail = detail
        self.fallback_reason: str | None = None
        self.openai_backend = openai_backend or OpenAISummaryBackend(model=openai_model, detail=detail)
        self.factchat_backend = factchat_backend or FactChatSummaryBackend(model=factchat_model, detail=detail)
        self.heuristic_backend = heuristic_backend or HeuristicSummaryBackend()

    @property
    def model(self) -> str | None:
        if _factchat_api_key() or getattr(self.factchat_backend, "client", None) is not None:
            return getattr(self.factchat_backend, "model", self.factchat_model)
        if os.environ.get("OPENAI_API_KEY") or getattr(self.openai_backend, "client", None) is not None:
            return getattr(self.openai_backend, "model", self.openai_model)
        return getattr(self.factchat_backend, "model", self.factchat_model)

    def summarize(
        self,
        paper: Paper,
        score: ReviewScore,
        *,
        evidence: PaperEvidence | None = None,
    ) -> PaperSummary:
        self.fallback_reason = None

        if _factchat_api_key() or getattr(self.factchat_backend, "client", None) is not None:
            try:
                return self.factchat_backend.summarize(paper, score, evidence=evidence)
            except Exception as exc:
                self.fallback_reason = f"FactChat summary failed: {exc}"
                return self.heuristic_backend.summarize(paper, score, evidence=evidence)

        if os.environ.get("OPENAI_API_KEY") or getattr(self.openai_backend, "client", None) is not None:
            try:
                return self.openai_backend.summarize(paper, score, evidence=evidence)
            except Exception as exc:
                self.fallback_reason = f"OpenAI summary failed: {exc}"
                return self.heuristic_backend.summarize(paper, score, evidence=evidence)

        self.fallback_reason = "FACTCHAT_API_KEY and OPENAI_API_KEY are not set"
        return self.heuristic_backend.summarize(paper, score, evidence=evidence)


class FactChatSummaryBackend:
    """FactChat Gateway summary backend using the OpenAI-compatible Chat API."""

    name = "factchat"

    def __init__(
        self,
        *,
        model: str,
        detail: str = "standard",
        client: Any | None = None,
        base_url: str | None = None,
    ) -> None:
        self.model = model
        self.detail = detail
        self.client = client
        self.base_url = base_url or os.environ.get("PAPERPILOT_FACTCHAT_BASE_URL") or FACTCHAT_BASE_URL
        self.fallback_reason: str | None = None

    def summarize(
        self,
        paper: Paper,
        score: ReviewScore,
        *,
        evidence: PaperEvidence | None = None,
    ) -> PaperSummary:
        pack = build_evidence_pack(paper, score, evidence=evidence, detail=self.detail)
        data = self._request_summary(pack)
        data = _sanitize_llm_summary_data(data, evidence_text=json.dumps(pack, ensure_ascii=False))
        summary = _summary_from_llm_data(paper, evidence, data, backend_label="FactChat")
        reflection = validate_summary(summary)
        if not reflection.passed:
            raise SummaryBackendError(f"FactChat summary failed reflection: {', '.join(reflection.issues)}")
        return PaperSummary(
            problem=summary.problem,
            contribution=summary.contribution,
            method=summary.method,
            experiments=summary.experiments,
            limitations=summary.limitations,
            reflection=reflection,
        )

    def _request_summary(self, evidence_pack: dict[str, Any]) -> dict[str, Any]:
        client = self.client or _factchat_client(base_url=self.base_url)
        candidates = self._model_candidates(client)
        selection_errors: list[str] = []
        for model in candidates:
            try:
                response = client.chat.completions.create(
                    model=model,
                    messages=[
                        {"role": "system", "content": _openai_instructions(self.detail)},
                        {"role": "user", "content": json.dumps(evidence_pack, ensure_ascii=False)},
                    ],
                    response_format={
                        "type": "json_schema",
                        "json_schema": {
                            "name": "paperpilot_summary",
                            "strict": True,
                            "schema": _openai_summary_schema(),
                        },
                    },
                )
            except Exception as exc:
                if self.model == "auto" and _is_factchat_model_selection_error(exc):
                    selection_errors.append(f"{model}: {exc}")
                    continue
                raise SummaryBackendError(_factchat_request_error(model, exc)) from exc

            self.model = model
            output_text = _chat_completion_text(response)
            if not output_text:
                raise SummaryBackendError("FactChat response did not include message content")
            try:
                data = json.loads(output_text)
            except json.JSONDecodeError as exc:
                raise SummaryBackendError(f"FactChat response was not valid JSON: {exc}") from exc
            _validate_llm_summary_data(data)
            return data

        tried = ", ".join(candidates) if candidates else "none"
        detail = f" Last errors: {' | '.join(selection_errors[-3:])}" if selection_errors else ""
        raise SummaryBackendError(
            f"No accessible FactChat chat model found. Tried: {tried}. "
            "Run `paperpilot models --provider factchat` and pass one with `--summary-model`."
            f"{detail}"
        )

    def _model_candidates(self, client: Any) -> tuple[str, ...]:
        if self.model != "auto":
            return (self.model,)

        model_ids = _factchat_model_ids(client=client, base_url=self.base_url)
        ordered: list[str] = []
        for model in FACTCHAT_MODEL_PREFERENCES:
            if model in model_ids:
                ordered.append(model)
        for model in model_ids:
            if model not in ordered:
                ordered.append(model)
        if not ordered:
            raise SummaryBackendError(
                "FactChat returned no available models. Check your Gateway API key or tenant configuration."
            )
        return tuple(ordered)


class OpenAISummaryBackend:
    """OpenAI Responses API summary backend using structured JSON output."""

    name = "openai"

    def __init__(self, *, model: str, detail: str = "standard", client: Any | None = None) -> None:
        self.model = model
        self.detail = detail
        self.client = client
        self.fallback_reason: str | None = None

    def summarize(
        self,
        paper: Paper,
        score: ReviewScore,
        *,
        evidence: PaperEvidence | None = None,
    ) -> PaperSummary:
        pack = build_evidence_pack(paper, score, evidence=evidence, detail=self.detail)
        data = self._request_summary(pack)
        data = _sanitize_llm_summary_data(data, evidence_text=json.dumps(pack, ensure_ascii=False))
        summary = _summary_from_llm_data(paper, evidence, data, backend_label="OpenAI")
        reflection = validate_summary(summary)
        if not reflection.passed:
            raise SummaryBackendError(f"OpenAI summary failed reflection: {', '.join(reflection.issues)}")
        return PaperSummary(
            problem=summary.problem,
            contribution=summary.contribution,
            method=summary.method,
            experiments=summary.experiments,
            limitations=summary.limitations,
            reflection=reflection,
        )

    def _request_summary(self, evidence_pack: dict[str, Any]) -> dict[str, Any]:
        client = self.client or _openai_client()
        response = client.responses.create(
            model=self.model,
            instructions=_openai_instructions(self.detail),
            input=json.dumps(evidence_pack, ensure_ascii=False),
            text={
                "format": {
                    "type": "json_schema",
                    "name": "paperpilot_summary",
                    "strict": True,
                    "schema": _openai_summary_schema(),
                }
            },
        )
        output_text = getattr(response, "output_text", None)
        if not output_text:
            raise SummaryBackendError("OpenAI response did not include output_text")
        try:
            data = json.loads(output_text)
        except json.JSONDecodeError as exc:
            raise SummaryBackendError(f"OpenAI response was not valid JSON: {exc}") from exc
        _validate_llm_summary_data(data)
        return data


class SummarizerAgent:
    """Write Korean summaries from paper metadata using a configurable backend."""

    def __init__(self, backend: SummaryBackend | None = None) -> None:
        self.backend = backend or HeuristicSummaryBackend()
        self.fallback_reasons: list[str] = []

    @property
    def backend_name(self) -> str:
        return self.backend.name

    @property
    def model(self) -> str | None:
        return self.backend.model

    def set_backend(self, backend: SummaryBackend) -> None:
        self.backend = backend
        self.fallback_reasons = []

    def summarize(
        self,
        paper: Paper,
        score: ReviewScore,
        *,
        evidence: PaperEvidence | None = None,
    ) -> PaperSummary:
        summary = self.backend.summarize(paper, score, evidence=evidence)
        fallback_reason = getattr(self.backend, "fallback_reason", None)
        if fallback_reason:
            self.fallback_reasons.append(fallback_reason)
        return summary


def build_summary_backend(
    mode: str,
    *,
    model: str | None = None,
    detail: str = "standard",
) -> SummaryBackend:
    """Build a summary backend from CLI/workflow options."""

    if mode not in {"auto", "openai", "factchat", "heuristic"}:
        raise ValueError("summary_backend must be one of: auto, openai, factchat, heuristic")
    if detail not in SUMMARY_DETAIL_LEVELS:
        raise ValueError("summary_detail must be one of: standard, deep, ultra")

    if mode == "heuristic":
        return HeuristicSummaryBackend()
    if mode == "openai":
        resolved_model = model or os.environ.get("PAPERPILOT_OPENAI_MODEL") or DEFAULT_OPENAI_MODEL
        return OpenAISummaryBackend(model=resolved_model, detail=detail)
    if mode == "factchat":
        resolved_model = model or os.environ.get("PAPERPILOT_FACTCHAT_MODEL") or DEFAULT_FACTCHAT_MODEL
        return FactChatSummaryBackend(model=resolved_model, detail=detail)
    return AutoSummaryBackend(
        openai_model=model or os.environ.get("PAPERPILOT_OPENAI_MODEL") or DEFAULT_OPENAI_MODEL,
        factchat_model=model or os.environ.get("PAPERPILOT_FACTCHAT_MODEL") or DEFAULT_FACTCHAT_MODEL,
        detail=detail,
    )


def list_summary_models(provider: str = "factchat") -> tuple[str, ...]:
    """List available models for a summary provider."""

    if provider != "factchat":
        raise SummaryBackendError("Only FactChat model listing is supported.")
    client = _factchat_client(base_url=os.environ.get("PAPERPILOT_FACTCHAT_BASE_URL") or FACTCHAT_BASE_URL)
    return _factchat_model_ids(client=client, base_url=os.environ.get("PAPERPILOT_FACTCHAT_BASE_URL") or FACTCHAT_BASE_URL)


def _heuristic_summarize(
    paper: Paper,
    score: ReviewScore,
    *,
    evidence: PaperEvidence | None = None,
) -> PaperSummary:
    problem = _problem_sentence(paper, evidence)
    contribution = _contribution_sentence(paper, evidence)
    method = _method_sentence(paper, evidence)
    experiments = _experiment_sentence(paper, evidence)
    limitations = _limitations_sentence(evidence)

    summary = PaperSummary(
        problem=problem,
        contribution=contribution,
        method=method,
        experiments=experiments,
        limitations=limitations,
    )
    reflection = validate_summary(summary)
    if reflection.passed:
        return PaperSummary(
            problem=summary.problem,
            contribution=summary.contribution,
            method=summary.method,
            experiments=summary.experiments,
            limitations=summary.limitations,
            reflection=reflection,
        )
    return rewrite_for_reflection(summary, reflection)


def build_evidence_pack(
    paper: Paper,
    score: ReviewScore,
    *,
    evidence: PaperEvidence | None = None,
    detail: str = "standard",
) -> dict[str, Any]:
    """Build the bounded evidence object sent to an LLM backend."""

    limit = _detail_snippet_limit(detail)
    evidence_text = evidence.text if evidence and evidence.available else paper.summary
    return {
        "paper": {
            "title": paper.title,
            "authors": list(paper.authors),
            "abstract": paper.summary,
            "categories": list(paper.categories),
            "published": paper.published.date().isoformat(),
            "url": paper.url,
        },
        "review_score": {
            "relevance": score.relevance,
            "novelty": score.novelty,
            "experimental_strength": score.experimental_strength,
            "total": score.total,
            "reason": score.reason,
        },
        "paper_kind": _paper_kind(paper, evidence),
        "detail": detail,
        "reading_focus": (
            "우선순위: 기존 접근과 비교해 무엇이 새롭고 왜 중요한지 먼저 판단한다. "
            "새로운 시스템 구성, 데이터/벤치마크, 평가 지표, 실험 설계, 실패 분석, 적용 범위 중 "
            "근거에서 확인되는 차별점을 구분해 설명한다."
        ),
        "quantitative_clues": _quantitative_snippets(evidence_text),
        "novelty_clues": _novelty_snippets(evidence_text, limit=limit + (2 if detail == "ultra" else 0)),
        "evidence_scope": _evidence_scope(evidence) if evidence and evidence.available else "abstract only",
        "sections": {
            "problem": _section_snippets(
                evidence,
                ("abstract", "introduction", "benchmark"),
                ("challenge", "problem", "motivation", "however", "need", "requires"),
                fallback=paper.summary,
                limit=limit,
            ),
            "contribution": _section_snippets(
                evidence,
                ("introduction", "method", "benchmark"),
                ("contribution", "contributions", "we propose", "we introduce", "we present", "our approach"),
                fallback=paper.summary,
                limit=limit,
            ),
            "novelty": _section_snippets(
                evidence,
                ("introduction", "method", "experiments", "benchmark", "limitations"),
                (
                    "novel",
                    "new",
                    "first",
                    "unlike",
                    "whereas",
                    "instead",
                    "different",
                    "variant",
                    "ablation",
                    "contribution",
                    "we propose",
                    "we introduce",
                    "we present",
                    "outperform",
                    "state-of-the-art",
                    "sota",
                ),
                fallback=evidence_text,
                limit=limit,
            ),
            "method_or_design": _section_snippets(
                evidence,
                ("method", "benchmark", "introduction"),
                ("approach", "pipeline", "architecture", "algorithm", "training", "method", "task", "dataset"),
                fallback=paper.summary,
                limit=limit,
            ),
            "experiments": _section_snippets(
                evidence,
                ("experiments", "benchmark"),
                ("experiment", "experiments", "evaluation", "benchmark", "dataset", "results", "outperform", "improve"),
                fallback=evidence_text,
                limit=limit,
            ),
            "limitations": _section_snippets(
                evidence,
                ("limitations", "experiments", "benchmark"),
                ("limitation", "limitations", "future work", "threats to validity", "failure", "fail", "discussion"),
                fallback=evidence_text,
                limit=limit,
            ),
        },
    }


def _openai_client() -> Any:
    try:
        from openai import OpenAI
    except ImportError as exc:
        raise SummaryBackendError("openai package is not installed") from exc
    return OpenAI()


def _factchat_client(*, base_url: str) -> Any:
    api_key = _factchat_api_key()
    if not api_key:
        raise SummaryBackendError("FACTCHAT_API_KEY is not set")
    try:
        from openai import OpenAI
    except ImportError as exc:
        raise SummaryBackendError("openai package is not installed") from exc
    return OpenAI(api_key=api_key, base_url=base_url)


def _factchat_api_key() -> str | None:
    return os.environ.get("FACTCHAT_API_KEY") or os.environ.get("PAPERPILOT_FACTCHAT_API_KEY")


def _factchat_model_ids(*, client: Any, base_url: str) -> tuple[str, ...]:
    sdk_error: Exception | None = None
    try:
        response = client.models.list()
        model_ids = _model_ids_from_response(response)
        if model_ids:
            return model_ids
    except AttributeError:
        pass
    except Exception as exc:
        sdk_error = exc

    try:
        return _factchat_model_ids_http(base_url=base_url)
    except SummaryBackendError as exc:
        if sdk_error:
            raise SummaryBackendError(
                f"Could not list FactChat models via SDK or HTTP. SDK error: {sdk_error}; HTTP error: {exc}"
            ) from exc
        raise


def _factchat_model_ids_http(*, base_url: str) -> tuple[str, ...]:
    api_key = _factchat_api_key()
    if not api_key:
        raise SummaryBackendError("FACTCHAT_API_KEY is not set")
    url = f"{base_url.rstrip('/')}/models/"
    request = Request(url, headers={"Authorization": f"Bearer {api_key}"})
    try:
        with urlopen(request, timeout=30) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        raise SummaryBackendError(f"FactChat model list failed with HTTP {exc.code}: {body}") from exc
    except (OSError, URLError, json.JSONDecodeError) as exc:
        raise SummaryBackendError(f"FactChat model list failed: {exc}") from exc

    return _model_ids_from_response(payload)


def _model_ids_from_response(response: Any) -> tuple[str, ...]:
    data = response.get("data") if isinstance(response, dict) else getattr(response, "data", None)
    if data is None:
        return ()
    model_ids: list[str] = []
    for item in data:
        model_id = item.get("id") if isinstance(item, dict) else getattr(item, "id", None)
        if isinstance(model_id, str) and model_id.strip():
            model_ids.append(model_id)
    return tuple(dict.fromkeys(model_ids))


def _is_factchat_model_selection_error(exc: Exception) -> bool:
    text = str(exc).lower()
    return any(
        marker in text
        for marker in (
            "no access to model",
            "permission_denied",
            "model_not_found",
            "does not exist",
            "not supported",
            "unsupported",
            "response_format",
            "json_schema",
        )
    )


def _factchat_request_error(model: str, exc: Exception) -> str:
    if _is_factchat_model_selection_error(exc):
        return (
            f"FactChat model '{model}' is not accessible or does not support this request. "
            "Run `paperpilot models --provider factchat` to see available model IDs, then retry with "
            "`--summary-model MODEL` or leave the model unset to auto-select. "
            f"Original error: {exc}"
        )
    return f"FactChat request failed for model '{model}': {exc}"


def _chat_completion_text(response: Any) -> str | None:
    choices = getattr(response, "choices", None)
    if not choices:
        return None
    message = getattr(choices[0], "message", None)
    content = getattr(message, "content", None)
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts: list[str] = []
        for item in content:
            if isinstance(item, str):
                parts.append(item)
            elif isinstance(item, dict) and isinstance(item.get("text"), str):
                parts.append(item["text"])
            elif hasattr(item, "text") and isinstance(item.text, str):
                parts.append(item.text)
        return "".join(parts) or None
    return None


def _openai_instructions(detail: str) -> str:
    if detail == "ultra":
        depth = (
            "각 배열은 가능하면 5~7개 bullet로 자세히 작성한다. "
            "특히 novelty 배열은 기존 방식 대비 무엇이 새롭고, 왜 중요한지, 어떤 근거 문장에 기대는지를 우선 설명한다. "
            "새로운 시스템 구성, 데이터/벤치마크, 평가 지표, 실험 설계, 실패 분석, 적용 범위를 서로 구분한다."
        )
    elif detail == "deep":
        depth = "각 배열은 가능하면 3~5개 bullet로 자세히 작성한다."
    else:
        depth = "각 배열은 2~3개 bullet로 간결하게 작성한다."
    return (
        "너는 한국어 연구 논문 큐레이터다. 제공된 evidence JSON 안에 있는 정보만 사용해 요약한다. "
        "가장 중요한 읽기 목표는 논문의 새로움과 기존 접근 대비 차별점을 먼저 파악하는 것이다. "
        "근거에 없는 수치, 데이터셋, 비교 결과, 한계를 만들지 않는다. "
        "확인할 수 없는 항목은 확인 불가 또는 추가 확인 필요라고 명시한다. "
        "문장은 자연스러운 한국어로 쓰고, 영어 원문을 길게 복사하지 않는다. "
        f"{depth}"
    )


def _openai_summary_schema() -> dict[str, Any]:
    array_schema = {
        "type": "array",
        "items": {"type": "string"},
        "minItems": 1,
        "maxItems": 8,
    }
    return {
        "type": "object",
        "additionalProperties": False,
        "required": [
            "one_line_summary",
            "problem",
            "novelty",
            "contributions",
            "method_or_design",
            "experiments",
            "limitations",
            "evidence_notes",
            "confidence",
        ],
        "properties": {
            "one_line_summary": {"type": "string"},
            "problem": {"type": "string"},
            "novelty": array_schema,
            "contributions": array_schema,
            "method_or_design": array_schema,
            "experiments": array_schema,
            "limitations": array_schema,
            "evidence_notes": array_schema,
            "confidence": {"type": "string", "enum": ["low", "medium", "high"]},
        },
    }


def _validate_llm_summary_data(data: dict[str, Any]) -> None:
    required = {
        "one_line_summary",
        "problem",
        "novelty",
        "contributions",
        "method_or_design",
        "experiments",
        "limitations",
        "evidence_notes",
        "confidence",
    }
    missing = required - set(data)
    if missing:
        raise SummaryBackendError(f"LLM summary missing fields: {', '.join(sorted(missing))}")
    for field in ("one_line_summary", "problem", "confidence"):
        if not isinstance(data[field], str) or not data[field].strip():
            raise SummaryBackendError(f"LLM summary field {field} must be a non-empty string")
    for field in ("novelty", "contributions", "method_or_design", "experiments", "limitations", "evidence_notes"):
        if not isinstance(data[field], list) or not data[field]:
            raise SummaryBackendError(f"LLM summary field {field} must be a non-empty list")
        if not all(isinstance(item, str) and item.strip() for item in data[field]):
            raise SummaryBackendError(f"LLM summary field {field} must contain non-empty strings")


def _sanitize_llm_summary_data(data: dict[str, Any], *, evidence_text: str) -> dict[str, Any]:
    allowed_numbers = set(_quantitative_snippets(evidence_text))
    unsupported: list[str] = []
    for field in ("one_line_summary", "problem"):
        unsupported.extend(number for number in _quantitative_snippets(data[field]) if number not in allowed_numbers)
    for field in ("novelty", "contributions", "method_or_design", "experiments", "limitations"):
        for item in data[field]:
            unsupported.extend(number for number in _quantitative_snippets(item) if number not in allowed_numbers)

    if unsupported:
        unique = sorted(set(unsupported))
        data = dict(data)
        data["evidence_notes"] = list(data["evidence_notes"]) + [
            f"근거에서 직접 확인되지 않은 정량 표현은 확인 필요로 표시했습니다: {', '.join(unique)}"
        ]
    return data


def _summary_from_llm_data(
    paper: Paper,
    evidence: PaperEvidence | None,
    data: dict[str, Any],
    *,
    backend_label: str,
) -> PaperSummary:
    kind = _paper_kind(paper, evidence)
    method_heading = "방법" if kind == "research" else "구성/평가 설계"
    experiment_heading = "실험/결과" if kind == "research" else "벤치마크/결과"
    confidence = f"신뢰도: {data['confidence']}"

    problem = (
        f"한 줄 요약: {data['one_line_summary']}\n\n"
        f"문제: {data['problem']}\n\n"
        f"근거:\n{_evidence_preview(evidence, 'abstract', 'introduction', 'benchmark')}\n"
        f"{confidence}"
    )
    contribution = (
        f"핵심 기여와 새로움: {backend_label} 요약 backend가 PDF 근거를 바탕으로 정리한 내용입니다.\n"
        f"새로움/차별점:\n{_plain_bullets(data['novelty'])}\n\n"
        "주요 기여:\n"
        f"{_plain_bullets(data['contributions'])}\n\n"
        f"근거:\n{_evidence_preview(evidence, 'introduction', 'method', 'benchmark')}"
    )
    method = (
        f"{method_heading}: {backend_label} 요약 backend가 PDF 근거를 바탕으로 정리한 내용입니다.\n"
        f"{_plain_bullets(data['method_or_design'])}\n\n"
        f"근거:\n{_evidence_preview(evidence, 'method', 'benchmark', 'introduction')}"
    )
    experiments = (
        f"{experiment_heading}: {backend_label} 요약 backend가 PDF 근거를 바탕으로 정리한 내용입니다.\n"
        f"{_plain_bullets(data['experiments'])}\n\n"
        f"근거:\n{_evidence_preview(evidence, 'experiments', 'benchmark')}"
    )
    limitations = (
        f"한계와 확인 필요: {backend_label} 요약 backend가 PDF 근거를 바탕으로 정리한 내용입니다.\n"
        f"{_plain_bullets(data['limitations'])}\n\n"
        f"근거/검증 메모:\n{_plain_bullets(data['evidence_notes'])}\n"
        f"근거:\n{_evidence_preview(evidence, 'limitations', 'experiments', 'benchmark')}"
    )
    return PaperSummary(
        problem=problem,
        contribution=contribution,
        method=method,
        experiments=experiments,
        limitations=limitations,
    )


def validate_summary(summary: PaperSummary) -> ReflectionResult:
    """Check whether the summary contains the expected five-part evidence."""

    text = " ".join(
        [
            summary.problem,
            summary.contribution,
            summary.method,
            summary.experiments,
            summary.limitations,
        ]
    )
    issues: list[str] = []
    experiment_discussed = any(token in text for token in ("실험", "벤치마크", "평가", "결과"))
    if "기여" not in text:
        issues.append("missing contribution")
    if not any(token in text for token in ("방법", "접근", "모델", "프레임워크")):
        issues.append("missing method")
    if not experiment_discussed:
        issues.append("missing experiment discussion")
    if experiment_discussed and not (
        _has_quantitative_evidence(text)
        or "확인할 수 없습니다" in text
        or "확인 필요" in text
    ):
        issues.append("missing quantitative evidence caveat")
    if not any(token in text for token in ("한계", "확인 필요", "추가 확인")):
        issues.append("missing limitations")
    return ReflectionResult(passed=not issues, issues=tuple(issues))


def rewrite_for_reflection(summary: PaperSummary, reflection: ReflectionResult) -> PaperSummary:
    """Patch missing reflection criteria with explicit caveats."""

    contribution = summary.contribution
    method = summary.method
    experiments = summary.experiments
    limitations = summary.limitations

    if "missing contribution" in reflection.issues:
        contribution = f"핵심 기여: 초록 기준으로 확인되는 기여는 {summary.problem}"
    if "missing method" in reflection.issues:
        method = f"{method} 방법 세부사항은 본문 확인이 필요합니다."
    if "missing experiment discussion" in reflection.issues:
        experiments = f"{experiments} 실험 구성은 초록만으로는 충분히 확인할 수 없습니다."
    if "missing quantitative evidence caveat" in reflection.issues:
        experiments = f"{experiments} 초록만으로는 정량 실험 수치를 확인할 수 없습니다."
    if "missing limitations" in reflection.issues:
        limitations = f"{limitations} 한계와 추가 확인 지점을 본문에서 검토해야 합니다."

    patched = PaperSummary(
        problem=summary.problem,
        contribution=contribution,
        method=method,
        experiments=experiments,
        limitations=limitations,
    )
    return PaperSummary(
        problem=patched.problem,
        contribution=patched.contribution,
        method=patched.method,
        experiments=patched.experiments,
        limitations=patched.limitations,
        reflection=validate_summary(patched),
    )


def _trim_sentence(text: str, max_chars: int = 320) -> str:
    compact = " ".join(text.split())
    if len(compact) <= max_chars:
        return compact
    return compact[: max_chars - 1].rstrip() + "..."


def _problem_sentence(paper: Paper, evidence: PaperEvidence | None = None) -> str:
    abstract = _trim_sentence(paper.summary)
    if evidence and evidence.available:
        text = _section_text(evidence, "abstract", "introduction", "benchmark") or evidence.text
        sentences = _evidence_sentences(
            text,
            (
                "challenge",
                "problem",
                "motivation",
                "however",
                "need",
                "requires",
            ),
            limit=2,
        )
        if sentences:
            return (
                f"한 줄 요약: {_one_line_summary(paper, evidence)}\n\n"
                f"문제: `{paper.title}`는 {abstract}\n\n"
                f"문제 해석:\n{_summary_bullets(sentences, kind='problem')}\n\n"
                f"PDF 문제 설정 근거({_evidence_scope(evidence)}):\n{_evidence_bullets(sentences)}"
            )
    return f"한 줄 요약: {_one_line_summary(paper, evidence)}\n\n문제: `{paper.title}`는 {abstract}"


def _contribution_sentence(paper: Paper, evidence: PaperEvidence | None = None) -> str:
    if evidence and evidence.available:
        text = _section_text(evidence, "introduction", "method", "benchmark") or evidence.text
        sentences = _evidence_sentences(
            text,
            (
                "contribution",
                "contributions",
                "we propose",
                "we introduce",
                "we present",
                "our approach",
            ),
            limit=3,
        )
        if sentences:
            prefix = "핵심 기여" if _paper_kind(paper, evidence) == "research" else "보고서/벤치마크 기여"
            return (
                f"{prefix}: PDF 본문 근거를 바탕으로 정리한 요약입니다.\n"
                f"{_summary_bullets(sentences, kind='contribution')}\n\n"
                f"근거:\n{_evidence_bullets(sentences)}\n"
                f"요약 판단: {_contribution_judgment(paper, evidence)}"
            )

    text = paper.summary.lower()
    if any(token in text for token in ("novel", "new", "introduce", "propose", "framework", "benchmark")):
        return "핵심 기여: 초록은 새로운 접근, 프레임워크, 또는 벤치마크 성격의 기여를 주장합니다."
    return "핵심 기여: 초록 기준으로는 문제 설정과 접근 방향이 확인되지만, 기여의 차별성은 본문 확인이 필요합니다."


def _method_sentence(paper: Paper, evidence: PaperEvidence | None = None) -> str:
    if evidence and evidence.available:
        kind = _paper_kind(paper, evidence)
        text = _section_text(evidence, "method", "benchmark", "introduction") or evidence.text
        keywords = (
            (
                "task",
                "dataset",
                "evaluation protocol",
                "leaderboard",
                "participants",
                "systems",
                "retrieval system",
            )
            if kind == "benchmark"
            else (
                "approach",
                "pipeline",
                "architecture",
                "algorithm",
                "training",
                "method",
            )
        )
        sentences = _evidence_sentences(
            text,
            keywords,
            limit=3,
        )
        if sentences:
            heading = "방법" if kind == "research" else "구성/평가 설계"
            focus = (
                "입력 처리, 검색/생성 파이프라인, 모델 구성 요소가 어떻게 분리되는지 본문 근거 중심으로 추적했습니다."
                if kind == "research"
                else "태스크 구성, 데이터셋, 평가 프로토콜, 참가 시스템 경향을 중심으로 추적했습니다."
            )
            return (
                f"{heading}: PDF 본문 근거를 바탕으로 정리한 요약입니다.\n"
                f"{_summary_bullets(sentences, kind='method' if kind == 'research' else 'benchmark_method')}\n\n"
                f"근거:\n{_evidence_bullets(sentences)}\n"
                f"확인 포인트: {focus}"
            )

    categories = ", ".join(paper.categories) if paper.categories else "분야 태그 없음"
    return (
        "방법: 저자들은 초록에서 설명한 모델/알고리즘 접근을 사용하며, "
        f"arXiv 카테고리는 {categories}입니다."
    )


def _experiment_sentence(paper: Paper, evidence: PaperEvidence | None = None) -> str:
    evidence_text = evidence.text if evidence and evidence.available else ""
    if evidence_text:
        kind = _paper_kind(paper, evidence)
        section_labels = ("experiments", "benchmark") if kind == "benchmark" else ("experiments",)
        text = _section_text(evidence, *section_labels)
        if len(_quantitative_snippets(text)) < 1:
            text = evidence_text
        numbers = _quantitative_snippets(text)
        contexts = _evidence_sentences(
            text,
            (
                "experiment",
                "experiments",
                "evaluation",
                "benchmark",
                "dataset",
                "results",
                "outperform",
                "improve",
            ),
            limit=3,
        )
        if numbers:
            label = "실험/결과" if kind == "research" else "벤치마크/결과"
            body = f"{label}: PDF 본문에서 확인되는 정량 단서는 {', '.join(numbers[:6])}입니다."
            if contexts:
                body = (
                    f"{body}\n"
                    f"실험 해석:\n{_summary_bullets(contexts, kind='experiments')}\n\n"
                    f"근거({_evidence_scope(evidence)}):\n{_evidence_bullets(contexts)}"
                )
            return (
                f"{body}\n"
                "해석 주의: 추출된 수치는 PDF 앞부분에서 잡힌 단서라서, 최종 표/부록의 전체 실험 결과와 대조가 필요합니다."
            )
        if contexts:
            return (
                "실험/결과: PDF 본문은 평가 설정을 설명하지만, 정량 실험 수치는 확인할 수 없습니다.\n"
                f"{_summary_bullets(contexts, kind='experiments')}\n\n"
                f"근거:\n{_evidence_bullets(contexts)}"
            )

    numbers = _quantitative_snippets(paper.summary)
    lower = paper.summary.lower()
    has_experiment_signal = any(
        token in lower
        for token in (
            "ablation",
            "benchmark",
            "dataset",
            "evaluation",
            "experiment",
            "results",
        )
    )
    if numbers:
        return f"실험/결과: 초록에서 확인되는 정량 단서는 {', '.join(numbers[:4])}입니다."
    if has_experiment_signal:
        return "실험/결과: 초록은 평가나 벤치마크를 언급하지만, 정량 실험 수치는 확인할 수 없습니다."
    return "실험/결과: 초록만으로는 실험 설정과 정량 실험 수치를 확인할 수 없습니다."


def _limitations_sentence(evidence: PaperEvidence | None = None) -> str:
    if evidence and evidence.available:
        text = _section_text(evidence, "limitations", "experiments", "benchmark") or evidence.text
        sentences = _evidence_sentences(
            text,
            (
                "limitation",
                "limitations",
                "future work",
                "threats to validity",
                "failure",
                "fail",
                "discussion",
            ),
            limit=3,
        )
        if sentences:
            return (
                "한계: PDF 본문 근거를 바탕으로 정리한 요약입니다.\n"
                f"{_summary_bullets(sentences, kind='limitations')}\n\n"
                f"근거:\n{_evidence_bullets(sentences)}\n"
                "추가 확인 필요: 이 항목은 명시적 limitation 섹션뿐 아니라 discussion/failure 표현도 함께 탐색한 결과입니다."
            )
        return (
            f"한계: {_evidence_scope(evidence)}를 확인했지만 명시적인 한계 문장은 찾지 못했습니다. "
            "실패 사례, 비교 기준, 데이터셋 편향은 본문 후반부와 부록에서 추가 확인이 필요합니다."
        )
    return (
        "한계: 전체 논문 본문을 확인하기 전에는 데이터셋 구성, 실패 사례, "
        "비교 기준의 공정성을 추가 확인해야 합니다."
    )


def _quantitative_snippets(text: str) -> list[str]:
    matches = re.findall(
        r"\b\d+(?:\.\d+)?\s?(?:%|x|k|m|b|datasets?|tasks?|benchmarks?|examples?|samples?|queries?|documents?|papers?|participants?|teams?)(?=[^A-Za-z0-9]|$)",
        text,
        flags=re.IGNORECASE,
    )
    snippets: list[str] = []
    seen: set[str] = set()
    for match in matches:
        snippet = " ".join(match.split())
        if _looks_like_section_number(snippet):
            continue
        key = snippet.lower()
        if key in seen:
            continue
        seen.add(key)
        snippets.append(snippet)
    return snippets


def _has_quantitative_evidence(text: str) -> bool:
    return bool(_quantitative_snippets(text))


def _best_sentence(text: str, keywords: tuple[str, ...], max_chars: int = 260) -> str | None:
    sentences = _evidence_sentences(text, keywords, limit=1, max_chars=max_chars)
    return sentences[0] if sentences else None


def _evidence_sentences(
    text: str,
    keywords: tuple[str, ...],
    *,
    limit: int,
    max_chars: int = 260,
) -> tuple[str, ...]:
    normalized = " ".join(text.split())
    candidates = re.split(r"(?<=[.!?])\s+", normalized)
    sentences: list[str] = []
    seen: set[str] = set()
    for candidate in candidates:
        compact = _clean_sentence(candidate)
        if len(compact) <= 25:
            continue
        if not any(_contains_keyword(compact, keyword) for keyword in keywords):
            continue
        sentence = _trim_sentence(compact, max_chars=max_chars)
        key = sentence.lower()
        if key in seen:
            continue
        seen.add(key)
        sentences.append(sentence)
        if len(sentences) >= limit:
            break
    return tuple(sentences)


def _looks_like_section_number(snippet: str) -> bool:
    if re.match(r"^\d+(?:\.\d+)?\s+[A-Z][A-Za-z]+$", snippet):
        return True
    return bool(re.match(r"^1\s+[A-Za-z]+s$", snippet))


def _clean_sentence(sentence: str) -> str:
    compact = sentence.strip()
    compact = re.sub(r"^[•\-\d.\s]+", "", compact)
    compact = re.sub(r"\s+([,.;:])", r"\1", compact)
    return compact


def _contains_keyword(sentence: str, keyword: str) -> bool:
    if " " in keyword:
        return keyword.lower() in sentence.lower()
    return bool(re.search(rf"\b{re.escape(keyword.lower())}s?\b", sentence.lower()))


def _evidence_bullets(sentences: tuple[str, ...] | list[str]) -> str:
    return "\n".join(f"- `{sentence}`" for sentence in sentences)


def _summary_bullets(sentences: tuple[str, ...] | list[str], *, kind: str) -> str:
    bullets = [_interpret_sentence(sentence, kind=kind) for sentence in sentences]
    deduped: list[str] = []
    seen: set[str] = set()
    for bullet in bullets:
        if bullet in seen:
            continue
        seen.add(bullet)
        deduped.append(bullet)
    return "\n".join(f"- {bullet}" for bullet in deduped)


def _plain_bullets(items: list[str] | tuple[str, ...]) -> str:
    return "\n".join(f"- {item}" for item in items)


def _section_snippets(
    evidence: PaperEvidence | None,
    labels: tuple[str, ...],
    keywords: tuple[str, ...],
    *,
    fallback: str,
    limit: int,
) -> list[str]:
    text = _section_text(evidence, *labels) if evidence and evidence.available else ""
    text = text or fallback
    snippets = _evidence_sentences(text, keywords, limit=limit)
    if snippets:
        return list(snippets)
    return list(_first_sentences(text, limit=limit))


def _detail_snippet_limit(detail: str) -> int:
    if detail == "ultra":
        return 8
    if detail == "deep":
        return 5
    return 3


def _novelty_snippets(text: str, *, limit: int) -> list[str]:
    keywords = (
        "novel",
        "new",
        "first",
        "unlike",
        "whereas",
        "instead",
        "different",
        "contribution",
        "contributions",
        "we propose",
        "we introduce",
        "we present",
        "variant",
        "ablation",
        "outperform",
        "state-of-the-art",
        "sota",
    )
    snippets = _evidence_sentences(text, keywords, limit=limit)
    if snippets:
        return list(snippets)
    return list(_first_sentences(text, limit=min(limit, 3)))


def _evidence_preview(evidence: PaperEvidence | None, *labels: str) -> str:
    if not evidence or not evidence.available:
        return "- `PDF 본문 근거를 사용할 수 없습니다.`"
    text = _section_text(evidence, *labels) or evidence.text
    snippets = _evidence_sentences(
        text,
        _preview_keywords(labels),
        limit=3,
        max_chars=220,
    )
    if not snippets:
        snippets = _first_sentences(text, limit=3, max_chars=220)
    return _evidence_bullets(snippets)


def _preview_keywords(labels: tuple[str, ...]) -> tuple[str, ...]:
    label_set = set(labels)
    if "experiments" in label_set:
        return (
            "experiment",
            "evaluation",
            "benchmark",
            "dataset",
            "result",
            "outperform",
            "improve",
            "accuracy",
            "score",
            "baseline",
        )
    if "limitations" in label_set:
        return (
            "limitation",
            "limitations",
            "future work",
            "discussion",
            "failure",
            "fail",
            "sensitive",
            "noisy",
            "threat",
        )
    if "method" in label_set:
        return (
            "approach",
            "method",
            "pipeline",
            "architecture",
            "algorithm",
            "chunk",
            "split",
            "rerank",
            "generator",
            "training",
        )
    if "benchmark" in label_set:
        return ("task", "dataset", "benchmark", "evaluation", "protocol", "leaderboard", "challenge")
    return (
        "novel",
        "new",
        "first",
        "unlike",
        "whereas",
        "instead",
        "contribution",
        "we propose",
        "we introduce",
        "we present",
        "problem",
        "challenge",
    )


def _first_sentences(text: str, *, limit: int, max_chars: int = 260) -> tuple[str, ...]:
    normalized = " ".join(text.split())
    sentences: list[str] = []
    for candidate in re.split(r"(?<=[.!?])\s+", normalized):
        compact = _clean_sentence(candidate)
        if len(compact) <= 25:
            continue
        sentences.append(_trim_sentence(compact, max_chars=max_chars))
        if len(sentences) >= limit:
            break
    return tuple(sentences)


def _interpret_sentence(sentence: str, *, kind: str) -> str:
    text = sentence.lower()
    numbers = _quantitative_snippets(sentence)
    entities = _named_entities(sentence)

    if kind == "problem":
        if any(token in text for token in ("we propose", "we introduce", "framework", "system")):
            return "본문은 이 문제를 해결하기 위한 시스템/프레임워크 제안으로 논의를 이어갑니다."
        if any(token in text for token in ("layout", "structure", "table", "chart", "visually-rich")):
            return "기존 RAG/검색 방식은 문서의 레이아웃, 표, 그림 같은 구조 정보를 충분히 다루지 못하는 문제가 있습니다."
        if any(token in text for token in ("challenge", "participant", "task")):
            return "논문은 여러 태스크나 참가 시스템을 통해 멀티모달 검색 문제를 평가해야 한다고 봅니다."
        return "기존 접근의 한계나 문제 설정을 본문에서 명시적으로 제기합니다."

    if kind == "contribution":
        if "fastrageval" in text:
            return "FastRAGEval이라는 평가 지표를 제안해 생성 답변의 recall 평가 비용과 인간 평가 정렬 문제를 다룹니다."
        if any(token in text for token in ("we propose", "we introduce", "framework", "system")):
            name = _preferred_entity(entities)
            target = f"{name}를 중심으로 " if name else ""
            return f"{target}새로운 시스템/프레임워크를 제안하는 것이 핵심 기여입니다."
        if "variant" in text:
            return "여러 설계 변형을 통제 비교해 어떤 구성 요소가 성능에 기여하는지 분리해 보려 합니다."
        return "본문에서 제안점이나 기여 항목으로 표시된 내용을 핵심 기여로 봅니다."

    if kind == "method":
        if any(token in text for token in ("pipeline", "ingestion", "chunk", "split")):
            return "문서 구조에 따라 parsing, chunking, ingestion 경로를 달리하는 파이프라인을 사용합니다."
        if any(token in text for token in ("rerank", "generator", "query re-writer", "assembly")):
            return "query rewriting, reranking, answer generation 같은 RAG 구성 요소를 분리해 조합합니다."
        if any(token in text for token in ("layout", "artifact", "placeholder")):
            return "레이아웃과 시각적 artifact를 보존해 retrieval 표현과 generation context를 다르게 구성합니다."
        return "본문에서 설명한 접근 방식과 시스템 구성 요소를 방법 단서로 사용합니다."

    if kind == "benchmark_method":
        if any(token in text for token in ("task", "track")):
            return "벤치마크는 복수의 검색 태스크를 하나의 시스템으로 풀도록 설계되어 있습니다."
        if any(token in text for token in ("dataset", "page", "screenshot", "ocr")):
            return "평가 데이터는 페이지 이미지, OCR 텍스트, 설명 등 멀티모달 입력을 포함합니다."
        if any(token in text for token in ("leaderboard", "score", "recall")):
            return "평가는 leaderboard 점수와 recall 계열 지표를 중심으로 집계됩니다."
        return "태스크, 데이터셋, 평가 프로토콜을 중심으로 벤치마크 구성을 설명합니다."

    if kind == "experiments":
        if any(token in text for token in ("outperform", "improve", "better")):
            metric = f" ({', '.join(numbers[:3])})" if numbers else ""
            return f"비교 기준 대비 성능 향상을 보고합니다{metric}."
        if any(token in text for token in ("dataset", "benchmark", "domain")):
            metric = f" ({', '.join(numbers[:3])})" if numbers else ""
            return f"여러 데이터셋/벤치마크/도메인에서 평가한 것으로 보입니다{metric}."
        if any(token in text for token in ("leaderboard", "participants", "teams", "submissions")):
            metric = f" ({', '.join(numbers[:4])})" if numbers else ""
            return f"참가 팀, 제출 수, leaderboard 결과를 통해 벤치마크 규모를 제시합니다{metric}."
        return "평가 설정이나 결과 해석에 필요한 실험 문맥을 제공합니다."

    if kind == "limitations":
        if any(token in text for token in ("failure", "fail", "sensitive", "noisy")):
            return "실패 사례나 noisy input에 대한 민감도를 추가로 확인해야 합니다."
        if "future" in text:
            return "저자들이 후속 연구로 남긴 범위가 있어 현재 결과의 적용 범위를 제한합니다."
        if "discussion" in text:
            return "Discussion 섹션의 관찰을 한계와 해석상 주의점으로 함께 봐야 합니다."
        return "본문의 논의 문장을 근거로 한계와 추가 확인 지점을 정리합니다."

    return _trim_sentence(sentence, max_chars=160)


def _named_entities(sentence: str) -> list[str]:
    candidates = re.findall(r"\b[A-Z][A-Za-z0-9-]*(?:RAG|LLM|VQA|IR|Bench|Eval)?\b", sentence)
    ignored = {"The", "This", "These", "We", "Our", "A", "An", "In", "To", "For", "Based", "Section"}
    entities: list[str] = []
    for candidate in candidates:
        if candidate in ignored or candidate in entities:
            continue
        entities.append(candidate)
    return entities


def _preferred_entity(entities: list[str]) -> str | None:
    for entity in entities:
        if any(token in entity for token in ("RAG", "LLM", "VQA", "Bench", "Eval")):
            return entity
    return entities[0] if entities else None


def _evidence_scope(evidence: PaperEvidence) -> str:
    if evidence.total_pages is None:
        return f"PDF {evidence.pages_read}페이지"
    return f"PDF {evidence.pages_read}/{evidence.total_pages}페이지"


def _section_text(evidence: PaperEvidence, *labels: str) -> str:
    parts: list[str] = []
    for label in labels:
        parts.extend(section.text for section in evidence.sections if section.label == label)
    return "\n".join(parts)


def _paper_kind(paper: Paper, evidence: PaperEvidence | None = None) -> str:
    title = paper.title.lower()
    abstract = paper.summary.lower()
    if any(signal in title for signal in ("overview", "challenge", "benchmark report", "survey")):
        return "benchmark"
    if any(signal in abstract for signal in ("challenge report", "describes the challenge", "final leaderboard")):
        return "benchmark"
    if any(signal in abstract for signal in ("we propose", "we introduce", "we present", "our approach")):
        return "research"

    benchmark_signals = (
        "challenge",
        "benchmark",
        "leaderboard",
        "track",
        "participants",
        "final standings",
        "evaluation protocol",
    )
    text = f"{title} {abstract}"
    if sum(1 for signal in benchmark_signals if signal in text) >= 2:
        return "benchmark"
    return "research"


def _one_line_summary(paper: Paper, evidence: PaperEvidence | None = None) -> str:
    kind = _paper_kind(paper, evidence)
    title = paper.title
    if kind == "benchmark":
        return f"{title}는 멀티모달 문서 검색/RAG 평가를 위한 벤치마크·챌린지 보고서입니다."
    if "rag" in title.lower() or "retrieval" in title.lower():
        return f"{title}는 검색 증강 생성에서 문서 구조와 검색/생성 파이프라인을 개선하려는 시스템 논문입니다."
    return f"{title}는 초록과 PDF 본문 근거를 바탕으로 선별된 관련 연구입니다."


def _contribution_judgment(paper: Paper, evidence: PaperEvidence | None = None) -> str:
    if _paper_kind(paper, evidence) == "benchmark":
        return "새 모델 제안 여부보다 태스크 정의, 평가 프로토콜, 참가 시스템 분석이 핵심 기여인지 확인했습니다."
    return "초록의 주장만 반복하지 않고, 본문에서 확인되는 시스템/프레임워크 수준의 차별점을 우선 기록했습니다."
