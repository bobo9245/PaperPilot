# PaperPilot

PaperPilot은 연구자가 입력한 주제를 바탕으로 최신 논문 후보를 수집하고, 검색 실패를 관찰해 query를 재계획하고, 중복 제거와 relevance review를 거친 뒤, PDF 근거 기반 한국어 요약과 평가용 Markdown 보고서를 생성하는 agentic paper curation CLI입니다.

한 줄로 말하면, PaperPilot은 “논문 검색 결과를 한 번 요약하는 도구”가 아니라 “검색-관찰-재계획-검토-근거추출-요약-성찰을 반복 가능한 workflow로 실행하는 작은 연구 보조 agent”입니다.

## Project Motivation

대학원생이나 연구자는 매주 빠르게 변하는 분야의 최신 논문을 훑어야 합니다. 이 과정은 단순히 키워드 하나를 검색하는 일이 아니라, 검색어를 바꾸고, 여러 논문 인덱스를 확인하고, 중복 논문을 제거하고, PDF를 열어 방법과 실험을 확인하고, 어떤 점이 새로운지와 한계가 무엇인지 정리하는 반복 작업입니다.

PaperPilot은 이 반복 작업을 자동화 가능한 agentic workflow로 모델링합니다.

- User: 최신 연구 동향을 빠르게 따라가야 하는 대학원생, 연구자, 프로젝트 팀
- Problem: 좁은 검색어는 좋은 후보를 놓치고, 넓은 검색어는 약한 후보를 많이 섞습니다.
- Pain point: query 조정, multi-source 검색, 중복 제거, PDF skim, novelty/limitation 정리가 반복적이고 시간이 오래 걸립니다.
- Agentic fit: 검색 결과가 약하면 다음 행동을 바꿔야 하므로, one-shot chatbot보다 observe-decide-act-reflect loop가 적합합니다.

## What PaperPilot Does

PaperPilot은 하나의 research query를 받아 다음 산출물을 만듭니다.

- `outputs/YYYY-MM-DD_query.md`: 논문 큐레이션 보고서
- `outputs/evaluations/YYYY-MM-DD_eval.md`: baseline vs agentic 평가 결과
- `paper/main.tex`: 소논문 형식의 LaTeX 원고
- `docs/demo_script.md`: 발표 시연 스크립트
- `docs/presentation_qna.md`: 예상 질문과 답변
- `outputs/.../paperpilot-agentic-curation.pptx`: 발표용 PPTX

보고서에는 다음 정보가 포함됩니다.

- 문제 정의와 agentic fit
- source/query별 search attempts
- query expansion, source skipping, fallback 같은 agent trace
- 중복 제거 결과
- relevance/novelty/experiment reviewer score
- PDF evidence 기반 한국어 5단 요약
- zero-selected 상황의 failure analysis
- Google Scholar 수동 확인 링크

## Agentic Workflow

PaperPilot의 핵심은 검색 결과를 관찰한 뒤 실제 다음 행동을 바꾸는 policy loop입니다.

```text
User Query
  -> QueryPlannerAgent
  -> SearcherAgent + Tools(arXiv, OpenAlex, Semantic Scholar)
  -> Observe search results
  -> CurationPolicyAgent decides recovery action
  -> Dedupe + metadata merge
  -> ReviewerAgent relevance gate
  -> PDF evidence extraction
  -> SummarizerAgent
  -> Reflection / fallback
  -> Markdown report + evaluation metrics
```

정책 agent가 선택할 수 있는 대표 action은 다음과 같습니다.

- `continue`: 현재 후보군으로 진행
- `expand_query`: 다음 query variant 검색
- `try_broad_search`: strict search가 너무 좁을 때 broader pass 시도
- `skip_rate_limited_source`: Semantic Scholar 429 등 source 장애를 기록하고 우회
- `use_abstract_fallback`: PDF가 없거나 추출 실패 시 abstract 기반 요약으로 복구
- `use_heuristic_summary_fallback`: LLM backend 실패 시 deterministic summary로 복구
- `stop_with_failure_analysis`: 약한 후보를 억지로 채우지 않고 실패 원인과 다음 시도 제안 출력

