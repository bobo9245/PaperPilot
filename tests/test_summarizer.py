from __future__ import annotations

import json

from paperpilot.agents.summarizer import (
    AutoSummaryBackend,
    FactChatSummaryBackend,
    OpenAISummaryBackend,
    SUMMARY_REVIEWER_PROMPT,
    SummaryReviewerAgent,
    SummarizerAgent,
    build_evidence_pack,
    build_summary_backend,
    rewrite_for_reflection,
    validate_summary,
)
from paperpilot.models import PaperEvidence, PaperEvidenceSection, PaperSummary, ReflectionResult, ReviewScore


def _score() -> ReviewScore:
    return ReviewScore(
        relevance=1.0,
        novelty=0.8,
        experimental_strength=0.9,
        total=0.9,
        reason="test",
    )


def test_summarizer_attaches_summary_reviewer_feedback(make_paper) -> None:
    paper = make_paper(summary="We propose a retrieval augmented generation model with evaluation on 6 datasets.")
    score = _score()

    summary = SummarizerAgent().summarize(paper, score)

    assert summary.review is not None
    assert summary.review.overall_score > 0
    assert "### 6. Summary Reviewer" in summary.as_markdown()
    prompt = SummaryReviewerAgent().build_prompt(paper, score, summary)
    assert SUMMARY_REVIEWER_PROMPT in prompt
    assert "draft_summary" in prompt
    assert "grounding_score" in prompt


class FakeOpenAIResponse:
    def __init__(self, data: dict) -> None:
        self.output_text = json.dumps(data, ensure_ascii=False)


class FakeOpenAIResponses:
    def __init__(self, data: dict | None = None, error: Exception | None = None) -> None:
        self.data = data or _llm_summary_data()
        self.error = error
        self.calls: list[dict] = []

    def create(self, **kwargs):
        self.calls.append(kwargs)
        if self.error:
            raise self.error
        return FakeOpenAIResponse(self.data)


class FakeOpenAIClient:
    def __init__(self, data: dict | None = None, error: Exception | None = None) -> None:
        self.responses = FakeOpenAIResponses(data=data, error=error)


class FakeChatMessage:
    def __init__(self, data: dict) -> None:
        self.content = json.dumps(data, ensure_ascii=False)


class FakeChatChoice:
    def __init__(self, data: dict) -> None:
        self.message = FakeChatMessage(data)


class FakeChatCompletionResponse:
    def __init__(self, data: dict) -> None:
        self.choices = [FakeChatChoice(data)]


class FakeChatCompletions:
    def __init__(self, data: dict | None = None, error: Exception | None = None) -> None:
        self.data = data or _llm_summary_data()
        self.error = error
        self.calls: list[dict] = []

    def create(self, **kwargs):
        self.calls.append(kwargs)
        if self.error:
            raise self.error
        return FakeChatCompletionResponse(self.data)


class FakeChat:
    def __init__(self, data: dict | None = None, error: Exception | None = None) -> None:
        self.completions = FakeChatCompletions(data=data, error=error)


class FakeModel:
    def __init__(self, model_id: str) -> None:
        self.id = model_id


class FakeModels:
    def __init__(self, model_ids: tuple[str, ...] = ("gemini-2.5-flash",)) -> None:
        self.model_ids = model_ids

    def list(self):
        return type("FakeModelList", (), {"data": [FakeModel(model_id) for model_id in self.model_ids]})()


class FakeFactChatClient:
    def __init__(
        self,
        data: dict | None = None,
        error: Exception | None = None,
        model_ids: tuple[str, ...] = ("gemini-2.5-flash",),
    ) -> None:
        self.chat = FakeChat(data=data, error=error)
        self.models = FakeModels(model_ids)


