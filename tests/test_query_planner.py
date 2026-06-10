from __future__ import annotations

from paperpilot.agents.query_planner import QueryPlannerAgent


def test_query_planner_expands_multimodal_rag_query() -> None:
    planner = QueryPlannerAgent(mode="basic", max_variants=6)

    variants = planner.plan("multimodal retrieval augmented generation")

    assert variants[0] == "multimodal retrieval augmented generation"
    assert "multimodal RAG" in variants
    assert "vision-language RAG" in variants
    assert "multimodal document retrieval" in variants
    assert len(variants) == 6


def test_query_planner_expands_dllm_unlearning_query() -> None:
    planner = QueryPlannerAgent(mode="basic", max_variants=7)

    variants = planner.plan("dllm unlearning")

    assert variants[0] == "dllm unlearning"
    assert "diffusion language model unlearning" in variants
    assert "language model unlearning" in variants
    assert "LLM unlearning" in variants


def test_query_planner_can_disable_expansion() -> None:
    planner = QueryPlannerAgent(mode="off", max_variants=6)

    assert planner.plan("multimodal retrieval augmented generation") == (
        "multimodal retrieval augmented generation",
    )
