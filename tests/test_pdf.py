from __future__ import annotations

from paperpilot.tools.pdf import PdfEvidenceExtractor, clean_pdf_text, extract_sections


def test_clean_pdf_text_normalizes_whitespace() -> None:
    assert clean_pdf_text("  Method   section  \n\n  Results\t 32%  ") == "Method section\nResults 32%"


def test_clean_pdf_text_repairs_hyphenated_line_breaks() -> None:
    assert clean_pdf_text("state- of-the-art\ncom- prising\nMM- BizRAG") == (
        "state-of-the-art\ncomprising\nMM-BizRAG"
    )


def test_clean_pdf_text_repairs_common_joined_tokens() -> None:
    text = clean_pdf_text(
        "approach:MM-BizRAGproactively uses adocument structureaware splitthat works. Pipelines.Every test "
        "We introduceFastRAGEval and asingle system within0.1point. LLM s work. "
        "A studycomprising variants attracted455 entrants and relevantpagesof documents reach100%."
    )

    assert text == (
        "approach: MM-BizRAG proactively uses a document structure-aware split that works. "
        "Pipelines. Every test We introduce FastRAGEval and a single system within 0.1 point. LLMs work. "
        "A study comprising variants attracted 455 entrants and relevant pages of documents reach 100%."
    )


def test_pdf_extractor_handles_missing_pdf_url(make_paper) -> None:
    paper = make_paper(source_id="no-pdf")
    paper = paper.__class__(
        title=paper.title,
        authors=paper.authors,
        summary=paper.summary,
        published=paper.published,
        updated=paper.updated,
        url=paper.url,
        pdf_url=None,
        categories=paper.categories,
        source_id=paper.source_id,
    )

    evidence = PdfEvidenceExtractor().fetch(paper)

    assert not evidence.available
    assert evidence.error == "paper has no PDF URL"


def test_extract_sections_labels_common_paper_headings() -> None:
    sections = extract_sections(
        """
Abstract
This paper studies multimodal retrieval augmented generation for complex documents.
1 Introduction
However, existing retrieval systems miss layout signals in enterprise documents.
2 Method
Our approach uses document-aware chunking and a reranking pipeline.
3 Experiments
Experiments on 6 datasets improve accuracy by 32%.
5 Discussion and Limitations
Limitations include sensitivity to noisy OCR and retrieved documents.
"""
    )

    assert [section.label for section in sections] == [
        "abstract",
        "introduction",
        "method",
        "experiments",
        "limitations",
    ]
    assert sections[2].heading == "Method"