이 trace는 최종 Markdown 보고서의 `Agent Trace` 섹션에 phase별로 기록됩니다.

## Architecture

주요 모듈은 다음과 같습니다.

| Module | Role |
| --- | --- |
| `src/paperpilot/main.py` | CLI entrypoint, cost profile, command parsing |
| `src/paperpilot/workflow.py` | end-to-end curation workflow orchestration |
| `src/paperpilot/agents/query_planner.py` | deterministic query expansion |
| `src/paperpilot/agents/searcher.py` | multi-source search, observation, dedupe |
| `src/paperpilot/agents/policy.py` | observe-decide-act recovery policy |
| `src/paperpilot/agents/reviewer.py` | relevance, novelty, experiment score |
| `src/paperpilot/agents/summarizer.py` | heuristic/OpenAI/FactChat summary backends |
| `src/paperpilot/tools/arxiv.py` | arXiv API client |
| `src/paperpilot/tools/openalex.py` | OpenAlex Works API client |
| `src/paperpilot/tools/semantic_scholar.py` | Semantic Scholar API client |
| `src/paperpilot/tools/pdf.py` | selected-paper PDF evidence extraction |
| `src/paperpilot/publisher.py` | Markdown report rendering |
| `src/paperpilot/evaluation.py` | baseline vs agentic evaluation runner |

## Search Sources

PaperPilot은 자동 수집에 공식 API를 사용합니다.

- `arxiv`: 기본 preprint source, PDF URL 제공
- `openalex`: 논문 metadata, DOI, venue, citation count 보강
- `semantic-scholar`: 논문 search와 citation metadata 보강

Google Scholar는 자동 scraping 대상에서 제외했습니다. 공식적인 자동 수집 API가 없고 blocking 가능성이 높기 때문입니다. 대신 `--scholar-links`를 켜면 보고서에 수동 확인용 Google Scholar 링크를 추가합니다.

여러 source에서 같은 논문이 발견되면 다음 순서로 중복 제거하고 metadata를 병합합니다.

1. DOI
2. arXiv ID
3. normalized title

## Summary Backends

요약 backend는 비용과 품질을 상황에 따라 선택할 수 있습니다.

| Backend | Use case |
| --- | --- |
| `heuristic` | API key 없이 테스트, 발표, fixture 평가 |
| `factchat` | FactChat Gateway 기반 한국어 요약 품질 향상 |
| `openai` | OpenAI API 기반 structured summary |
| `auto` | FactChat key -> OpenAI key -> heuristic fallback 순서로 자동 선택 |

LLM backend에는 raw PDF 전체를 그대로 보내지 않습니다. PaperPilot은 paper metadata, paper kind, section snippets, quantitative clues, limitation clues로 구성된 evidence pack만 보내고, 출력은 구조화된 JSON summary로 받습니다. 이후 reflection check를 통과하지 못하거나 API 호출이 실패하면 paper별 heuristic fallback을 사용합니다.

## Installation

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install -e ".[dev]"
```

설치 확인:

```bash
.venv/bin/python -m pytest
.venv/bin/paperpilot --help
```

## Quickstart

API 비용 없이 built-in sample로 실행:

```bash
.venv/bin/paperpilot curate "retrieval augmented generation" --dry-run
```

기본 arXiv 검색:

```bash
.venv/bin/paperpilot curate "multimodal retrieval augmented generation" \
  --days 7 \
  --max-results 20 \
  --top-k 3 \
  --category cs.CL
```

agentic multi-source 검색:

```bash
.venv/bin/paperpilot curate "diffusion language model unlearning" \
  --sources arxiv,openalex \
  --with-pdf \
  --cost-profile dev \
  --agentic-mode policy \
  --summary-backend heuristic \
  --scholar-links
