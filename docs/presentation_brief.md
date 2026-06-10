# PaperPilot Presentation Brief

## One-Sentence Pitch

PaperPilot is an agentic literature-curation CLI that turns a research query into a traceable loop of query planning, tool-based paper search, observation, replanning, deduplication, PDF evidence extraction, Korean summary generation, and reflection.

## What To Emphasize

- It solves a concrete research workflow pain point: weekly paper scanning is repetitive, uncertain, and easy to bias with one narrow query.
- It is agentic because observations change later actions: weak search results trigger query expansion, rate limits trigger source skipping, PDF failures trigger abstract fallback, and summary failures trigger heuristic fallback.
- It has repeatable evaluation: `paperpilot eval` compares a baseline pipeline against an agentic policy condition.
- It is cost-aware: default development settings use cheap/heuristic paths, and FactChat `gpt-5.4-nano` is reserved for final wording quality.
- It is honest about limits: every report preserves search attempts, failure analysis, source errors, and evidence scope.

## Recommended Demo Commands

```bash
paperpilot eval --mode fixture --all
```

```bash
paperpilot eval --mode live \
  --scenario dlm_unlearning \
  --sources arxiv,openalex \
  --cost-profile dev
```

```bash
paperpilot curate "diffusion language model unlearning" \
  --sources arxiv,openalex \
  --with-pdf \
  --cost-profile dev \
  --agentic-mode policy \
  --summary-backend heuristic \
  --scholar-links
```

```bash
paperpilot curate "diffusion language model unlearning" \
  --sources arxiv,openalex \
  --with-pdf \
  --cost-profile dev \
  --agentic-mode policy \
  --summary-backend factchat \
  --summary-model gpt-5.4-nano
```

## Slide Mapping

- Slide 1: Problem and user pain point.
- Slide 2: Agentic workflow diagram: plan -> search tool -> observe -> decide -> act -> review -> summarize -> reflect.
- Slide 3: System components and tools.
- Slide 4: Evaluation table from `outputs/evaluations/YYYY-MM-DD_eval.md`.
- Slide 5: Live curation report, starting from `Presentation Highlights`.
- Slide 6: Failure recovery and limitations.

## Strong Demo Sentence

"Baseline은 원문 query와 arXiv만 사용해서 실패할 수 있지만, agentic 조건은 같은 문제를 관찰하고 query를 넓히며 OpenAlex/PDF evidence까지 사용해 후보를 회복합니다."

## Known Limitations To Say Out Loud

- Reviewer scoring is deterministic and lightweight, so final paper judgment still belongs to the researcher.
- External APIs have coverage and rate-limit issues.
- Heuristic summaries are good for cost-free demos but final reports should use FactChat when credits are available.
- Google Scholar is intentionally not scraped; reports provide manual Scholar links instead.
