"""Command line interface for PaperPilot."""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any

from paperpilot.agents.summarizer import SummaryBackendError, get_summary_credits, list_summary_models
from paperpilot.evaluation import EVALUATION_SCENARIOS, run_evaluation
from paperpilot.workflow import CurationWorkflow


COST_PROFILE_DEFAULTS: dict[str, dict[str, Any]] = {
    "dev": {
        "top_k": 1,
        "pdf_max_pages": 8,
        "pdf_max_chars": 24_000,
        "summary_model": "gpt-5.4-nano",
        "summary_detail": "deep",
    },
    "balanced": {
        "top_k": 1,
        "pdf_max_pages": 12,
        "pdf_max_chars": 32_000,
        "summary_model": "gpt-5.4-nano",
        "summary_detail": "ultra",
    },
    "final": {
        "top_k": 3,
        "pdf_max_pages": 20,
        "pdf_max_chars": 64_000,
        "summary_model": "gpt-5.4-mini",
        "summary_detail": "ultra",
    },
}


class _RecordExplicit(argparse.Action):
    """argparse action that records which options the user passed explicitly."""

    def __call__(
        self,
        parser: argparse.ArgumentParser,
        namespace: argparse.Namespace,
        values: Any,
        option_string: str | None = None,
    ) -> None:
        explicit = set(getattr(namespace, "_explicit_options", set()))
        explicit.add(self.dest)
        setattr(namespace, "_explicit_options", explicit)
        setattr(namespace, self.dest, values)


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
    curate.add_argument("--top-k", type=int, default=3, action=_RecordExplicit, help="number of papers to select")
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
    curate.add_argument(
        "--sources",
        default="arxiv",
        help="comma-separated search sources: arxiv, semantic-scholar, openalex",
    )
    curate.add_argument(
        "--query-expansion",
        choices=("off", "basic"),
        default="basic",
        help="expand the input query into deterministic search variants",
    )
    curate.add_argument(
        "--max-query-variants",
        type=int,
        default=6,
        help="maximum number of query variants to try when query expansion is enabled",
    )
    curate.add_argument(
        "--agentic-mode",
        choices=("off", "policy", "hybrid"),
        default="policy",
        help="control the observe-decide-act loop; hybrid currently uses guarded policy behavior",
    )
    curate.add_argument(
        "--max-agent-steps",
        type=int,
        default=6,
        help="maximum recovery/replanning decisions the policy agent may take",
    )
    curate.add_argument(
        "--failure-analysis",
        dest="failure_analysis",
        action="store_true",
        default=True,
        help="include failure analysis when no papers are selected",
    )
    curate.add_argument(
        "--no-failure-analysis",
        dest="failure_analysis",
        action="store_false",
        help="omit the zero-selected failure analysis section",
    )
    curate.add_argument(
        "--scholar-links",
        action="store_true",
        help="include manual Google Scholar search links in the report without scraping Scholar",
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
        action=_RecordExplicit,
        help="maximum PDF pages to extract per selected paper when --with-pdf is enabled",
    )
    curate.add_argument(
        "--pdf-max-chars",
        type=int,
        default=16_000,
        action=_RecordExplicit,
        help="maximum extracted PDF characters to keep per selected paper",
    )
    curate.add_argument(
        "--cost-profile",
        choices=tuple(COST_PROFILE_DEFAULTS),
        default=None,
        help="apply low-cost presets for top-k, PDF budget, summary model, and summary detail",
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
        action=_RecordExplicit,
        help="LLM model for summaries; use 'cheap' with FactChat to prefer low-cost models",
    )
    curate.add_argument(
        "--summary-detail",
        choices=("standard", "deep", "ultra"),
        default="standard",
        action=_RecordExplicit,
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

    credits = subparsers.add_parser("credits", help="show available summary credits")
    credits.add_argument(
        "--provider",
        choices=("factchat",),
        default="factchat",
        help="summary provider to inspect",
    )

    evaluate = subparsers.add_parser("eval", help="run repeatable project evaluation scenarios")
    evaluate.add_argument(
        "--mode",
        choices=("fixture", "live"),
        default="fixture",
        help="fixture is cost-free; live calls external search/PDF APIs",
    )
    evaluate.add_argument(
        "--scenario",
        choices=tuple(EVALUATION_SCENARIOS),
        default=None,
        help="single evaluation scenario to run",
    )
    evaluate.add_argument("--all", action="store_true", help="run every fixture evaluation scenario")
    evaluate.add_argument(
        "--sources",
        default="arxiv,openalex",
        help="comma-separated sources for the agentic condition in live mode",
    )
    evaluate.add_argument("--top-k", type=int, default=3, action=_RecordExplicit)
    evaluate.add_argument("--pdf-max-pages", type=int, default=8, action=_RecordExplicit)
    evaluate.add_argument("--pdf-max-chars", type=int, default=24_000, action=_RecordExplicit)
    evaluate.add_argument("--max-agent-steps", type=int, default=6)
    evaluate.add_argument(
        "--cost-profile",
        choices=tuple(COST_PROFILE_DEFAULTS),
        default=None,
        help="apply low-cost presets to the agentic evaluation condition",
    )
    evaluate.add_argument(
        "--summary-backend",
        choices=("auto", "openai", "factchat", "heuristic"),
        default="heuristic",
        help="summary backend for the agentic condition",
    )
    evaluate.add_argument(
        "--summary-model",
        default=None,
        action=_RecordExplicit,
        help="LLM model for the agentic condition",
    )
    evaluate.add_argument(
        "--summary-detail",
        choices=("standard", "deep", "ultra"),
        default="deep",
        action=_RecordExplicit,
        help="summary detail for the agentic condition",
    )
    evaluate.add_argument("--output-dir", default="outputs/evaluations")
    evaluate.add_argument("--json", dest="write_json", action="store_true", help="also write JSON metrics")

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

    if args.command == "credits":
        try:
            print(_format_credits(get_summary_credits(args.provider)))
        except SummaryBackendError as exc:
            parser.exit(1, f"error: {exc}\n")
        return 0

    if args.command == "eval":
        _apply_cost_profile(args)
        if args.max_agent_steps < 1:
            parser.error("--max-agent-steps must be at least 1")
        if args.mode == "live" and (args.all or not args.scenario):
            parser.error("live evaluation requires exactly one --scenario and does not support --all")
        if args.mode == "fixture" and not args.all and not args.scenario:
            parser.error("fixture evaluation requires --all or --scenario")
        try:
            sources = _normalize_sources(args.sources)
        except ValueError as exc:
            parser.error(str(exc))
        scenario_ids = tuple(EVALUATION_SCENARIOS) if args.all else (args.scenario,)
        try:
            result = run_evaluation(
                mode=args.mode,
                scenario_ids=scenario_ids,
                output_dir=Path(args.output_dir),
                sources=sources,
                top_k=args.top_k,
                pdf_max_pages=args.pdf_max_pages,
                pdf_max_chars=args.pdf_max_chars,
                summary_backend=args.summary_backend,
                summary_model=args.summary_model,
                summary_detail=args.summary_detail,
                max_agent_steps=args.max_agent_steps,
                write_json=args.write_json,
            )
        except SummaryBackendError as exc:
            parser.exit(1, f"error: {exc}\n")
        print(f"Saved evaluation report: {result.output_path}")
        if result.json_path:
            print(f"Saved evaluation JSON: {result.json_path}")
        print(f"Evaluation runs: {len(result.runs)}")
        return 0

    if args.command != "curate":
        parser.print_help()
        return 0

    _apply_cost_profile(args)
    query = args.query_option or args.query
    if not query:
        parser.error("a query is required, for example: paperpilot curate 'rag evaluation'")
    try:
        sources = _normalize_sources(args.sources)
    except ValueError as exc:
        parser.error(str(exc))
    if args.max_agent_steps < 1:
        parser.error("--max-agent-steps must be at least 1")

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
            sources=sources,
            query_expansion=args.query_expansion,
            max_query_variants=args.max_query_variants,
            scholar_links=args.scholar_links,
            with_pdf=args.with_pdf,
            pdf_max_pages=args.pdf_max_pages,
            pdf_max_chars=args.pdf_max_chars,
            summary_backend=args.summary_backend,
            summary_model=args.summary_model,
            summary_detail=args.summary_detail,
            agentic_mode=args.agentic_mode,
            max_agent_steps=args.max_agent_steps,
            failure_analysis=args.failure_analysis,
            dry_run=args.dry_run,
            output_dir=Path(args.output_dir),
        )
    except SummaryBackendError as exc:
        parser.exit(1, f"error: {exc}\n")
    print(f"Saved curation report: {report.output_path}")
    if report.log_output_path:
        print(f"Saved curation log: {report.log_output_path}")
    print(f"Selected papers: {len(report.selected)}")
    return 0


