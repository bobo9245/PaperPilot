# README for PPT: PaperPilot 발표 제작 가이드

이 문서는 PaperPilot 프로젝트를 직접 PPT로 만들 때 필요한 발표 흐름, 슬라이드별 핵심 문구, 넣을 표/그림/스크린샷, 데모 명령어를 한 번에 보기 위한 자료입니다.

## 발표 한 줄 요약

PaperPilot은 연구자가 입력한 논문 주제를 바탕으로 여러 논문 검색 source를 사용하고, 검색 결과를 관찰해 query를 재계획하며, 중복 제거, relevance review, PDF evidence extraction, 한국어 요약, reflection/fallback까지 수행하는 agentic paper curation system입니다.

더 짧게 말하면:

> PaperPilot은 논문 검색 결과를 단순 요약하는 도구가 아니라, 실패를 관찰하고 다음 행동을 바꾸는 논문 큐레이션 agent입니다.

## 발표 핵심 메시지

PPT 전체에서 계속 밀고 갈 메시지는 세 가지입니다.

1. 논문 탐색은 단순 검색이 아니라 반복적인 의사결정 문제다.
2. PaperPilot은 observe -> decide -> act -> reflect 구조로 이 과정을 자동화한다.
3. baseline이 실패하는 좁은 query에서도 agentic workflow는 query expansion, multi-source search, fallback으로 회복을 시도한다.

## 추천 발표 구성

7분 발표 기준으로 8장 정도가 적당합니다.

| Slide | Title | 핵심 역할 |
| --- | --- | --- |
| 1 | PaperPilot | 프로젝트 이름, 한 줄 소개 |
| 2 | Problem | 논문 탐색 pain point 설명 |
| 3 | Why Agentic? | one-shot chatbot이 아니라 agent loop가 필요한 이유 |
| 4 | System Workflow | 전체 workflow 다이어그램 |
| 5 | Implementation | 구현 모듈과 사용 tool/API |
| 6 | Demo Report | 실제 report의 Search Attempts, Agent Trace 보여주기 |
| 7 | Evaluation | baseline vs agentic 결과 표 |
| 8 | Limitations & Future Work | 한계와 개선 방향 |

시간이 부족하면 6장으로 줄일 수 있습니다.

| Slide | Title |
| --- | --- |
| 1 | PaperPilot |
| 2 | Problem & Agentic Fit |
| 3 | Workflow |
| 4 | Demo Trace |
| 5 | Evaluation |
| 6 | Limitations |

## Slide 1. Title

추천 제목:

```text
PaperPilot
Agentic Paper Curation Workflow
```

추천 부제:

```text
검색 실패를 관찰하고 query를 재계획하는 논문 큐레이션 agent
```

발표 멘트:

```text
PaperPilot은 연구자가 입력한 주제에 대해 최신 논문 후보를 찾고, 검색 결과가 약하면 query와 source를 바꾸며, PDF 근거를 바탕으로 한국어 요약 보고서를 생성하는 agentic workflow입니다.
```

넣으면 좋은 시각 요소:

- 검색창 아이콘
- 논문/PDF 아이콘
- agent loop 아이콘
- Markdown report 아이콘

## Slide 2. Problem

슬라이드 핵심 문구:

```text
최신 논문 탐색은 반복적이고 불확실한 작업이다.
```

넣을 bullet:

- 검색어가 좁으면 관련 논문을 놓친다.
- 검색어가 넓으면 약한 후보가 너무 많이 섞인다.
- 같은 논문이 여러 source에 중복으로 나온다.
- 초록만 보면 방법, 실험, 한계를 충분히 파악하기 어렵다.
- 매주 반복되는 작업이라 시간 비용이 크다.

발표 멘트:

```text
논문 탐색은 단순히 키워드를 한 번 검색하는 일이 아닙니다. 검색어를 바꾸고, arXiv나 OpenAlex 같은 source를 오가고, 중복을 제거하고, PDF를 열어 방법과 실험을 확인해야 합니다. 그래서 이 문제는 고정된 한 번의 답변보다 관찰 후 행동을 바꾸는 workflow가 더 잘 맞습니다.
```

## Slide 3. Why Agentic?

슬라이드 핵심 문구:

```text
검색 결과가 약하면 다음 행동이 바뀌어야 한다.
```

표로 넣기 좋은 내용:

| Observation | Decision | Action |
| --- | --- | --- |
| 결과가 0개 또는 너무 적음 | query를 넓힌다 | `expand_query` |
| strict search가 너무 좁음 | broader pass 시도 | `try_broad_search` |
| source가 rate limit | source를 우회 | `skip_rate_limited_source` |
| PDF 추출 실패 | abstract 사용 | `use_abstract_fallback` |
| LLM 요약 실패 | heuristic summary 사용 | `use_heuristic_summary_fallback` |

발표 멘트:

```text
PaperPilot에서 agentic함은 trace를 많이 찍는 것이 아니라, 관찰 결과에 따라 실제 다음 행동이 바뀐다는 점입니다. 예를 들어 Semantic Scholar가 rate limit을 내면 전체 workflow를 멈추지 않고 다른 source로 넘어가고, PDF가 없으면 abstract fallback을 사용합니다.
```

## Slide 4. System Workflow

PPT에 넣을 workflow:

```text
User Query
  -> QueryPlannerAgent
  -> SearcherAgent + Paper APIs
  -> Observe Results
  -> CurationPolicyAgent
  -> Dedupe + Metadata Merge
  -> ReviewerAgent
  -> PDF Evidence Extraction
  -> SummarizerAgent
  -> Reflection / Fallback
  -> Markdown Report
```

권장 시각화:

- 가로 흐름도 또는 원형 loop
- `Observe -> Decide -> Act -> Reflect`는 색을 다르게 강조
- 외부 tool은 arXiv, OpenAlex, Semantic Scholar로 따로 표시

각 agent 역할:

| Agent/Tool | 역할 |
| --- | --- |
| `QueryPlannerAgent` | 입력 query를 여러 검색 variant로 확장 |
| `SearcherAgent` | arXiv/OpenAlex/Semantic Scholar 검색 |
| `CurationPolicyAgent` | 검색 실패, rate limit, PDF 실패를 보고 recovery action 선택 |
| `ReviewerAgent` | relevance, novelty, experiment score 계산 |
| `PdfEvidenceExtractor` | selected paper PDF에서 근거 text 추출 |
| `SummarizerAgent` | 한국어 5단 요약 생성, LLM 실패 시 fallback |
| `MarkdownPublisher` | report 저장 |

## Slide 5. Implementation

슬라이드 핵심 문구:

```text
CLI + Markdown report 중심으로 구현한 재현 가능한 agentic system
```

넣을 내용:

- Language: Python
- Interface: CLI
- Output: Markdown report, evaluation report, paper draft
- Search APIs: arXiv, OpenAlex, Semantic Scholar
- Optional LLM backend: FactChat Gateway, OpenAI
- Offline fallback: heuristic summary
- Tests: `79 passed`

모듈 표:

| File | Description |
| --- | --- |
| `src/paperpilot/main.py` | CLI command parsing |
| `src/paperpilot/workflow.py` | 전체 workflow orchestration |
| `src/paperpilot/agents/searcher.py` | multi-source search와 dedupe |
| `src/paperpilot/agents/policy.py` | agentic recovery policy |
| `src/paperpilot/agents/summarizer.py` | heuristic/LLM summary backend |
| `src/paperpilot/evaluation.py` | baseline vs agentic evaluation |

발표 멘트:

```text
구현은 웹 UI보다 CLI와 Markdown 산출물에 집중했습니다. 과제의 핵심이 agentic workflow와 평가이기 때문에, 실행 결과가 파일로 남고 다시 재현 가능한 구조를 우선했습니다.
```

## Slide 6. Demo Report

보여줄 파일:

```text
outputs/2026-06-09_diffusion-language-model-unlearning.md
```

PPT에 캡처하면 좋은 섹션:

1. `Presentation Highlights`
2. `Search Attempts`
3. `Agent Trace`
4. `Selected Papers`
5. `Summary Reflection`

강조할 실제 demo story:

```text
diffusion language model unlearning query에서 arXiv는 처음에 후보를 찾지 못했지만,
OpenAlex와 query expansion을 통해 language model unlearning 관련 후보를 회복했다.
```

보고서에서 보여줄 수 있는 수치:

- Unique candidates: 20
- Duplicates merged: 11
- Selected papers: 1
- Search attempts: 8
- Query variants: 4
- PDF evidence: 1/1
- Summary reflection: 1/1 passed

발표 멘트:

```text
여기서 중요한 점은 결과만 보여주는 것이 아니라, 어떤 source에 어떤 query를 던졌고, 어디서 실패했고, 그 실패를 보고 어떤 다음 행동을 선택했는지가 report에 남는다는 것입니다.
```

## Slide 7. Evaluation

보여줄 파일:

```text
outputs/evaluations/2026-06-09_eval.md
```

PPT에 넣을 fixture 평가 표:

| Scenario | Baseline selected | Agentic selected | Agentic replans | Deduped |
| --- | ---: | ---: | ---: | ---: |
| multimodal RAG | 1 | 2 | 5 | 3 |
| DLM unlearning | 0 | 2 | 5 | 7 |
| agentic AI evaluation | 1 | 2 | 3 | 1 |

가장 강한 설명 포인트:

```text
DLM unlearning scenario에서 baseline은 0개를 선택했지만, agentic condition은 query expansion과 multi-source search로 2개를 선택했다.
```

live evaluation으로 말할 수 있는 내용:

```text
live dlm_unlearning 평가에서도 baseline은 0개, agentic은 1개를 선택했다.
```

주의해서 말할 점:

```text
fixture 평가는 실제 검색 성능을 증명하는 benchmark가 아니라, agentic behavior가 재현 가능하게 동작하는지 확인하는 평가입니다.
```

