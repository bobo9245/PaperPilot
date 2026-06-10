from __future__ import annotations

from paperpilot.evaluation import run_evaluation


def test_fixture_evaluation_writes_markdown_and_json(tmp_path) -> None:
    result = run_evaluation(
        mode="fixture",
        scenario_ids=("multimodal_rag", "dlm_unlearning", "agentic_ai_evaluation"),
        output_dir=tmp_path,
        write_json=True,
    )

    assert result.output_path is not None
    assert result.output_path.exists()
    assert result.json_path is not None
    assert result.json_path.exists()
    assert len(result.runs) == 6

    content = result.output_path.read_text(encoding="utf-8")
    assert "## Summary Table" in content
    assert "## Presentation Takeaways" in content
    assert "## Conditions" in content
    assert "| multimodal_rag | baseline |" in content
    assert "| dlm_unlearning | agentic |" in content
    assert "baseline은 0개를 선택했지만 agentic은" in content
    assert "## Limitations" in content


def test_fixture_evaluation_agentic_improves_dlm_unlearning_selection(tmp_path) -> None:
    result = run_evaluation(
        mode="fixture",
        scenario_ids=("dlm_unlearning",),
        output_dir=tmp_path,
    )

    runs = {run.condition: run for run in result.runs}

    assert runs["baseline"].metrics.selected_count == 0
    assert runs["agentic"].metrics.selected_count >= 1
    assert runs["agentic"].metrics.replans >= 1
    assert runs["agentic"].metrics.deduped_count >= 1