def _normalize_categories(values: list[str]) -> tuple[str, ...]:
    categories: list[str] = []
    for value in values:
        categories.extend(category.strip() for category in value.split(","))
    return tuple(category for category in categories if category)


def _normalize_sources(value: str) -> tuple[str, ...]:
    allowed = {"arxiv", "semantic-scholar", "openalex"}
    aliases = {
        "semantic_scholar": "semantic-scholar",
        "semanticscholar": "semantic-scholar",
        "s2": "semantic-scholar",
        "open-alex": "openalex",
    }
    sources: list[str] = []
    for raw_source in value.split(","):
        source = aliases.get(raw_source.strip().lower(), raw_source.strip().lower())
        if not source:
            continue
        if source not in allowed:
            raise ValueError(f"unknown search source: {raw_source.strip()}")
        sources.append(source)
    return tuple(dict.fromkeys(sources))


def _apply_cost_profile(args: argparse.Namespace) -> argparse.Namespace:
    profile = getattr(args, "cost_profile", None)
    if not profile:
        return args
    explicit = set(getattr(args, "_explicit_options", set()))
    for key, value in COST_PROFILE_DEFAULTS[profile].items():
        if key not in explicit:
            setattr(args, key, value)
    return args


def _format_credits(balance: dict[str, Any]) -> str:
    sections = [
        ("Monthly allocated", balance.get("monthly_allocated")),
        ("Purchased", balance.get("purchased")),
        ("Total", balance.get("total")),
    ]
    lines = ["FactChat credits"]
    for label, payload in sections:
        if isinstance(payload, dict):
            lines.append(
                f"- {label}: quota {_format_credit_value(payload.get('quota'))}, "
                f"used {_format_credit_value(payload.get('used'))}, "
                f"remaining {_format_credit_value(payload.get('remaining'))}"
            )
            renewal_date = payload.get("renewal_date")
            if renewal_date:
                lines.append(f"  renewal: {renewal_date}")
    return "\n".join(lines)


def _format_credit_value(value: Any) -> str:
    if isinstance(value, int | float):
        return f"{value:g}"
    return "unknown"


if __name__ == "__main__":
    raise SystemExit(main())