def _llm_summary_data(**overrides) -> dict:
    data = {
        "one_line_summary": "엔터프라이즈 문서 QA를 위한 RAG 파이프라인을 제안한다.",
        "problem": "복잡한 문서의 표와 레이아웃 단서가 기존 텍스트 중심 RAG에서 충분히 활용되지 못한다.",
        "novelty": [
            "기존 텍스트 중심 RAG와 달리 문서 구조와 레이아웃 단서를 명시적으로 활용한다.",
            "파이프라인 구성 요소별 효과를 분리해 볼 수 있는 변형 설계를 제공한다.",
        ],
        "contributions": [
            "레이아웃 인식 청킹과 재랭킹을 결합한 RAG 프레임워크를 제시한다.",
            "검색 근거를 더 안정적으로 연결하는 시스템 설계를 정리한다.",
        ],
        "method_or_design": [
            "문서 페이지를 구조 단위로 나누고 reranking 모델로 후보 근거를 재정렬한다.",
            "검색된 근거를 기반으로 답변 생성 단계의 grounding을 강화한다.",
        ],
        "experiments": [
            "6개 데이터셋에서 answer faithfulness가 32% 개선되었다는 근거가 제시된다.",
            "dense retrieval, OCR-only retrieval, multimodal retrieval baseline과 비교한다.",
        ],
        "limitations": [
            "noisy OCR과 검색 문서 품질에 민감하다는 한계가 있다.",
            "더 큰 multilingual corpus 평가는 추가 확인 필요하다.",
        ],
        "evidence_notes": ["요약은 제공된 PDF evidence pack에 근거했다."],
        "confidence": "high",
    }
    data.update(overrides)
    return data


def test_summarizer_marks_missing_quantitative_results(make_paper) -> None:
    paper = make_paper(
        summary=(
            "We propose a benchmark for retrieval augmented generation. "
            "The abstract describes evaluation protocols but omits headline metrics."
        )
    )
    score = ReviewScore(
        relevance=1.0,
        novelty=0.7,
        experimental_strength=0.5,
        total=0.75,
        reason="test",
    )

    summary = SummarizerAgent().summarize(paper, score)

    assert "정량 실험 수치는 확인할 수 없습니다" in summary.experiments
    assert summary.reflection.passed


def test_summarizer_uses_pdf_evidence_when_available(make_paper) -> None:
    paper = make_paper(summary="This paper studies retrieval augmented generation.")
    evidence = PaperEvidence(
        source="pdf",
        text=(
            "We propose a retrieval augmented generation pipeline for enterprise QA. "
            "Our approach uses layout-aware chunking and a reranking model. "
            "Experiments on 6 datasets improve answer faithfulness by 32%. "
            "Limitations include sensitivity to noisy retrieved documents."
        ),
        pages_read=4,
        total_pages=12,
    )
    score = ReviewScore(
        relevance=1.0,
        novelty=0.7,
        experimental_strength=0.9,
        total=0.9,
        reason="test",
    )

    summary = SummarizerAgent().summarize(paper, score, evidence=evidence)

    assert "PDF 본문 근거를 바탕으로 정리한 요약" in summary.contribution
    assert "방법: PDF 본문 근거를 바탕으로 정리한 요약" in summary.method
    assert "6 datasets" in summary.experiments
    assert "32%" in summary.experiments
    assert "한계: PDF 본문 근거를 바탕으로 정리한 요약" in summary.limitations
    assert "근거:" in summary.contribution
    assert "근거:" in summary.method
    assert "해석 주의" in summary.experiments
    assert "추가 확인 필요" in summary.limitations


def test_summarizer_builds_detailed_pdf_summary(make_paper) -> None:
    paper = make_paper(
        title="Detailed Retrieval Augmented Generation",
        summary="This paper studies retrieval augmented generation for enterprise documents.",
    )
    evidence = PaperEvidence(
        source="pdf",
        text=(
            "However, enterprise documents contain charts, tables, and layout cues that text-only RAG misses. "
            "We propose a retrieval augmented generation pipeline for enterprise QA. "
            "We present a controlled variant study that isolates ingestion and embedding choices. "
            "Our approach uses layout-aware chunking and a reranking model. "
            "The pipeline routes pages through orientation-specific ingestion stages. "
            "Experiments on 6 datasets improve answer faithfulness by 32%. "
            "Evaluation compares dense retrieval, OCR-only retrieval, and multimodal retrieval baselines. "
            "Results show better evidence grounding on 4 benchmarks. "
            "Limitations include sensitivity to noisy retrieved documents. "
            "Future work should evaluate larger multilingual corpora."
        ),
        pages_read=6,
        total_pages=18,
    )
    score = ReviewScore(
        relevance=1.0,
        novelty=0.8,
        experimental_strength=0.9,
        total=0.9,
        reason="test",
    )

    summary = SummarizerAgent().summarize(paper, score, evidence=evidence)

    assert "PDF 문제 설정 근거(PDF 6/18페이지)" in summary.problem
    assert summary.contribution.count("- ") >= 4
    assert summary.method.count("- ") >= 4
    assert summary.experiments.count("- ") >= 4
    assert "6 datasets" in summary.experiments
    assert "4 benchmarks" in summary.experiments
    assert summary.limitations.count("- ") >= 4