```

FactChat을 사용하는 저비용 개발 설정:

```bash
export FACTCHAT_API_KEY="..."
export PAPERPILOT_FACTCHAT_MODEL=gpt-5.4-nano

.venv/bin/paperpilot curate "multimodal retrieval augmented generation" \
  --sources arxiv,openalex \
  --with-pdf \
  --cost-profile dev \
  --summary-backend factchat \
  --summary-model gpt-5.4-nano
```

## Recommended Cost Profiles

개발 중에는 모델을 키우기보다 `top-k`, PDF page/char budget, summary detail을 같이 제한하는 것이 비용 절약에 더 중요합니다.

| Profile | Model | Top-k | PDF budget | Detail | Purpose |
| --- | --- | ---: | --- | --- | --- |
| `dev` | `gpt-5.4-nano` | 1 | 8 pages / 24000 chars | `deep` | 평소 개발, 저비용 확인 |
| `balanced` | `gpt-5.4-nano` | 1 | 12 pages / 32000 chars | `ultra` | 품질 점검 |
| `final` | `gpt-5.4-mini` | 3 | 20 pages / 64000 chars | `ultra` | 최종 보고서 생성 |

관련 명령:

```bash
.venv/bin/paperpilot models --provider factchat
.venv/bin/paperpilot credits --provider factchat
```

## Evaluation

PaperPilot은 baseline과 agentic condition을 비교하는 평가 CLI를 제공합니다.

Baseline:

- arXiv only
- query expansion off
- PDF off
- heuristic summary
- agentic mode off

Agentic:

- arXiv + OpenAlex 등 official sources
- query expansion basic
- PDF evidence on
- reflection/fallback on
- agentic mode policy

비용 없는 fixture 평가:

```bash
.venv/bin/paperpilot eval --mode fixture --all
```

single live scenario:

```bash
.venv/bin/paperpilot eval --mode live \
  --scenario dlm_unlearning \
  --sources arxiv,openalex \
  --cost-profile dev
```

현재 fixture 평가 결과 요약:

| Scenario | Baseline selected | Agentic selected | Agentic replans | Agentic deduped | Reflection pass |
| --- | ---: | ---: | ---: | ---: | ---: |
| `multimodal_rag` | 1 | 2 | 5 | 3 | 1.00 |
| `dlm_unlearning` | 0 | 2 | 5 | 7 | 1.00 |
| `agentic_ai_evaluation` | 1 | 2 | 3 | 1 | 1.00 |

현재 live `dlm_unlearning` 평가에서는 baseline이 0개를 선택한 반면 agentic condition은 1개를 선택했습니다. 이 사례는 발표에서 “narrow query 실패를 agentic workflow가 회복하는 장면”으로 사용하기 좋습니다.

## CLI Reference

자주 쓰는 `curate` 옵션:

| Option | Meaning |
| --- | --- |
| `--sources arxiv,openalex` | 사용할 논문 검색 source |
| `--query-expansion off/basic` | deterministic query expansion 사용 여부 |
| `--max-query-variants 6` | 최대 query variant 수 |
| `--agentic-mode off/policy/hybrid` | agentic policy loop 사용 여부 |
| `--max-agent-steps 6` | recovery decision step 제한 |
| `--min-relevance 0.8` | reviewer relevance threshold |
| `--strict-search` | title/abstract 중심 검색 |
| `--broad-search` | 더 넓은 field 검색 |
| `--with-pdf` | selected paper PDF evidence 사용 |
| `--pdf-max-pages 8` | PDF 추출 page 제한 |
| `--pdf-max-chars 24000` | PDF text budget 제한 |
| `--summary-backend heuristic/factchat/openai/auto` | 요약 backend 선택 |
| `--summary-detail standard/deep/ultra` | summary evidence detail 수준 |
| `--cost-profile dev/balanced/final` | 비용-품질 preset |
| `--scholar-links` | Google Scholar 수동 확인 링크 추가 |

예시:

```bash
.venv/bin/paperpilot curate "agentic ai evaluation benchmark" \
  --sources arxiv,openalex \
  --query-expansion basic \
  --with-pdf \
  --cost-profile dev \
  --agentic-mode policy \
  --summary-backend heuristic
