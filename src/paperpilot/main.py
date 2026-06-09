"""Command line interface for PaperPilot."""

from __future__ import annotations

import argparse
from pathlib import Path

from paperpilot.agents.summarizer import SummaryBackendError, list_summary_models
from paperpilot.workflow import CurationWorkflow


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="paperpilot",
        description="Curate recent arXiv papers into a Korean Markdown brief.",
    )
    subparsers = parser.add_subparsers(dest="command")

    curate = subparsers.add_parser("curate", help="run the curation workflow")
    curate.add_argument("query", nargs="?", help="research query to search")
    curate.add_argument("--query", dest="query_option", help="research query to search")
    curate.add_argument("--days", type=int, default=7, help="recent publication window in days")
    curate.add_argument("--max-results", type=int, default=20, help="maximum arXiv results to inspect")
    curate.add_argument("--top-k", type=int, default=3, help="number of papers to select")
    curate.add_argument(
        "--min-relevance",
        type=float,
        default=0.8,
        help="minimum reviewer relevance score required for selection",
    )
    curate.add_argument(
        "--category",
        action="append",
        default=[],
        help="restrict arXiv search to a category such as cs.CL; may be repeated",
    )
    search_mode = curate.add_mutually_exclusive_group()
    search_mode.add_argument(
        "--strict-search",
        dest="strict_search",
        action="store_true",
        default=True,
        help="search title/abstract with phrase and AND constraints",
    )
    search_mode.add_argument(
        "--broad-search",
        dest="strict_search",
        action="store_false",
        help="search all arXiv fields with AND constraints",
    )
    curate.add_argument(
        "--with-pdf",
        action="store_true",
        help="download selected paper PDFs and use extracted text as summary evidence",
    )
    curate.add_argument(
        "--pdf-max-pages",
        type=int,
        default=6,
        help="maximum PDF pages to extract per selected paper when --with-pdf is enabled",
    )
    curate.add_argument(
        "--pdf-max-chars",
        type=int,
        default=16_000,
        help="maximum extracted PDF characters to keep per selected paper",
    )
    curate.add_argument(
        "--summary-backend",
        choices=("auto", "openai", "factchat", "heuristic"),
        default="auto",
        help=(
            "summary backend to use; auto uses FactChat when FACTCHAT_API_KEY is set, "
            "then OpenAI when OPENAI_API_KEY is set, and falls back otherwise"
        ),
    )
    curate.add_argument(
        "--summary-model",
        default=None,
        help="LLM model for summaries; defaults depend on the selected backend",
    )
    curate.add_argument(
        "--summary-detail",
        choices=("standard", "deep", "ultra"),
        default="standard",
        help="amount of evidence detail to send to the summary backend",
    )
    curate.add_argument("--output-dir", default="outputs", help="directory for Markdown reports")
    curate.add_argument("--dry-run", action="store_true", help="use built-in sample papers instead of arXiv")

    models = subparsers.add_parser("models", help="list available summary models")
    models.add_argument(
        "--provider",
        choices=("factchat",),
        default="factchat",
        help="summary provider to inspect",
    )

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.command == "models":
        try:
            for model in list_summary_models(args.provider):
                print(model)
        except SummaryBackendError as exc:
            parser.exit(1, f"error: {exc}\n")
        return 0

    if args.command != "curate":
        parser.print_help()
        return 0

    query = args.query_option or args.query
    if not query:
        parser.error("a query is required, for example: paperpilot curate 'rag evaluation'")

    workflow = CurationWorkflow()
    try:
        report = workflow.run(
            query,
            days=args.days,
            max_results=args.max_results,
            top_k=args.top_k,
            min_relevance=args.min_relevance,
            categories=_normalize_categories(args.category),
            strict_search=args.strict_search,
            with_pdf=args.with_pdf,
            pdf_max_pages=args.pdf_max_pages,
            pdf_max_chars=args.pdf_max_chars,
            summary_backend=args.summary_backend,
            summary_model=args.summary_model,
            summary_detail=args.summary_detail,
            dry_run=args.dry_run,
            output_dir=Path(args.output_dir),
        )
    except SummaryBackendError as exc:
        parser.exit(1, f"error: {exc}\n")
    print(f"Saved curation report: {report.output_path}")
    print(f"Selected papers: {len(report.selected)}")
    return 0


def _normalize_categories(values: list[str]) -> tuple[str, ...]:
    categories: list[str] = []
    for value in values:
        categories.extend(category.strip() for category in value.split(","))
    return tuple(category for category in categories if category)


if __name__ == "__main__":
    raise SystemExit(main())