def test_summarizer_uses_section_aware_evidence(make_paper) -> None:
    paper = make_paper(
        title="MM-BizRAG",
        summary="This paper studies multimodal retrieval augmented generation.",
    )
    evidence = PaperEvidence(
        source="pdf",
        text=(
            "However, enterprise documents contain layout cues. "
            "Our approach uses layout-aware chunking. "
            "Experiments on 6 datasets improve faithfulness by 32%. "
            "Limitations include noisy OCR."
        ),
        sections=(
            PaperEvidenceSection(
                label="introduction",
                heading="Introduction",
                text="However, enterprise documents contain layout cues that text-only RAG misses.",
            ),
            PaperEvidenceSection(
                label="method",
                heading="Method",
                text="Our approach uses layout-aware chunking and a reranking pipeline.",
            ),
            PaperEvidenceSection(
                label="experiments",
                heading="Experiments",
                text="Experiments on 6 datasets improve answer faithfulness by 32%.",
            ),
            PaperEvidenceSection(
                label="limitations",
                heading="Limitations",
                text="Limitations include noisy OCR and sensitivity to retrieved documents.",
            ),
        ),
        pages_read=6,
        total_pages=20,
    )
    score = ReviewScore(
        relevance=1.0,
        novelty=0.8,
        experimental_strength=0.9,
        total=0.9,
        reason="test",
    )

    summary = SummarizerAgent().summarize(paper, score, evidence=evidence)

    assert "PDF 문제 설정 근거" in summary.problem
    assert "Our approach uses layout-aware chunking" in summary.method
    assert "6 datasets" in summary.experiments
    assert "32%" in summary.experiments
    assert "Limitations include noisy OCR" in summary.limitations


def test_summarizer_formats_benchmark_reports_differently(make_paper) -> None:
    paper = make_paper(
        title="Overview of the Multimodal Document Retrieval Challenge",
        summary="This challenge report describes tasks, datasets, and evaluation protocol.",
    )
    evidence = PaperEvidence(
        source="pdf",
        text=(
            "The challenge asks participants to build a single retrieval system. "
            "The evaluation protocol compares leaderboard submissions from 22 teams. "
            "Discussion and lessons learned show one backbone and two specialised pipelines."
        ),
        sections=(
            PaperEvidenceSection(
                label="benchmark",
                heading="Tasks and Datasets",
                text=(
                    "The challenge asks participants to build a single retrieval system. "
                    "The evaluation protocol compares leaderboard submissions from 22 teams."
                ),
            ),
            PaperEvidenceSection(
                label="limitations",
                heading="Discussion",
                text="Discussion and lessons learned show one backbone and two specialised pipelines.",
            ),
        ),
        pages_read=5,
        total_pages=5,
    )
    score = ReviewScore(
        relevance=1.0,
        novelty=0.6,
        experimental_strength=0.8,
        total=0.8,
        reason="test",
    )

    summary = SummarizerAgent().summarize(paper, score, evidence=evidence)

    assert "벤치마크·챌린지 보고서" in summary.problem
    assert "보고서/벤치마크 기여" in summary.contribution or "초록 기준" in summary.contribution
    assert "구성/평가 설계" in summary.method
    assert "벤치마크/결과" in summary.experiments