```

## Environment Variables

선택적으로 사용할 수 있는 환경 변수:

| Variable | Purpose |
| --- | --- |
| `FACTCHAT_API_KEY` | FactChat Gateway API key |
| `PAPERPILOT_FACTCHAT_API_KEY` | FactChat key alternative name |
| `PAPERPILOT_FACTCHAT_MODEL` | FactChat default model |
| `OPENAI_API_KEY` | OpenAI summary backend key |
| `PAPERPILOT_OPENAI_MODEL` | OpenAI default summary model |
| `SEMANTIC_SCHOLAR_API_KEY` | Semantic Scholar rate limit 개선 |
| `OPENALEX_MAILTO` | OpenAlex polite pool 식별 |

## Presentation Materials

발표 준비용 산출물:

- [docs/demo_script.md](docs/demo_script.md): 7분 시연 흐름
- [docs/presentation_brief.md](docs/presentation_brief.md): 발표 핵심 문장과 slide mapping
- [docs/presentation_speaker_notes.md](docs/presentation_speaker_notes.md): slide별 발표 대본
- [docs/presentation_qna.md](docs/presentation_qna.md): 예상 질문과 답변
- [paper/paper.md](paper/paper.md): 소논문 초안
- [paper/main.tex](paper/main.tex): LaTeX 논문 원고
- [paper/references.bib](paper/references.bib): 참고문헌
- [outputs/evaluations/2026-06-09_eval.md](outputs/evaluations/2026-06-09_eval.md): fixture 평가 결과
- [outputs/2026-06-09_diffusion-language-model-unlearning.md](outputs/2026-06-09_diffusion-language-model-unlearning.md): live-style curation demo report

PPTX는 다음 경로에 있습니다.

```text
outputs/019eaafa-cabd-7140-8589-90aeb1107b60/presentations/paperpilot-final/output/paperpilot-agentic-curation.pptx
```

## Suggested Demo Flow

1. 문제 제기: 논문 탐색은 query tuning, source checking, PDF skim, novelty judgment가 반복되는 작업이라고 설명합니다.
2. `paperpilot eval --mode fixture --all` 결과를 열어 baseline과 agentic 조건을 비교합니다.
3. `dlm_unlearning`에서 baseline이 0개, agentic이 후보를 회복하는 사례를 보여줍니다.
4. curation report의 `Search Attempts`를 보여주며 query/source별 관찰을 설명합니다.
5. `Agent Trace`에서 `expand_query`, `continue`, `fallback` 같은 decision을 보여줍니다.
6. selected paper summary에서 PDF evidence와 reflection pass를 확인합니다.
7. limitation을 솔직히 말합니다: reviewer score는 lightweight이며 최종 판단은 연구자에게 남습니다.

## Testing

현재 테스트는 unit/CLI/workflow/evaluation을 포함합니다.

```bash
.venv/bin/python -m pytest
```

최근 확인 결과:

```text
79 passed
```

## Known Limitations

- Reviewer score는 반복 가능한 비교를 위한 lightweight signal이며, 전문가의 최종 논문 판단을 대체하지 않습니다.
- live search는 외부 API coverage, rate limit, indexing delay의 영향을 받습니다.
- PDF extraction은 PDF 구조와 text layer 품질에 따라 실패할 수 있습니다.
- heuristic summary는 비용 없는 실행에 강하지만, 최종 제출용 자연스러운 문장은 FactChat/OpenAI backend가 더 적합합니다.
- Google Scholar는 자동 scraping하지 않으며, 수동 확인 링크만 제공합니다.

## Future Work

- 더 강한 benchmark dataset과 human annotation 기반 평가
- 논문별 novelty claim verification 강화
- reviewer score calibration과 false positive 분석
- source별 recall/precision 비교
- 웹 UI 또는 lightweight dashboard
- BibTeX export와 Zotero/Notion integration

