from __future__ import annotations

from paperpilot.agents.reviewer import ReviewerAgent


def test_reviewer_ranks_relevant_experimental_paper_first(make_paper) -> None:
    strong = make_paper(
        title="Novel Retrieval Augmented Generation Benchmark",
        summary=(
            "We introduce a novel retrieval augmented generation benchmark. "
            "Experiments on 8 datasets improve accuracy by 9%."
        ),
        source_id="strong",
    )
    weak = make_paper(
        title="A General Note on Optimization",
        summary="This note discusses broad optimization ideas without evaluation.",
        source_id="weak",
    )

    ranked = ReviewerAgent().rank((weak, strong), query="retrieval augmented generation")

    assert ranked[0].paper.source_id == "strong"
    assert ranked[0].score.relevance == 1.0
    assert ranked[0].score.experimental_strength > ranked[1].score.experimental_strength


def test_reviewer_filters_below_min_relevance(make_paper) -> None:
    relevant = make_paper(
        title="Retrieval Augmented Generation for Long Context QA",
        summary="We propose a retrieval augmented generation method with evaluation on 4 datasets.",
        source_id="relevant",
    )
    unrelated = make_paper(
        title="Manifold Aware Diffusion for Image Generation",
        summary="A novel diffusion model improves generation quality on image benchmarks.",
        source_id="unrelated",
    )

    ranked = ReviewerAgent().rank(
        (unrelated, relevant),
        query="retrieval augmented generation",
        min_relevance=0.6,
    )

    assert [item.paper.source_id for item in ranked] == ["relevant"]


def test_reviewer_matches_acronyms_for_relevance(make_paper) -> None:
    paper = make_paper(
        title="DLM Unlearning for Text Generation",
        summary="We propose an unlearning method for discrete diffusion language models.",
        source_id="dlm",
    )

    score = ReviewerAgent().score(paper, query="diffusion language model unlearning")

    assert score.relevance >= 0.8


def test_reviewer_treats_llm_unlearning_as_dlm_unlearning_fallback(make_paper) -> None:
    paper = make_paper(
        title="Large Language Model Unlearning",
        summary="We propose an LLM unlearning method with experiments.",
        source_id="llm-unlearning",
    )

    score = ReviewerAgent().score(paper, query="diffusion language model unlearning")

    assert score.relevance >= 0.8