def test_summarizer_avoids_rag_template_for_unlearning_benchmarks(make_paper) -> None:
    paper = make_paper(
        title="REMEDI: A Benchmark for Retention and Unlearning Evaluation",
        summary=(
            "Language models trained for clinical disease inference may include sensitive patient data. "
            "However, exactly unlearning patient-specific data is intractable. "
            "We introduce a structured benchmark for machine unlearning methods."
        ),
    )
    evidence = PaperEvidence(
        source="pdf",
        text=(
            "However, exactly unlearning patient-specific data is intractable. "
            "We introduce a structured and comprehensive benchmark called REMEDI. "
            "The evaluation framework measures utility and privacy. "
            "We evaluate four machine unlearning methods across three severity levels."
        ),
        sections=(
            PaperEvidenceSection(
                label="introduction",
                heading="Introduction",
                text="However, exactly unlearning patient-specific data is intractable.",
            ),
            PaperEvidenceSection(
                label="benchmark",
                heading="Benchmark",
                text=(
                    "We introduce a structured and comprehensive benchmark called REMEDI. "
                    "The evaluation framework measures utility and privacy."
                ),
            ),
            PaperEvidenceSection(
                label="experiments",
                heading="Experiments",
                text="We evaluate four machine unlearning methods across three severity levels.",
            ),
        ),
        pages_read=7,
        total_pages=7,
    )
    score = ReviewScore(
        relevance=1.0,
        novelty=0.8,
        experimental_strength=0.9,
        total=0.9,
        reason="test",
    )

    summary = SummarizerAgent().summarize(paper, score, evidence=evidence)
    full_text = " ".join(
        [
            summary.problem,
            summary.contribution,
            summary.method,
            summary.experiments,
            summary.limitations,
        ]
    )

    assert "모델 언러닝" in summary.problem
    assert "기존 RAG/검색 방식" not in full_text
    assert "멀티모달 문서 검색/RAG" not in full_text
    assert "레이아웃" not in summary.problem


def test_summarizer_keeps_system_papers_as_research_even_with_benchmarks(make_paper) -> None:
    paper = make_paper(
        title="MM-BizRAG: Rethinking Multimodal Retrieval-Augmented Generation",
        summary=(
            "We propose MM-BizRAG, a multimodal RAG framework. "
            "Experiments evaluate two public benchmarks and an enterprise dataset."
        ),
    )
    evidence = PaperEvidence(
        source="pdf",
        text=(
            "We propose MM-BizRAG, a multimodal RAG framework. "
            "Our approach uses document structure-aware splitting and ingestion pipelines. "
            "Through experiments on two public benchmarks, MM-BizRAG improves performance by 32%."
        ),
        sections=(
            PaperEvidenceSection(
                label="method",
                heading="Method",
                text="Our approach uses document structure-aware splitting and ingestion pipelines.",
            ),
        ),
        pages_read=4,
        total_pages=20,
    )
    score = ReviewScore(
        relevance=1.0,
        novelty=0.8,
        experimental_strength=0.9,
        total=0.9,
        reason="test",
    )

    summary = SummarizerAgent().summarize(paper, score, evidence=evidence)

    assert "시스템 논문" in summary.problem
    assert "핵심 기여" in summary.contribution
    assert "벤치마크/결과" not in summary.experiments
    assert "32%" in summary.experiments


def test_summarizer_uses_keyword_boundaries_for_pdf_evidence(make_paper) -> None:
    paper = make_paper(summary="This paper studies retrieval augmented generation.")
    evidence = PaperEvidence(
        source="pdf",
        text=(
            "This is a methodologically novel framework but not the method description. "
            "Our approach uses layout-aware chunking and a reranking model. "
            "Experiments improve answer faithfulness by 32%. "
            "Limitations include sensitivity to noisy retrieved documents."
        ),
        pages_read=2,
        total_pages=8,
    )
    score = ReviewScore(
        relevance=1.0,
        novelty=0.6,
        experimental_strength=0.8,
        total=0.8,
        reason="test",
    )

    summary = SummarizerAgent().summarize(paper, score, evidence=evidence)

    assert "Our approach uses layout-aware chunking" in summary.method


