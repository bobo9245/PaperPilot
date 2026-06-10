from __future__ import annotations

import pytest

import paperpilot.main as main_module
from paperpilot.main import _apply_cost_profile, _normalize_sources, build_parser


def test_cli_parses_summary_backend_options() -> None:
    args = build_parser().parse_args(
        [
            "curate",
            "retrieval augmented generation",
            "--pdf-max-chars",
            "64000",
            "--summary-backend",
            "factchat",
            "--summary-model",
            "claude-sonnet-4-6",
            "--summary-detail",
            "ultra",
        ]
    )

    assert args.pdf_max_chars == 64_000
    assert args.summary_backend == "factchat"
    assert args.summary_model == "claude-sonnet-4-6"
    assert args.summary_detail == "ultra"


def test_cli_applies_dev_cost_profile_defaults() -> None:
    args = build_parser().parse_args(
        [
            "curate",
            "retrieval augmented generation",
            "--cost-profile",
            "dev",
        ]
    )

    _apply_cost_profile(args)

    assert args.top_k == 1
    assert args.pdf_max_pages == 8
    assert args.pdf_max_chars == 24_000
    assert args.summary_model == "gpt-5.4-nano"
    assert args.summary_detail == "deep"


def test_cli_explicit_options_override_cost_profile() -> None:
    args = build_parser().parse_args(
        [
            "curate",
            "retrieval augmented generation",
            "--cost-profile",
            "dev",
            "--top-k",
            "2",
            "--pdf-max-chars",
            "48000",
            "--summary-model",
            "gpt-5.4-mini",
            "--summary-detail",
            "ultra",
        ]
    )

    _apply_cost_profile(args)

    assert args.top_k == 2
    assert args.pdf_max_pages == 8
    assert args.pdf_max_chars == 48_000
    assert args.summary_model == "gpt-5.4-mini"
    assert args.summary_detail == "ultra"


def test_cli_defaults_to_auto_summary_backend() -> None:
    args = build_parser().parse_args(["curate", "retrieval augmented generation"])

    assert args.summary_backend == "auto"
    assert args.summary_model is None
    assert args.summary_detail == "standard"
    assert args.sources == "arxiv"
    assert args.query_expansion == "basic"
    assert args.max_query_variants == 6
    assert args.agentic_mode == "policy"
    assert args.max_agent_steps == 6
    assert args.failure_analysis is True
    assert not args.scholar_links


def test_cli_parses_multisource_search_options() -> None:
    args = build_parser().parse_args(
        [
            "curate",
            "retrieval augmented generation",
            "--sources",
            "arxiv,semantic-scholar,openalex",
            "--query-expansion",
            "basic",
            "--max-query-variants",
            "6",
            "--scholar-links",
        ]
    )

    assert _normalize_sources(args.sources) == ("arxiv", "semantic-scholar", "openalex")
    assert args.query_expansion == "basic"
    assert args.max_query_variants == 6
    assert args.scholar_links


def test_cli_parses_factchat_model_listing_command() -> None:
    args = build_parser().parse_args(["models", "--provider", "factchat"])

    assert args.command == "models"
    assert args.provider == "factchat"


def test_cli_parses_factchat_credits_command() -> None:
    args = build_parser().parse_args(["credits", "--provider", "factchat"])

    assert args.command == "credits"
    assert args.provider == "factchat"


def test_cli_parses_eval_command() -> None:
    args = build_parser().parse_args(
        [
            "eval",
            "--mode",
            "fixture",
            "--scenario",
            "dlm_unlearning",
            "--json",
        ]
    )

    assert args.command == "eval"
    assert args.mode == "fixture"
    assert args.scenario == "dlm_unlearning"
    assert args.write_json


def test_cli_parses_agentic_workflow_options() -> None:
    args = build_parser().parse_args(
        [
            "curate",
            "retrieval augmented generation",
            "--agentic-mode",
            "off",
            "--max-agent-steps",
            "3",
            "--no-failure-analysis",
        ]
    )

    assert args.agentic_mode == "off"
    assert args.max_agent_steps == 3
    assert args.failure_analysis is False


def test_main_rejects_invalid_max_agent_steps() -> None:
    with pytest.raises(SystemExit) as exc:
        main_module.main(["curate", "rag", "--max-agent-steps", "0"])

    assert exc.value.code == 2


def test_main_runs_fixture_evaluation(tmp_path, capsys) -> None:
    assert (
        main_module.main(
            [
                "eval",
                "--mode",
                "fixture",
                "--scenario",
                "dlm_unlearning",
                "--output-dir",
                str(tmp_path),
            ]
        )
        == 0
    )

    output = capsys.readouterr().out
    assert "Saved evaluation report:" in output
    assert "Evaluation runs: 2" in output
    assert list(tmp_path.glob("*_eval.md"))


def test_main_rejects_live_eval_all() -> None:
    with pytest.raises(SystemExit) as exc:
        main_module.main(["eval", "--mode", "live", "--all"])

    assert exc.value.code == 2


def test_main_prints_factchat_credits(monkeypatch, capsys) -> None:
    monkeypatch.setattr(
        main_module,
        "get_summary_credits",
        lambda provider: {
            "monthly_allocated": {
                "quota": 20_000,
                "used": 123.5,
                "remaining": 19_876.5,
                "renewal_date": "2026-07-01T00:00:00+09:00",
            },
            "purchased": {"quota": 0, "used": 0, "remaining": 0},
            "total": {"quota": 20_000, "used": 123.5, "remaining": 19_876.5},
        },
    )

    assert main_module.main(["credits", "--provider", "factchat"]) == 0

    output = capsys.readouterr().out
    assert "FactChat credits" in output
    assert "Total: quota 20000, used 123.5, remaining 19876.5" in output
