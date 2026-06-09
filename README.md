# PaperPilot

PaperPilot is a small agentic workflow that curates recent arXiv papers for a research query. It searches, replans if results are weak, scores candidate papers, writes Korean five-part summaries from bounded evidence, and publishes a Markdown brief.

## Agentic Fit

Paper discovery is a good fit for a lightweight agent loop because search quality is often uncertain. PaperPilot records each search attempt, broadens the query when results are too thin or an arXiv request fails, and then uses a reviewer pass before writing summaries.

## Architecture

- `ArxivSearchClient`: fetches and normalizes recent arXiv Atom results.
- `SearcherAgent`: searches, logs observations, and replans up to two broader queries.
- `ReviewerAgent`: scores relevance, novelty, and experimental strength.
- `SummarizerAgent`: produces Korean five-part summaries with either OpenAI structured summaries or an offline heuristic fallback, then applies a reflection check.
- `MarkdownPublisher`: saves a dated Markdown curation report.
- `CurationWorkflow`: connects search, review, summary, reflection, and publishing.

## Quickstart

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install -e ".[dev]"
python -m pytest
```

Run a no-network demo:

```bash
paperpilot curate "retrieval augmented generation" --dry-run
```

Run against arXiv:

```bash
paperpilot curate "multimodal retrieval augmented generation" --days 7 --max-results 20 --top-k 3 --category cs.CL
```

Use selected-paper PDFs to strengthen summaries:

```bash
paperpilot curate "multimodal retrieval augmented generation" --category cs.CL --with-pdf --pdf-max-pages 8 --pdf-max-chars 32000
```

Use OpenAI-backed summaries when an API key is available:

```bash
export OPENAI_API_KEY="..."
paperpilot curate "multimodal retrieval augmented generation" --with-pdf --summary-backend auto --summary-detail deep
```

Use FactChat Gateway-backed summaries:

```bash
export FACTCHAT_API_KEY="..."
paperpilot models --provider factchat
paperpilot curate "multimodal retrieval augmented generation" --with-pdf --pdf-max-pages 20 --pdf-max-chars 64000 --summary-backend factchat --summary-detail ultra
```

Force the offline summarizer:

```bash
paperpilot curate "multimodal retrieval augmented generation" --summary-backend heuristic
```

Reports are written to `outputs/YYYY-MM-DD_query.md` by default.

Useful controls:

- `--min-relevance 0.8`: require a minimum reviewer relevance score before a paper can be selected.
- `--category cs.CL`: restrict arXiv results to one category; repeat it or pass comma-separated values for several categories.
- `--strict-search`: search title/abstract using phrase and AND constraints. This is the default.
- `--broad-search`: search all arXiv fields using AND constraints when strict search is too narrow.
- `--with-pdf`: download selected PDFs and use extracted text for method, experiment, and limitation evidence.
- `--pdf-max-pages 8`: limit how many pages are extracted from each selected PDF.
- `--pdf-max-chars 64000`: keep a larger extracted PDF text budget so later experiment, discussion, and limitation sections are not clipped before summarization.
- `--summary-backend auto`: choose `auto`, `factchat`, `openai`, or `heuristic`. `auto` uses FactChat when `FACTCHAT_API_KEY` or `PAPERPILOT_FACTCHAT_API_KEY` is set, then OpenAI when `OPENAI_API_KEY` is set, and falls back to the heuristic summarizer if no key is available or the request fails.
- `--summary-model MODEL`: choose the LLM model for summaries. FactChat defaults to `PAPERPILOT_FACTCHAT_MODEL` or `auto`, which lists Gateway models and chooses an accessible chat model; OpenAI defaults to `PAPERPILOT_OPENAI_MODEL` or `gpt-5.2`.
- `--summary-detail ultra`: send a novelty-focused evidence pack to the summary backend. Choose `standard`, `deep`, or `ultra`.
- `paperpilot models --provider factchat`: list the model IDs enabled for your FactChat tenant.

If no candidate passes the relevance threshold, PaperPilot writes a report with zero selected papers instead of filling the list with weak matches.

## Summary Backends

The default `auto` backend keeps the project runnable offline while allowing higher-quality LLM summaries when configured. It prefers FactChat Gateway when a FactChat key is present, then OpenAI. It sends only a compact evidence pack to the LLM: paper metadata, paper kind, novelty clues, section snippets, and quantitative clues. The LLM must return a structured JSON object with problem, novelty, contributions, method or benchmark design, experiments, limitations, evidence notes, and confidence.

Markdown reports keep Korean summaries separate from short source snippets. If the LLM provider call fails, the JSON response is invalid, or the API key is unavailable, PaperPilot falls back to the deterministic heuristic backend and records the fallback reason in the report metadata.

## MVP Scope

The MVP keeps search, review, relevance gating, evidence extraction, reflection, and publishing deterministic. LLM usage is limited to summary wording quality, with an offline heuristic path preserved for tests, demos, and environments without an API key.