def test_summarizer_avoids_broad_model_mentions_for_method(make_paper) -> None:
    paper = make_paper(summary="This paper studies retrieval augmented generation.")
    evidence = PaperEvidence(
        source="pdf",
        text=(
            "Existing systems depend on pretrained embeddings or vision-language models to capture structure. "
            "Our approach uses layout-aware chunking and a reranking model. "
            "Experiments improve answer faithfulness by 32%. "
            "Limitations include sensitivity to noisy retrieved documents."
        ),
        pages_read=2,
        total_pages=8,
    )
    score = ReviewScore(
        relevance=1.0,
        novelty=0.6,
        experimental_strength=0.8,
        total=0.8,
        reason="test",
    )

    summary = SummarizerAgent().summarize(paper, score, evidence=evidence)

    assert "Existing systems depend" not in summary.method
    assert "Our approach uses layout-aware chunking" in summary.method


def test_summarizer_preserves_quantitative_units(make_paper) -> None:
    paper = make_paper(
        summary=(
            "Experiments on 6 datasets show a 12.4% improvement over baselines "
            "for retrieval augmented generation."
        )
    )
    score = ReviewScore(
        relevance=1.0,
        novelty=0.7,
        experimental_strength=1.0,
        total=0.9,
        reason="test",
    )

    summary = SummarizerAgent().summarize(paper, score)

    assert "6 datasets" in summary.experiments
    assert "12.4%" in summary.experiments


def test_summarizer_does_not_treat_bare_years_as_metrics(make_paper) -> None:
    paper = make_paper(
        summary=(
            "The MIR 2025 challenge track 1 describes evaluation protocols for "
            "multimodal retrieval augmented generation."
        )
    )
    score = ReviewScore(
        relevance=1.0,
        novelty=0.5,
        experimental_strength=0.6,
        total=0.8,
        reason="test",
    )

    summary = SummarizerAgent().summarize(paper, score)

    assert "2025" not in summary.experiments
    assert "정량 실험 수치는 확인할 수 없습니다" in summary.experiments


def test_summarizer_skips_section_numbers_as_metrics(make_paper) -> None:
    paper = make_paper(summary="This paper studies retrieval augmented generation.")
    evidence = PaperEvidence(
        source="pdf",
        text=(
            "3.1 Tasks describe the benchmark setup. "
            "2.1 Document parsing is used before retrieval. "
            "Experiments compare 22 teams on multimodal retrieval."
        ),
        pages_read=3,
        total_pages=5,
    )
    score = ReviewScore(
        relevance=1.0,
        novelty=0.6,
        experimental_strength=0.7,
        total=0.8,
        reason="test",
    )

    summary = SummarizerAgent().summarize(paper, score, evidence=evidence)

    assert "3.1 Tasks" not in summary.experiments
    assert "2.1 Document" not in summary.experiments
    assert "22 teams" in summary.experiments


def test_summarizer_reflection_accepts_percent_only_metrics(make_paper) -> None:
    paper = make_paper(summary="The method improves answer faithfulness by 32% over baselines.")
    score = ReviewScore(
        relevance=1.0,
        novelty=0.5,
        experimental_strength=0.8,
        total=0.8,
        reason="test",
    )

    summary = SummarizerAgent().summarize(paper, score)

    assert summary.experiments.endswith("32%입니다.")
    assert summary.reflection.passed


