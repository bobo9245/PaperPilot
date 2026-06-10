from __future__ import annotations

from paperpilot.agents.searcher import SearcherAgent
from paperpilot.models import PaperEvidence
from paperpilot.workflow import CurationWorkflow


def test_workflow_fetches_pdf_evidence_for_selected_papers(make_paper, tmp_path) -> None:
    paper = make_paper(
        title="Retrieval Augmented Generation with Evidence",
        summary="We propose a retrieval augmented generation model with evaluation.",
    )

    def fake_search(query: str, **kwargs):
        return (paper,)

    class FakePdfExtractor:
        def fetch(self, paper, *, max_pages: int, max_chars: int):
            assert max_pages == 2
            assert max_chars == 32_000
            return PaperEvidence(
                source="pdf",
                text=(
                    "We propose a retrieval augmented generation pipeline. "
                    "Our approach uses a reranking model. "
                    "Experiments improve answer faithfulness by 32%. "
                    "Limitations include sensitivity to noisy retrieved documents."
                ),
                pages_read=2,
                total_pages=10,
            )

    workflow = CurationWorkflow(
        searcher=SearcherAgent(fake_search, min_results=1),
        pdf_extractor=FakePdfExtractor(),
    )

    report = workflow.run(
        "retrieval augmented generation",
        top_k=1,
        with_pdf=True,
        pdf_max_pages=2,
        pdf_max_chars=32_000,
        summary_backend="heuristic",
        output_dir=tmp_path,
    )

    assert report.with_pdf
    assert report.pdf_max_pages == 2
    assert report.pdf_max_chars == 32_000
    assert report.selected[0].evidence is not None
    assert report.selected[0].evidence.available
    assert "PDF 본문" in report.selected[0].summary.method
    assert "32%" in report.selected[0].summary.experiments
    assert report.output_path is not None
    assert report.candidate_count == 1
    trace_steps = [event.step for event in report.trace]
    assert "extract_pdf" in trace_steps
    assert "summarize" in trace_steps
    assert "reflect" in trace_steps
    assert any(event.step == "review" for event in report.trace)
    content = report.output_path.read_text(encoding="utf-8")
    assert "- PDF evidence: Enabled, max pages 2, max chars 32000" in content
    assert "## Agent Trace" in content
    assert "| review | Score relevance, novelty, and experimental strength |" in content


def test_workflow_records_auto_summary_fallback(make_paper, tmp_path, monkeypatch) -> None:
    monkeypatch.delenv("FACTCHAT_API_KEY", raising=False)
    monkeypatch.delenv("PAPERPILOT_FACTCHAT_API_KEY", raising=False)
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    paper = make_paper(
        title="Retrieval Augmented Generation with Evidence",
        summary="We propose a retrieval augmented generation model with evaluation on 6 datasets.",
    )

    def fake_search(query: str, **kwargs):
        return (paper,)

    workflow = CurationWorkflow(searcher=SearcherAgent(fake_search, min_results=1))

    report = workflow.run(
        "retrieval augmented generation",
        top_k=1,
        summary_backend="auto",
        summary_model="custom-summary-model",
        output_dir=tmp_path,
    )

    assert report.summary_backend == "auto"
    assert report.summary_model == "custom-summary-model"
    assert report.summary_detail == "standard"
    assert report.summary_fallback_reason == "FACTCHAT_API_KEY and OPENAI_API_KEY are not set"
    assert any(event.step == "fallback" for event in report.trace)
    assert "핵심 기여" in report.selected[0].summary.contribution
    assert "OpenAI 요약 backend" not in report.selected[0].summary.contribution


