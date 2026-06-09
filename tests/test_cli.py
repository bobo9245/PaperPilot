from __future__ import annotations

from paperpilot.main import build_parser


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


def test_cli_defaults_to_auto_summary_backend() -> None:
    args = build_parser().parse_args(["curate", "retrieval augmented generation"])

    assert args.summary_backend == "auto"
    assert args.summary_model is None
    assert args.summary_detail == "standard"


def test_cli_parses_factchat_model_listing_command() -> None:
    args = build_parser().parse_args(["models", "--provider", "factchat"])

    assert args.command == "models"
    assert args.provider == "factchat"