def test_openai_backend_uses_structured_response_schema(make_paper) -> None:
    paper = make_paper(summary="This paper studies retrieval augmented generation.")
    evidence = PaperEvidence(
        source="pdf",
        text=(
            "Enterprise documents contain charts and layout cues. "
            "Our approach uses layout-aware chunking and a reranking model. "
            "Experiments on 6 datasets improve answer faithfulness by 32%. "
            "Limitations include noisy OCR."
        ),
        sections=(
            PaperEvidenceSection(
                label="method",
                heading="Method",
                text="Our approach uses layout-aware chunking and a reranking model.",
            ),
            PaperEvidenceSection(
                label="experiments",
                heading="Experiments",
                text="Experiments on 6 datasets improve answer faithfulness by 32%.",
            ),
            PaperEvidenceSection(
                label="limitations",
                heading="Limitations",
                text="Limitations include noisy OCR.",
            ),
        ),
        pages_read=4,
        total_pages=12,
    )
    client = FakeOpenAIClient()
    backend = OpenAISummaryBackend(model="custom-summary-model", detail="deep", client=client)

    summary = backend.summarize(paper, _score(), evidence=evidence)

    call = client.responses.calls[0]
    assert call["model"] == "custom-summary-model"
    assert call["text"]["format"]["type"] == "json_schema"
    assert call["text"]["format"]["strict"] is True
    assert "novelty" in call["text"]["format"]["schema"]["required"]
    assert "엔터프라이즈 문서 QA" in summary.problem
    assert "새로움/차별점" in summary.contribution
    assert "레이아웃 인식 청킹" in summary.contribution
    assert "32%" in summary.experiments
    assert "Experiments on 6 datasets improve answer faithfulness by 32%" in summary.experiments
    assert summary.reflection.passed


def test_factchat_backend_uses_gateway_chat_schema(make_paper) -> None:
    paper = make_paper(summary="This paper studies retrieval augmented generation.")
    evidence = PaperEvidence(
        source="pdf",
        text=(
            "Enterprise documents contain charts and layout cues. "
            "Our approach uses layout-aware chunking and a reranking model. "
            "Experiments on 6 datasets improve answer faithfulness by 32%. "
            "Limitations include noisy OCR."
        ),
        pages_read=4,
        total_pages=12,
    )
    client = FakeFactChatClient()
    backend = FactChatSummaryBackend(model="claude-sonnet-4-6", detail="ultra", client=client)

    summary = backend.summarize(paper, _score(), evidence=evidence)

    call = client.chat.completions.calls[0]
    assert call["model"] == "claude-sonnet-4-6"
    assert call["response_format"]["type"] == "json_schema"
    assert call["response_format"]["json_schema"]["strict"] is True
    assert "novelty" in call["response_format"]["json_schema"]["schema"]["required"]
    assert "한국어 연구 논문 큐레이터" in call["messages"][0]["content"]
    assert "논문의 새로움" in call["messages"][0]["content"]
    assert "기존 방식 대비" in call["messages"][0]["content"]
    assert "FactChat 요약 backend" not in summary.contribution
    assert "새로움/차별점" in summary.contribution
    assert "32%" in summary.experiments
    assert summary.reflection.passed


def test_factchat_backend_auto_selects_available_model(make_paper) -> None:
    paper = make_paper(summary="This paper studies retrieval augmented generation.")
    client = FakeFactChatClient(model_ids=("custom-unlisted-model", "gemini-2.5-flash"))
    backend = FactChatSummaryBackend(model="auto", detail="standard", client=client)

    summary = backend.summarize(paper, _score())

    call = client.chat.completions.calls[0]
    assert call["model"] == "gemini-2.5-flash"
    assert backend.model == "gemini-2.5-flash"
    assert "새로움/차별점" in summary.contribution


def test_factchat_backend_cheap_selects_low_cost_model(make_paper) -> None:
    paper = make_paper(summary="This paper studies retrieval augmented generation.")
    client = FakeFactChatClient(
        model_ids=(
            "gpt-5.4-mini",
            "gpt-5.4-nano",
            "gemini-3.1-flash-lite",
        )
    )
    backend = FactChatSummaryBackend(model="cheap", detail="standard", client=client)

    summary = backend.summarize(paper, _score())

    call = client.chat.completions.calls[0]
    assert call["model"] == "gpt-5.4-nano"
    assert backend.model == "gpt-5.4-nano"
    assert "새로움/차별점" in summary.contribution


def test_factchat_backend_default_model_is_cheap() -> None:
    backend = build_summary_backend("factchat")

    assert backend.model == "cheap"


