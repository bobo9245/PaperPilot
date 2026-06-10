# PaperPilot Demo Script

## Goal

Show PaperPilot as an agentic paper curation system, not a one-shot chatbot. The demo should make the loop visible: plan query variants, use external paper-search tools, observe weak results, replan, deduplicate, review candidates, extract PDF evidence, summarize, and reflect.

## 7-Minute Presentation Flow

1. Problem, 45 seconds
   - "논문 탐색은 검색어 조정, 출처 확인, 중복 제거, PDF 훑기, 새로움 판단이 반복되는 작업입니다."
   - State the user: a graduate student or researcher preparing a weekly literature brief.

2. System idea, 60 seconds
   - PaperPilot is an agentic workflow: observe weak search results, decide the next action, act through tools, then reflect on the output.
   - Do not frame it as "a better summarizer"; frame it as "a recoverable curation pipeline."

3. Architecture, 75 seconds
   - QueryPlannerAgent expands search terms without LLM cost.
   - SearcherAgent uses arXiv/OpenAlex/Semantic Scholar tools and records observations.
   - CurationPolicyAgent chooses recovery actions such as `expand_query`, `try_broad_search`, `skip_rate_limited_source`, and fallback paths.
   - ReviewerAgent filters weak candidates before any expensive summary step.
   - SummarizerAgent writes Korean summaries from bounded evidence and runs reflection.

4. Evaluation, 75 seconds
   - Open `outputs/evaluations/YYYY-MM-DD_eval.md`.
   - Show `Summary Table` first, then `Presentation Takeaways`.
   - The strongest story is a scenario where baseline selects 0 papers and agentic recovers at least 1.

5. Live report demo, 120 seconds
   - Open the curation report.
   - Show `Presentation Highlights`, `Search Attempts`, `Agent Trace`, and one `Selected Papers` summary.
   - Narrate the loop as observation -> decision -> action -> grounded output.

6. Limitation and next step, 45 seconds
   - Reviewer scoring is lightweight and not a substitute for expert judgment.
   - External APIs can rate-limit; the system records and recovers from this but cannot guarantee coverage.
   - Heuristic summaries are safe and cheap, while FactChat summaries are better for final wording.

## Demo Flow

1. Start with the user problem.
   - "A researcher wants a weekly brief on a fast-moving topic, but manual search requires query tuning, source checking, duplicate removal, PDF skimming, and novelty judgment."

2. Run the cost-free evaluation.
   ```bash
   paperpilot eval --mode fixture --all
   ```
   - Open `outputs/evaluations/YYYY-MM-DD_eval.md`.
   - Point to the baseline-vs-agentic table.
   - Explain that fixture mode is repeatable and validates system behavior without API cost.

3. Run the live-style curation demo.
   ```bash
   paperpilot curate "diffusion language model unlearning" \
     --sources arxiv,openalex \
     --with-pdf \
     --cost-profile dev \
     --agentic-mode policy \
     --summary-backend heuristic \
     --scholar-links
   ```
   - Open the generated report.
   - Show `Presentation Highlights`, `Project Alignment`, `Search Attempts`, and `Agent Trace`.
   - Highlight replanning from narrow DLM wording toward broader language-model unlearning terms.
   - Point to policy decisions such as `expand_query`, `try_broad_search`, `use_abstract_fallback`, or `use_heuristic_summary_fallback` when they appear.

4. Optional final-quality run with FactChat.
   ```bash
   paperpilot curate "diffusion language model unlearning" \
     --sources arxiv,openalex \
     --with-pdf \
     --cost-profile dev \
     --agentic-mode policy \
     --summary-backend factchat \
     --summary-model gpt-5.4-nano
   ```
   - Use this only when credits are available.
   - Compare the Korean summary wording with the heuristic report.

## Backup Plan

- If live search is slow or rate-limited, use `paperpilot eval --mode fixture --all` and open the generated fixture reports under `outputs/evaluations/curations/`.
- If FactChat credits are unavailable, use `--summary-backend heuristic`; the report still demonstrates the agent loop, fallback behavior, and evidence tracking.
- If no papers are selected, do not hide it. Open `Failure Analysis` and explain that the system refuses to fill the report with weak matches.

## Failure Case to Explain

- Semantic Scholar can return HTTP 429 without an API key.
- PaperPilot records the source error and continues with other sources or query variants.
- In policy mode, the report records `skip_rate_limited_source` as an explicit recovery decision.
- This is a useful demo point because the system shows recovery behavior instead of hiding the failure.

## Closing Points

- The system is repeatable: same scenarios can be evaluated again.
- The report connects problem, system behavior, output, and limitations.
- The main limitation is that reviewer scoring is lightweight and still requires human judgment for final paper selection.