발표 멘트:

```text
평가는 baseline과 agentic 조건을 분리했습니다. baseline은 arXiv만 사용하고 query expansion과 PDF를 끕니다. agentic 조건은 query expansion, multi-source search, PDF evidence, reflection/fallback을 켭니다. 여기서 중요한 결과는 agentic 조건이 더 많은 trace와 recovery action을 통해 baseline 실패 사례를 회복했다는 점입니다.
```

## Slide 8. Limitations & Future Work

슬라이드 핵심 문구:

```text
PaperPilot은 완전 자동 연구자가 아니라, traceable curation assistant이다.
```

Limitations:

- reviewer score는 lightweight heuristic이므로 전문가 판단을 대체하지 않는다.
- live search는 외부 API coverage와 rate limit의 영향을 받는다.
- PDF extraction은 PDF text layer 품질에 따라 실패할 수 있다.
- heuristic summary는 안전하고 싸지만, 최종 자연어 품질은 LLM backend가 더 좋다.
- Google Scholar는 자동 scraping하지 않고 수동 링크만 제공한다.

Future work:

- human annotation 기반 평가 dataset 구축
- novelty claim verification 강화
- reviewer score calibration
- source별 recall/precision 비교
- BibTeX/Zotero/Notion export
- 웹 dashboard 추가

마무리 멘트:

```text
결론적으로 PaperPilot은 논문 탐색의 반복적인 의사결정을 agentic workflow로 구조화하고, 실패와 fallback을 숨기지 않고 report에 남기는 시스템입니다.
```

## 데모 명령어

비용 없는 fixture 평가:

```bash
.venv/bin/paperpilot eval --mode fixture --all
```

발표용 live-style curation:

```bash
.venv/bin/paperpilot curate "diffusion language model unlearning" \
  --sources arxiv,openalex \
  --with-pdf \
  --cost-profile dev \
  --agentic-mode policy \
  --summary-backend heuristic \
  --scholar-links
```

FactChat 사용 가능할 때:

```bash
export FACTCHAT_API_KEY="..."

.venv/bin/paperpilot curate "diffusion language model unlearning" \
  --sources arxiv,openalex \
  --with-pdf \
  --cost-profile dev \
  --agentic-mode policy \
  --summary-backend factchat \
  --summary-model gpt-5.4-nano
```

테스트:

```bash
.venv/bin/python -m pytest
```

## PPT에 넣기 좋은 캡처 위치

| 목적 | 파일 |
| --- | --- |
| 전체 프로젝트 설명 | `README.md` |
| fixture 평가 표 | `outputs/evaluations/2026-06-09_eval.md` |
| live DLM demo report | `outputs/2026-06-09_diffusion-language-model-unlearning.md` |
| live multimodal RAG eval | `outputs/evaluations/live_multimodal_rag/2026-06-09_eval.md` |
| 소논문 원고 | `paper/main.tex` |
| 발표 대본 | `docs/presentation_speaker_notes.md` |
| 예상 Q&A | `docs/presentation_qna.md` |

## 발표 디자인 팁

- 색상은 2-3개만 사용합니다.
- `Observe`, `Decide`, `Act`, `Reflect` 네 단어를 반복적으로 강조합니다.
- 평가 표는 숫자를 모두 넣기보다 baseline vs agentic 차이가 보이는 열만 남깁니다.
- 코드 구조는 너무 깊게 설명하지 말고 agent 역할 중심으로 설명합니다.
- 실패 사례를 숨기지 말고 “실패를 report에 남기고 recovery를 시도한다”는 점을 강점으로 말합니다.

## 예상 질문 대비

Q. 이게 그냥 검색 + 요약 아닌가?

A. PaperPilot은 검색 결과를 보고 다음 행동을 바꿉니다. 결과 부족 시 query expansion, source rate limit 시 skip, PDF 실패 시 abstract fallback, LLM 실패 시 heuristic fallback을 수행하고 이 decision을 trace로 남깁니다.

Q. LLM이 핵심인가?

A. 아닙니다. LLM은 요약 문장 품질 향상에만 선택적으로 사용합니다. 검색, query expansion, relevance gate, dedupe, evaluation은 deterministic하게 동작합니다.

Q. Google Scholar는 왜 안 쓰나?

A. 공식 자동 수집 API가 없고 scraping 안정성이 낮아서 자동 수집 대상에서 제외했습니다. 대신 보고서에 수동 확인 링크를 제공합니다.

Q. 평가가 충분한가?

A. 현재 평가는 시스템 behavior를 보여주는 small-scale evaluation입니다. fixture mode로 반복 가능성을 확보했고, live mode로 실제 API 환경에서 회복 사례를 확인했습니다. 다만 human-labeled benchmark는 future work입니다.

Q. 가장 중요한 contribution은?

A. 논문 큐레이션을 traceable agentic workflow로 구조화한 점입니다. 특히 검색 실패와 fallback을 숨기지 않고 report와 evaluation에 남깁니다.