def test_ultra_detail_adds_novelty_focused_evidence(make_paper) -> None:
    paper = make_paper(summary="This paper studies retrieval augmented generation.")
    evidence = PaperEvidence(
        source="pdf",
        text=(
            "Unlike text-only RAG, we introduce a novel layout-aware retrieval pipeline. "
            "The first contribution is a document-structure split. "
            "We present three controlled variants for ablation. "
            "Our approach uses layout-aware chunking and a reranking model. "
            "Experiments on 6 datasets improve answer faithfulness by 32%. "
            "Limitations include noisy OCR."
        ),
        sections=(
            PaperEvidenceSection(
                label="introduction",
                heading="Introduction",
                text=(
                    "Unlike text-only RAG, we introduce a novel layout-aware retrieval pipeline. "
                    "The first contribution is a document-structure split. "
                    "We present three controlled variants for ablation."
                ),
            ),
            PaperEvidenceSection(
                label="method",
                heading="Method",
                text="Our approach uses layout-aware chunking and a reranking model.",
            ),
        ),
        pages_read=8,
        total_pages=20,
    )

    pack = build_evidence_pack(paper, _score(), evidence=evidence, detail="ultra")

    assert pack["detail"] == "ultra"
    assert "reading_focus" in pack
    assert pack["novelty_clues"]
    assert "novelty" in pack["sections"]
    assert len(pack["sections"]["novelty"]) >= 3


def test_auto_backend_falls_back_without_api_key(make_paper, monkeypatch) -> None:
    monkeypatch.delenv("FACTCHAT_API_KEY", raising=False)
    monkeypatch.delenv("PAPERPILOT_FACTCHAT_API_KEY", raising=False)
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    paper = make_paper(summary="This paper studies retrieval augmented generation.")
    backend = AutoSummaryBackend(
        openai_model="custom-openai-model",
        factchat_model="custom-factchat-model",
        detail="standard",
    )

    summary = backend.summarize(paper, _score())

    assert backend.fallback_reason == "FACTCHAT_API_KEY and OPENAI_API_KEY are not set"
    assert "초록 기준" in summary.contribution
    assert "OpenAI 요약 backend" not in summary.contribution


def test_auto_backend_falls_back_after_openai_error(make_paper, monkeypatch) -> None:
    monkeypatch.delenv("FACTCHAT_API_KEY", raising=False)
    monkeypatch.delenv("PAPERPILOT_FACTCHAT_API_KEY", raising=False)
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    paper = make_paper(summary="This paper studies retrieval augmented generation.")
    openai_backend = OpenAISummaryBackend(
        model="custom-summary-model",
        client=FakeOpenAIClient(error=RuntimeError("temporary failure")),
    )
    backend = AutoSummaryBackend(
        openai_model="custom-summary-model",
        factchat_model="custom-factchat-model",
        detail="standard",
        openai_backend=openai_backend,
    )

    summary = backend.summarize(paper, _score())

    assert backend.fallback_reason == "OpenAI summary failed: temporary failure"
    assert "초록 기준" in summary.contribution


def test_auto_backend_prefers_factchat_when_key_exists(make_paper, monkeypatch) -> None:
    monkeypatch.setenv("FACTCHAT_API_KEY", "test-key")
    monkeypatch.setenv("OPENAI_API_KEY", "openai-test-key")
    paper = make_paper(summary="This paper studies retrieval augmented generation.")
    factchat_backend = FactChatSummaryBackend(
        model="auto",
        client=FakeFactChatClient(),
    )
    backend = AutoSummaryBackend(
        openai_model="custom-openai-model",
        factchat_model="auto",
        detail="standard",
        factchat_backend=factchat_backend,
    )

    summary = backend.summarize(paper, _score())

    assert backend.model == "gemini-2.5-flash"
    assert backend.fallback_reason is None
    assert "새로움/차별점" in summary.contribution


def test_llm_summary_polishes_report_language(make_paper) -> None:
    paper = make_paper(summary="This paper studies retrieval augmented generation.")
    client = FakeOpenAIClient(
        data=_llm_summary_data(
            novelty=[
                "document structure-aware split는 evidence 범위에서 확인된다.",
            ],
            limitations=[
                "JSON 범위 내에서 baseline 상세는 확인 불가다.",
            ],
        )
    )
    backend = OpenAISummaryBackend(model="custom-summary-model", client=client)

    summary = backend.summarize(paper, _score())

    assert "문서 구조 인식 분할" in summary.contribution
    assert "제공된 근거 범위" in summary.contribution
    assert "비교 기준" in summary.limitations
    assert "JSON 범위" not in summary.limitations
    assert "evidence" not in summary.contribution


