# PaperPilot Speaker Notes

## Slide 1. PaperPilot

오늘 발표할 PaperPilot은 논문 요약기가 아니라 논문 큐레이션 agent입니다. 핵심은 검색 결과를 한 번 받아서 끝내는 것이 아니라, 결과가 약하면 검색어를 바꾸고 source를 바꾸며, PDF evidence와 reflection까지 연결하는 workflow입니다.

## Slide 2. Problem

대상 사용자는 최신 연구를 매주 따라가야 하는 대학원생과 연구자입니다. 이 사람들은 검색어 조정, 중복 제거, PDF 읽기, 새로움과 한계 판단을 계속 반복합니다. 검색 품질은 실행 전에는 알 수 없기 때문에 agentic workflow가 자연스럽습니다.

## Slide 3. Agent Loop

여기서 중요한 것은 trace가 단순 로그가 아니라 decision point라는 점입니다. 예를 들어 arXiv가 0개를 반환하면 observe 단계에서 약한 결과를 기록하고, policy가 expand query를 선택하고, act 단계에서 다음 query variant나 source를 시도합니다.

## Slide 4. Implementation

각 agent의 역할을 분리했습니다. QueryPlannerAgent는 deterministic하게 query를 확장하고, SearcherAgent는 external source를 호출합니다. CurationPolicyAgent는 recovery action을 선택하고, ReviewerAgent는 candidate gate 역할을 합니다. SummarizerAgent는 heuristic과 FactChat/OpenAI backend를 지원하지만, API가 없어도 fallback으로 계속 동작합니다.

## Slide 5. Evaluation

fixture 평가는 실제 검색 recall을 측정하기보다 system behavior를 반복 가능하게 보여주는 평가입니다. 가장 중요한 결과는 DLM unlearning입니다. baseline은 0개를 선택했지만 agentic 조건은 query expansion과 multi-source search를 통해 2개를 선택했습니다.

## Slide 6. Live Demo Trace

발표 시 실제 보고서는 Search Attempts, Agent Trace, Selected Paper 순서로 보여주면 됩니다. 좁은 query에서 arXiv는 0개를 반환했고, OpenAlex와 broader query variant가 후보를 회복했습니다. 이 과정에서 8 search attempts, 4 query variants, 11 duplicate merges, 1 selected paper가 기록되었습니다.

## Slide 7. Limitations

이 프로젝트는 expert reviewer를 대체하지 않습니다. Reviewer scoring은 candidate gate입니다. 또한 fixture evaluation은 실제 recall 증명이 아니며, PDF extraction과 external API coverage에도 한계가 있습니다. 대신 이 시스템의 강점은 실패를 숨기지 않고 관찰 가능하게 남긴다는 점입니다.
