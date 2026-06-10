# PaperPilot Q&A Prep

## 1. 이게 단순 논문 요약기와 무엇이 다른가?

PaperPilot의 핵심은 최종 요약 문장이 아니라 검색 실패를 관찰하고 다음 행동을 바꾸는 workflow입니다. 검색 결과 수, source 오류, PDF 추출 성공 여부, summary reflection 결과를 관찰하고, `expand_query`, `skip_rate_limited_source`, `use_abstract_fallback`, `use_heuristic_summary_fallback` 같은 action을 선택합니다. 그래서 보고서에는 최종 결과뿐 아니라 Search Attempts와 Agent Trace가 남습니다.

## 2. 왜 LLM agent가 아니라 deterministic policy agent인가?

개발과 평가에서는 비용과 재현성이 중요했습니다. Query expansion, source recovery, fallback은 deterministic policy로도 충분히 관찰 가능한 행동 변화를 만들 수 있습니다. LLM은 summary wording을 개선하는 선택적 backend로 제한했고, `hybrid` 모드에서는 guardrail 안에서만 advisor로 붙일 수 있게 했습니다.

## 3. Reviewer score를 믿을 수 있는가?

ReviewerAgent는 전문가 판단을 대체하지 않습니다. 목적은 최종 논문 판정이 아니라 약한 후보를 요약 단계로 넘기지 않는 lightweight gate입니다. 그래서 relevance, novelty, experimental strength를 단순하고 반복 가능한 기준으로 계산하고, 최종 판단은 사용자가 report evidence를 보고 내리도록 설계했습니다.

## 4. fixture 평가가 실제 성능을 증명하는가?

fixture 평가는 실제 검색 recall을 증명하지 않습니다. 대신 같은 조건에서 baseline과 agentic workflow의 behavior 차이를 반복 가능하게 보여줍니다. 실제 API 환경은 live evaluation과 curation report로 보완했습니다. 특히 `dlm_unlearning` live case에서는 baseline이 0개를 선택했지만 agentic 조건은 1개를 선택했습니다.

## 5. live 결과가 압도적인 성능 향상은 아닌데 괜찮은가?

네. 이 프로젝트의 주장은 "항상 더 많은 논문을 찾는다"가 아니라 "검색 실패, source 차이, PDF grounding, fallback을 관찰 가능하게 처리한다"입니다. 일부 query에서는 baseline도 충분히 잘 동작합니다. 하지만 DLM unlearning처럼 좁은 query에서는 agentic condition이 후보 회복을 보여줍니다.

## 6. Semantic Scholar 429 같은 실패는 어떻게 처리하는가?

source별 error를 전체 실패로 처리하지 않고 SearchAttempt와 Agent Trace에 남깁니다. rate limit이면 `skip_rate_limited_source` decision을 기록하고 다른 source나 query variant를 계속 시도합니다. 데모에서는 실패를 숨기지 않고 recovery evidence로 보여주는 것이 포인트입니다.

## 7. PDF evidence가 틀리거나 noisy하면 어떻게 하나?

현재 PDF extractor는 page/character budget 안에서 text evidence를 추출하기 때문에 표, 수식, 스캔 문서, 다단 레이아웃에 약할 수 있습니다. 그래서 summary에는 evidence scope와 caveat를 남기고, reflection에서 실험/결과/한계가 확인되지 않으면 확인 필요를 표시합니다.

## 8. FactChat이 없으면 프로젝트가 약해지는가?

아닙니다. FactChat은 최종 한국어 summary wording을 개선하는 선택 기능입니다. 핵심 agentic workflow는 query planning, tool use, observation, replanning, reviewer gate, PDF evidence, reflection/fallback입니다. API key가 없으면 heuristic fallback으로 report generation을 유지합니다.

## 9. Google Scholar는 왜 자동 수집하지 않았나?

Google Scholar는 안정적인 공식 자동 수집 API가 없고 scraping은 차단/정책 문제가 생길 수 있습니다. 따라서 자동 수집은 arXiv, OpenAlex, Semantic Scholar 같은 공식 API로 제한하고, Google Scholar는 수동 확인 링크만 제공합니다.

## 10. 다음 개선은 무엇인가?

첫째, reviewer scoring을 더 정교화하고 human evaluation과 비교해야 합니다. 둘째, live evaluation scenario를 더 늘려 source coverage와 recall을 검증해야 합니다. 셋째, PDF table/equation extraction을 개선해야 합니다. 넷째, FactChat/OpenAI summary validation을 더 엄격히 만들어 근거 없는 claim을 줄여야 합니다.

## Closing Answer

"PaperPilot은 논문을 대신 읽어주는 챗봇이 아니라, 논문 탐색 과정에서 생기는 실패와 근거 제한을 추적하고 회복하는 agentic workflow입니다. 그래서 결과보다 중요한 산출물은 Search Attempts, Agent Trace, Failure Analysis입니다."