def test_openai_backend_marks_unsupported_numeric_claims(make_paper) -> None:
    paper = make_paper(summary="This paper studies retrieval augmented generation.")
    evidence = PaperEvidence(
        source="pdf",
        text=(
            "Our approach uses layout-aware chunking and a reranking model. "
            "Experiments on 6 datasets improve answer faithfulness by 32%. "
            "Limitations include noisy OCR."
        ),
        pages_read=4,
        total_pages=12,
    )
    client = FakeOpenAIClient(
        data=_llm_summary_data(
            experiments=[
                "6개 데이터셋에서 answer faithfulness가 99% 개선되었다고 요약한다.",
            ]
        )
    )
    backend = OpenAISummaryBackend(model="custom-summary-model", client=client)

    summary = backend.summarize(paper, _score(), evidence=evidence)

    assert "99%" in summary.limitations
    assert "확인 필요" in summary.limitations
    assert summary.reflection.passed


def test_openai_backend_keeps_benchmark_report_format(make_paper) -> None:
    paper = make_paper(
        title="EReL@MIR Challenge Overview",
        summary="This challenge report describes tasks, datasets, and evaluation protocol.",
    )
    evidence = PaperEvidence(
        source="pdf",
        text=(
            "The challenge defines retrieval tasks and datasets. "
            "The evaluation protocol compares leaderboard submissions from 22 teams. "
            "Discussion lists limitations and lessons learned."
        ),
        sections=(
            PaperEvidenceSection(
                label="benchmark",
                heading="Tasks and Datasets",
                text=(
                    "The challenge defines retrieval tasks and datasets. "
                    "The evaluation protocol compares leaderboard submissions from 22 teams."
                ),
            ),
            PaperEvidenceSection(
                label="limitations",
                heading="Discussion",
                text="Discussion lists limitations and lessons learned.",
            ),
        ),
        pages_read=5,
        total_pages=5,
    )
    client = FakeOpenAIClient(
        data=_llm_summary_data(
            one_line_summary="MIR 챌린지의 과제, 데이터셋, 평가 프로토콜을 정리한 보고서다.",
            problem="참가자들이 같은 검색 과제와 평가 기준으로 시스템을 비교할 필요가 있다.",
            method_or_design=[
                "retrieval task와 dataset 구성을 정의한다.",
                "leaderboard 제출물을 같은 evaluation protocol로 비교한다.",
            ],
            experiments=[
                "22개 팀의 제출 결과를 leaderboard 방식으로 비교한다.",
                "정량 세부 수치는 원문 표 확인이 추가 확인 필요하다.",
            ],
        )
    )
    backend = OpenAISummaryBackend(model="custom-summary-model", client=client)

    summary = backend.summarize(paper, _score(), evidence=evidence)

    assert "구성/평가 설계" in summary.method
    assert "벤치마크/결과" in summary.experiments
    assert summary.reflection.passed


def test_rewrite_for_reflection_patches_missing_sections() -> None:
    summary = PaperSummary(
        problem="문제: short",
        contribution="short",
        method="short",
        experiments="short",
        limitations="short",
    )
    reflection = validate_summary(summary)

    patched = rewrite_for_reflection(summary, reflection)

    assert patched.reflection.passed
    assert "핵심 기여" in patched.contribution
    assert "방법" in patched.method
    assert "실험" in patched.experiments
    assert "한계" in patched.limitations


def test_validate_summary_reports_issues() -> None:
    result = validate_summary(
        PaperSummary(
            problem="문제만 있음",
            contribution="없음",
            method="없음",
            experiments="없음",
            limitations="없음",
            reflection=ReflectionResult(passed=True),
        )
    )

    assert not result.passed
    assert "missing contribution" in result.issues
