# PaperPilot Workshop Paper Outline

Full Korean draft: [paper.md](paper.md)

ACM-style LaTeX draft: [main.tex](main.tex)

## Abstract

PaperPilot is an agentic paper curation workflow for researchers who repeatedly scan fast-moving topics. It combines query planning, multi-source search, result observation, replanning, duplicate merging, reviewer scoring, PDF evidence extraction, Korean summary generation, and reflection/fallback. The system is evaluated with repeatable baseline-vs-agentic scenarios and live curation reports.

## Introduction

- Problem: manual paper discovery is repetitive and uncertain.
- User: graduate students and researchers tracking weekly literature.
- Pain point: query reformulation, source checking, duplicate removal, PDF reading, novelty extraction, and limitation tracking take time.
- Agentic fit: search quality is only known after observing tool results, so the system needs planning, action, observation, and replanning.

## System Design

- QueryPlannerAgent expands the user query deterministically.
- SearcherAgent calls arXiv/OpenAlex/Semantic Scholar tools and records observations.
- CurationPolicyAgent turns observations into recovery actions such as query expansion, broad-search retry, source skipping, abstract fallback, and heuristic summary fallback.
- ReviewerAgent scores candidates by relevance, novelty, and experimental strength.
- PdfEvidenceExtractor reads bounded selected-paper PDF evidence.
- SummarizerAgent writes Korean structured summaries with heuristic, OpenAI, or FactChat backends.
- MarkdownPublisher exposes Search Attempts, Agent Trace, selected papers, evidence, scores, and limitations.

## Implementation

- CLI entrypoints: `curate`, `models`, `credits`, and `eval`.
- Agentic modes: `off` for baseline, `policy` for deterministic observe-decide-act recovery, and `hybrid` for guarded advisor behavior.
- Default development path is cost-safe: fixture evaluation and heuristic summaries.
- FactChat is optional for final wording quality, with `gpt-5.4-nano` as the low-cost development model.
- Multi-source metadata is deduplicated by DOI, arXiv ID, and normalized title.

## Results and Evaluation

- Use `paperpilot eval --mode fixture --all` to generate the main result table.
- Compare baseline and agentic settings on:
  - selected_count
  - search_attempts
  - replans
  - deduped_count
  - pdf_success_rate
  - avg_relevance
  - summary_reflection_pass_rate
  - runtime_seconds
  - fallback_count
- For live demonstration, run one scenario such as `dlm_unlearning` with arXiv and OpenAlex.
- Report qualitative recovery examples from Agent Trace: `expand_query`, `try_broad_search`, `skip_rate_limited_source`, `use_abstract_fallback`, and `use_heuristic_summary_fallback`.

## Limitation

- Reviewer scoring is deterministic and lightweight, so expert judgment is still needed.
- External APIs can rate-limit or change results.
- PDF extraction can miss tables, equations, or scanned text.
- LLM summaries improve readability but require evidence validation and cost control.