def test_workflow_combines_multisource_search_results(make_paper, tmp_path) -> None:
    arxiv_paper = make_paper(
        title="Shared Multimodal RAG Paper",
        source_id="2606.00001",
        source="arxiv",
        doi="10.1234/shared",
    )
    openalex_paper = make_paper(
        title="Shared Multimodal RAG Paper",
        source_id="openalex-1",
        source="openalex",
        doi="10.1234/shared",
        citation_count=55,
        venue="ICLR",
    )

    def arxiv_search(query: str, **kwargs):
        return (arxiv_paper,)

    def openalex_search(query: str, **kwargs):
        return (openalex_paper,)

    workflow = CurationWorkflow(
        searcher=SearcherAgent(
            {
                "arxiv": arxiv_search,
                "openalex": openalex_search,
            },
            min_results=1,
        )
    )

    report = workflow.run(
        "multimodal retrieval augmented generation",
        top_k=1,
        sources=("arxiv", "openalex"),
        query_expansion="off",
        summary_backend="heuristic",
        scholar_links=True,
        output_dir=tmp_path,
    )

    assert len(report.selected) == 1
    paper = report.selected[0].reviewed.paper
    assert paper.source == "arxiv, openalex"
    assert paper.citation_count == 55
    assert paper.venue == "ICLR"
    assert report.deduped_count == 1
    assert [attempt.source for attempt in report.attempts] == ["arxiv", "openalex"]
    content = report.output_path.read_text(encoding="utf-8")
    assert "| arxiv | multimodal retrieval augmented generation | success | 1 |" in content
    assert "- Google Scholar: https://scholar.google.com/scholar?q=Shared+Multimodal+RAG+Paper" in content


def test_workflow_records_pdf_abstract_fallback_decision(make_paper, tmp_path) -> None:
    paper = make_paper(
        title="Retrieval Augmented Generation without PDF",
        summary="We propose a retrieval augmented generation model with evaluation.",
    )

    class FailingPdfExtractor:
        def fetch(self, paper, *, max_pages: int, max_chars: int):
            return PaperEvidence(source="pdf", error="paper has no PDF URL")

    workflow = CurationWorkflow(
        searcher=SearcherAgent(lambda query, **kwargs: (paper,), min_results=1),
        pdf_extractor=FailingPdfExtractor(),
    )

    report = workflow.run(
        "retrieval augmented generation",
        top_k=1,
        with_pdf=True,
        summary_backend="heuristic",
        output_dir=tmp_path,
    )

    assert report.selected[0].evidence is not None
    assert not report.selected[0].evidence.available
    assert any("use_abstract_fallback" in event.action for event in report.trace)


def test_workflow_falls_back_when_forced_summary_backend_fails(make_paper, tmp_path, monkeypatch) -> None:
    monkeypatch.delenv("FACTCHAT_API_KEY", raising=False)
    monkeypatch.delenv("PAPERPILOT_FACTCHAT_API_KEY", raising=False)
    paper = make_paper(
        title="Retrieval Augmented Generation with Fallback",
        summary="We propose a retrieval augmented generation model with experiments on 5 datasets.",
    )

    workflow = CurationWorkflow(searcher=SearcherAgent(lambda query, **kwargs: (paper,), min_results=1))

    report = workflow.run(
        "retrieval augmented generation",
        top_k=1,
        summary_backend="factchat",
        output_dir=tmp_path,
    )

    assert len(report.selected) == 1
    assert report.summary_fallback_reason is not None
    assert any("use_heuristic_summary_fallback" in event.action for event in report.trace)


def test_workflow_writes_failure_analysis_when_zero_selected(make_paper, tmp_path) -> None:
    paper = make_paper(
        title="Unrelated Optimization Paper",
        summary="This paper studies database indexing and storage optimization.",
    )
    workflow = CurationWorkflow(searcher=SearcherAgent(lambda query, **kwargs: (paper,), min_results=1))

    report = workflow.run(
        "retrieval augmented generation",
        top_k=1,
        min_relevance=0.95,
        summary_backend="heuristic",
        output_dir=tmp_path,
    )

    assert not report.selected
    assert any("stop_with_failure_analysis" in event.action for event in report.trace)
    content = report.output_path.read_text(encoding="utf-8")
    assert "## Failure Analysis" in content
    assert "No papers were selected." in content
