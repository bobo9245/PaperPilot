# PaperPilot Curation: Machine Unlearning in Masked Diffusion Language Models

- Generated: 2026-06-10T05:07:05.624961+00:00
- Selected papers: 2
- Min relevance: 0.850
- Categories: Any
- Search mode: strict title/abstract
- Agentic mode: policy, max steps 8
- Unique candidates: 98
- Duplicates merged: 47
- PDF evidence: Enabled, max pages 20, max chars 64000
- Summary backend: factchat, detail ultra, model gpt-5.4-nano
- Evaluater backend : factchat, model gpt-5.4-nano

## Selected Papers

## 1. Machine Unlearning for Masked Diffusion Language Models

- Authors: Georu Lee, Seungwon Jeong, Hoki Kim, Jinseong Park, Woojin Lee
- Published: 2026-05-18
- URL: https://arxiv.org/abs/2605.18253v1
- PDF: https://arxiv.org/pdf/2605.18253v1
- Source: arxiv, openalex
- DOI: 10.48550/arxiv.2605.18253
- Venue: arXiv (Cornell University)
- Citations: 0
- Google Scholar: https://scholar.google.com/scholar?q=Machine+Unlearning+for+Masked+Diffusion+Language+Models
- Evidence: PDF text, pages 20/20
- Reviewer score: 0.888 (relevance 1.000, novelty 1.000, experiments 0.440)
- Selection reason: query terms are strongly represented; contains novelty or recent-contribution signals; experimental evidence looks limited from the abstract

### 1. 왜 중요한가

한 줄 요약: 마스킹 확산 언어모델(MDLM)에서 잊어야 할 지식에만 영향을 주도록, 조건부 예측과 무조건부 앵커 사이의 KL 발산을 마스킹된 응답 위치마다 최소화하는 ‘Masked Diffusion Unlearning(MDU)’을 제안한다.

문제: - MDLM은 자동회귀 모델과 달리, 프롬프트를 조건으로 두고 마스킹된 위치를 반복적 노이즈 제거(복수 위치 병렬) 방식으로 복원한다. - 그럼에도 불구하고 MDLM에 맞춘 기계적 언러닝(unlearning) 목적함수는 아직 정리되지 않았고, 특히 ‘다음 토큰 예측’ 중심의 자동회귀 관점에서 벗어난 설계가 필요하다(제공된 근거: “machine unlearning for MDLMs remains largely unexplored”). - 일반적인 언러닝의 목표는 잊기 집합(forget set) 쌍에 대해, 해당 모델이 잊어야 할 응답에 높은 확률을 더 이상 주지 않게 만드는 것이다(제공된 근거: “successful unlearning requires that pθ(· |xf, yt) no longer assigns high probability to… yf”). - 다만 기존 방식이 항상 “완전히 잊기”만 달성하는 것은 아니며, 때로는 잊어야 하는 정보뿐 아니라 필요 정보를 덜 잊는 under-forgetting 현상도 언급된다(제공된 근거: “it sometimes under-forgets information that needs to be forgotten.”). - 따라서 MDLM의 학습/생성 과정(확산에서의 궤적 변화)을 고려해, 잊기 목표를 그 메커니즘에 직접 대응시키는 목적 설계가 요구된다.

주요 근거:
- `This left-toright factorization requires tokens to be generated one after another, with each prediction depending only on the preceding context.`
- `However, machine unlearning for MDLMs remains largely unexplored, leaving open how to design unlearning objectives for masked denoising states rather than sequential next-token prediction.`
- `However, unlike decoding and safety, machine unlearning has not yet been formulated for MDLMs.`
신뢰도: medium
### 2. 핵심 기여

새로움/차별점:
- - ‘MDLM용 언러닝’ 목적함수를 최초로 제시: 제공된 근거에서 저자들은 “MDU, the first unlearning framework for MDLMs”와 “first unlearning objective designed for MDLMs”를 명시한다. 즉, 자동회귀 LLM용 언러닝을 그대로 가져오는 것이 아니라 MDLM의 생성 구조에 맞춰 새 목표를 구성한다는 점이 새롭다. - 확산 모델의 ‘학습=궤적 유도’ 관점을 언러닝에 적용: 제공된 근거에서 지식 학습을 패턴 매칭이 아니라 기준 궤적(reference trajectory)에서 새로운 궤적 pθ(· |x, yt)를 유도하는 최적화로 해석하고, 언러닝도 그 ‘궤적 변화’ 관점에서 재정의한다. 이는 단순한 로짓/확률 조정이 아니라 생성 과정 전체를 관통하는 아이디어로 읽힌다. - 마스킹된 응답 위치마다 조건부-무조건부의 KL 발산을 최소화: 제공된 근거에 따르면 MDU는 매 마스크된 응답 위치마다 “prompt-conditional prediction”과 “prompt-masked unconditional anchor” 사이의 KL divergence를 최소화한다. 즉, MDLM의 병렬 마스킹 복원 메커니즘에 직접 대응해 위치별로 언러닝 신호를 준다는 점이 차별점이다. - 온도 스케일링으로 ‘프라이버시-유틸리티’ 트레이드오프를 조절: 제공된 근거에서 온도 스케일링 파라미터가 privacy-utility trade-off을 제어한다고 밝힌다. 이는 잊기 강도와 성능 보존 사이 균형을 단일 방식으로 고정하지 않고, 조절 가능한 설계 요소로 둔다는 점에서 중요하다. - 표준 언어모델과 다른 생성/학습 경로를 전제로 설계: 제공된 근거는 자동회귀 모델은 순차 생성이지만, MDLM은 마스킹 위치를 병렬로 반복 복원한다고 구분한다. MDU는 이 차이를 인지한 상태에서 언러닝을 구성하므로, 자동회귀 중심 기존 접근과의 직접적인 정렬이 아니라 ‘생성 경로 차이’에 근거한 새 접근으로 볼 수 있다. - 표준 CFG(조건부-무조건부 결합)와의 비교 맥락: 제공된 근거에 “Unlike standard CFG…”가 등장해, 제안식이 단순히 CFG처럼 조건/무조건 예측을 결합해 신호를 증폭하는 방식이 아님을 암시한다. 따라서 기존의 잘 알려진 결합 전략을 그대로 재사용하지 않는 점이 새로움으로 연결될 수 있다(다만 구체 비교 수식 해석은 제공된 발췌 수준에서 한계가 있다).

주요 기여:
- - MDLM을 위한 첫 언러닝 목적/프레임워크로서 Masked Diffusion Unlearning(MDU) 제안(제공된 근거: “first unlearning framework/objective for MDLMs”). - 잊기 목표를 확산의 ‘조건부 예측’과 ‘마스킹된 무조건부 앵커’ 사이의 KL 최소화로 정식화(제공된 근거: “minimizes the KL divergence… at every masked response position”). - 온도 스케일링 파라미터를 통해 언러닝 강도와 성능(유틸리티) 사이의 균형을 조절하는 설계 포함(제공된 근거: “temperature scaling parameter to control the privacy-utility trade-off”). - 두 가지 백본(MDLM 계열)에서 표준 벤치마크로 실험 수행하며, 기존 LLM 언러닝 방법들과의 비교를 통해 효과를 보고(제공된 근거: “empirical results… compared to existing LLM unlearning methods”). - 공개 코드 제공(제공된 근거: “Code is available at …”).

주요 근거:
- `Therefore, we propose Masked Diffusion Unlearning (MDU), the first unlearning objective designed for MDLMs.`
- `However, unlike decoding and safety, machine unlearning has not yet been formulated for MDLMs.`
- `Unlike autoregressive LLMs, diffusion models acquire such information by shifting their denoising trajectory away from a reference trajectory.`
### 3. 방법

방법:
- - 모델 계열: 마스킹 확산 언어모델(MDLM)에서, 프롬프트와 마스킹 상태를 조건으로 특정 응답 위치를 복원하는 메커니즘을 언러닝에 활용한다(제공된 근거: MDLM 설명 및 MDU 정식화). - 언러닝 목표: 매 마스킹된 응답 위치마다 조건부 예측 분포와(프롬프트 조건 하) 마스킹된 무조건부 앵커 분포 사이의 KL 발산을 최소화한다(제공된 근거: “between the conditional answer and the unconditional anchor… at every masked response position”). - 온도(temperature) 스케일링: 목표의 분포 비교에 온도 스케일링을 포함하여 프라이버시-유틸리티 트레이드오프를 조절한다(제공된 근거: “temperature scaling parameter”). - 포지션(위치) 기반 적용: ‘순차 토큰 예측’이 아니라 확산의 마스킹된 응답 위치들에 대한 항(항별 KL) 평균 형태로 설계되어, MDLM의 병렬 복원 구조를 반영한다는 뉘앙스가 있다(제공된 근거: “every masked response position”, “1/|Mt| … i∈Mt KL”). - 학습 관점: 제공된 근거는 지식 학습을 기준 궤적에서 새 궤적을 유도하는 최적화로 해석하고, 언러닝도 그 궤적 관점에서 목표를 구성한다고 설명한다. - 생성 궤적의 초기 단계 해석: 제공된 근거에 “Early in the trajectory… unmasked… exhibiting high KL divergence…” 같은 서술이 있어, 확산 궤적 내에서 조건부/앵커 간 불일치가 언러닝 손실로 작동할 수 있음을 시사한다(단, 세부 수치·해석은 제공된 발췌만으로는 제한적).

주요 근거:
- `Masked Diffusion Language Models Georu Lee1, Seungwon Jeong 1, Hoki Kim 2, Jinseong Park 3, Woojin Lee1 1Dongguk University-Seoul, 2Chung-Ang University, 3Korea Institute for Advanced Study {dlrjfn1,youai058,wj926}@dgu....`
- `For each column, boldmarks the best and underline the second-best among unlearning methods.`
- `LLaDA-8B-Instruct Dream-7B-Instruct Forget↓Neighbor↑Utility↑Forget↓Neighbor↑Utility↑ Method F-L1 F-L2 F-L3 N-L1 N-L2 MMLU TruQA TriQA F-L1 F-L2 F-L3 N-L1 N-L2 MMLU TruQA TriQA Base0.488 0.433 0.469 0.551 0.372 0.395 0.3...`
### 4. 실험/결과

실험/결과:
- - 평가 벤치마크: 두 가지 벤치마크 TOFU와 RWKU에서 실험을 수행한다(제공된 근거: “evaluate unlearning on two benchmarks, TOFU… and RWKU…”). - 비교 대상: 자동회귀 계열 기반의 언러닝 알고리즘 6개와 비교한다(제공된 근거: “six LLM unlearning algorithms: GA, GD, NPO, SimNPO, WGA, DPO”). - 백본(모델): LLaDA-8B-Instruct와 Dream-7B-Instruct 두 백본에서 결과를 보고한다(제공된 근거: Table 2/3 서술). - 언러닝-보존 트레이드오프 지표: 제공된 근거에서 TOFU는 forget/retain의 균형(예: forget↓, Retain↑ 등)과 함께 RA, WF 같은 보조 지표를 사용함을 표 설명에서 확인할 수 있다(제공된 근거: “Forget↓Retain↑RA↑WF↑”). - 온도 스위프(τ sweep): τ 값에 따른 성능 변화를 관찰하며, LLaDA에서는 τ=0.00이 최선 기준 대비 개선, Dream에서는 τ=0.50에서 동일한 패턴을 보였다고 서술한다(제공된 근거: “τ=0.00…”, “τ=0.50…”). - 정성 결과: TOFU와 RWKU의 forget set에 대한 정성적(qualitative) 결과를 포함한다(제공된 근거: “Table 4: Qualitative results…”).
- - RWKU 대상자 평균: RWKU에서는 10명의 target subjects에 대해 평균했다고 명시한다(제공된 근거: “averaged over ten target subjects.”). - 전반적 결론(추상 기반): MDU가 TOFU 및 RWKU에서 trade-off를 개선한다고 보고한다(제공된 근거: “MDU improves this trade-off across the τ sweep.”).

주요 근거:
- `Experiments 6.1 Experimental Setup Datasets and Models.`
- `We evaluate unlearning on two benchmarks, TOFU [ 11] and RWKU [12].`
- `Since TOFU provides a designated retain split, we add the same retain SFT regularizer to all unlearning objectives, including both MDU and the baselines.`
### 5. 한계와 확인 필요

한계와 확인 필요:
- - 제공된 근거에는 일반적인 실험 한계(데이터 규모, 계산량, 재현성 세부, 실패 양상 분해 등)에 대한 명시가 부족하다. 따라서 현재 제공된 정보만으로는 한계를 확정해 적기 어렵다. - 제시된 ‘limitations’ 배열의 항목은 인물/서술(예: Hsiao Yun-Hwa의 writing style)처럼 보이지만, 이것이 MDUs의 방법적 한계인지(예: 특정 스타일 데이터셋 영향) 여부는 제공된 발췌만으로 확인이 불가하다(“A: Hsiao Yun-Hwa’s writing style is unique…”). 추가 근거가 필요하다. - 실험 강도에 대한 정량적 평가는 제공된 추상 발췌 수준에서 제한적이며, 제공된 근거만으로 실험 설계의 상세(실험 반복 횟수, 통계적 유의성, 계산 비용 등)를 확인할 수 없다.

근거/검증 메모:
- - 제공된 근거는 논문 제목/초록 및 일부 섹션 발췌에 기반해 요약했으며, 세부 수치(표 전체)는 일부만 발췌되어 있어 정량 비교를 전부 재구성할 수 없다. - ‘높은 언러닝 성능’ 및 ‘기존 LLM 언러닝 방법 대비 개선’은 추상 및 표/서술 문장에서 확인되지만, 정확한 수치 비교는 표 전체 문맥이 필요하다(제공된 근거에 Table 2/3/4가 언급됨). - 정량 수치로 보이는 “8B, 7B, 3.8%, 1.4%, 20.6%, 20%, 10%”는 제공된 근거의 위치가 명확하지 않아, 어떤 지표/조건에 대응되는지 확인이 불가하다(추가 확인 필요). - 저자/코드 제공 링크는 제공된 근거에 명시되어 있으나, 실제 구현 디테일(학습 설정)은 추가 근거가 필요하다(추가 확인 필요).
주요 근거:
- `Experiments on TOFU and RWKU with LLaDA and Dream show that MDU improves the forget–retain trade-off over existing unlearning baselines, validating the necessity of our unlearning framework for MDLMs.`
- `The wmdp benchmark: measuring and reducing malicious use with unlearning.`
- `(2) 9: else 10: L sft ←0 11: end if 12: L ← Lforget +λL sft 13: θ←θ−AdamW   ∇θ L  ▷ θ0 remains frozen B Experiment Details B.1 TOFU Dataset.`

## 2. SPACE: Source-free Proxy Anchor Concept Erasure for MLLMs

- Authors: Zhijing Zhang, Jiaqi Ding, Qianshan Wei, Nan Zhou, Jiaqi Li, Yongliang Wu, Tongxin Zhu, Xiaolin Fang
- Published: 2026-06-01
- URL: https://arxiv.org/abs/2606.09868v1
- PDF: https://arxiv.org/pdf/2606.09868v1
- Source: arxiv
- DOI: N/A
- Venue: N/A
- Citations: N/A
- Google Scholar: https://scholar.google.com/scholar?q=SPACE%3A+Source-free+Proxy+Anchor+Concept+Erasure+for+MLLMs
- Evidence: PDF text, pages 20/27
- Reviewer score: 0.856 (relevance 0.800, novelty 1.000, experiments 0.880)
- Selection reason: query terms are strongly represented; contains novelty or recent-contribution signals; reports evaluation or quantitative evidence

### 1. 왜 중요한가

한 줄 요약: SPACE는 MLLM을 위한 최초의 ‘데이터 소스 없이’(target 개념의 원본 이미지 접근 없이) 프록시 앵커를 찾고 최적화해 목표 개념을 지우는 기법으로, 잔존 지식에 대한 변화는 제한하면서 성능 저하를 최소화하는 방향을 이론·실험으로 제시한다.

문제: 기존 기계 언유닝(특히 개념/정보 삭제)은 보통 목표 개념이 포함된 시각 데이터(이미지)에 접근해야 하지만, 개인정보·규제 제약으로 인해 target 소스를 보유/재사용할 수 없는 상황이 많다. 따라서 제공된 근거에서는 ‘원본 데이터 없이’ 오직 원래 모델과 목표 개념의 텍스트 설명만으로 MLLM에서 개념을 지우는 source-free 언유닝 요구가 커졌다고 문제를 설정한다. 또한 MLLM은 이미지-텍스트의 깊은 교차 결합이 있어(분류기와 달리 생성형 텍스트를 조건부로 만들기 때문) 기존 언유닝 패러다임이 그대로 적용되기 어렵다는 점도 강조된다. 제공된 근거에는 해결해야 할 핵심으로 (1) target 소스 부재에서 프록시를 어떻게 구성할지, (2) 프록시를 이용하되 잔존 지식(보존해야 할 능력)은 망가지지 않게 업데이트할지, (3) 실제 성능을 데이터 의존 방식과 비교해 검증할지 등이 포함된다.

주요 근거:
- `Limitations SPACE utilizes the public dataset Dpub to retrieve proxy anchors P.`
신뢰도: medium
### 2. 핵심 기여

새로움/차별점:
- 제공된 근거에서 SPACE는 ‘MLLM에 특화된 최초의 source-free 언유닝 프레임워크’로 명시된다(“first source-free unlearning framework specialized for MLLMs”). 이는 기존 MU가 target 시각 소스를 필요로 하는 병목을 직접 겨냥하며, 실제 배포 환경(엄격한 데이터 보존 정책)에서 중요한 차별점이 된다. 이 새로움은 ‘target data 접근 불가’ 상황을 전제로 한 설계 자체에서 드러난다.
- 새로운 시스템 구성으로 TPAS(텍스트-유도 프록시 앵커 선택)와 DCSI(이중 제약 기반 의미적 분리)를 2단계로 결합한다는 점이 차별점이다. 제공된 근거에서는 TPAS가 ‘공유된 특징 공간’에서 의미적으로 정렬된 프록시 앵커를 검색하고, DCSI가 이를 최적화해 목표 개념을 간접 삭제한다고 설명한다. 즉, 소스 없는 상황에서 ‘무엇을 삭제할지’를 원본 데이터 대신 프록시로 매핑하는 절차가 핵심 혁신으로 제시된다.
- DCSI가 업데이트를 잔존 지식의 ‘널 공간(null space)’에 가둔다고 주장하는 것이 기술적 새로움 포인트로 보인다. 제공된 근거에는 “confines updates to the null space of retained knowledge”라는 설명과 함께, 잔존 지식에 대한 섭동을 엄격히 제한한다는 이론적 정리/증명 언급이 포함된다(“theoretically prove”). 이는 단순히 성능을 유지한다고 말하는 수준을 넘어 ‘구조적 보전’을 겨냥한다는 점에서 중요하다.
- 또한 제공된 근거에서는 ‘특징(피처) 스펙트럴 엔트로피를 최대화’하는 방향의 최적화 성격을 함께 제시한다. 이는 프록시 앵커 쪽 표현을 어떻게 교란(지우기)할지에 대한 목적함수 설계 관점의 차별성으로 해석된다(“maximizes feature spectral entropy”).
- 실험 측면에서도 단순히 언유닝 여부만 보지 않고, ‘데이터 의존(state-of-the-art data-dependent) 방식과 성능이 비슷하다’고 주장한다. 제공된 근거는 6개 데이터셋에서 “comparable to … data-dependent methods”라고 서술하며, source-free 시나리오에서도 효과가 검증된다고 연결한다. 이 비교 프레이밍이 기존 방식 대비 SPACE의 실용적 가치를 뒷받침하려는 포인트다.
- 방법의 목표가 ‘잊기( forgetting )를 위해 단순히 그라디언트 상승’이 아니라, 제공된 근거에서 ‘프록시 앵커를 모델이 더 잘 기억하도록 강제해 민감 표현을 덮어쓰는 방식’으로도 대비된다(“Unlike prior methods … maximize forgetting … we explicitly force … memorize the proxy anchors to overwrite”). 즉, 삭제 방향을 강화하는 방식이 기존 MU와 다르다는 점이 추가 차별점이다.

주요 기여:
- SPACE 제안: MLLM을 위한 source-free 프록시 앵커 개념 지우기 프레임워크를 제시한다(“Source-free Proxy Anchor Concept Erasure (SPACE)”).
- TPAS 설계: target 원본 이미지가 없을 때, 공용/일반 특징 공간에서 목표 개념과 의미적으로 정렬된 프록시 앵커를 텍스트 유도로 선택하는 절차를 포함한다(“Text-Guided Proxy Anchor Selection (TPAS)”).
- DCSI 설계: 선택된 프록시 앵커를 기반으로 이중 제약을 걸어 목표 개념을 간접적으로 제거하는 최적화를 제안한다(“Dual-Constraint Semantic Isolation (DCSI)”).
- 이론적 보장: 잔존 지식에 대한 섭동(perturbation)을 엄격히 경계(bounded)하고, 특징 스펙트럴 엔트로피를 최대화하는 성질을 ‘이론적으로’ 증명했다고 제공된 근거에서 밝힌다(정리 번호 “Theorem 3.1” 언급 포함).
- 학습/최적화 관점: 전체 손실에 작업 손실과 정규화 항(예: 정형성/등방성 관련 정규화)이 결합되며, 제공된 근거에는 선형 부분공간(안전 기저 벡터로 생성된 Span)으로 그라디언트를 투영하는 “Projected Gradient Descent” 방식이 설명된다.
- 실험 검증: 6개 데이터셋에서 데이터 의존 SOTA 방식과 유사한 성능을 보였다고 주장하며, source-free 언유닝 시나리오의 유효성을 강조한다.
- 코드 공개 계획: 제공된 근거에는 소스 코드 공개(“will be released”)가 언급된다.

주요 근거:
- `In this work, we propose Source-free Proxy Anchor Concept Erasure (SPACE), the first source-free unlearning framework specialized for MLLM s.`
- `Introduction Multimodal Large Language Models (MLLM s) have achieved remarkable performance through large-scale *Equal contribution 1School of Computer Science and Engineering, Southeast University 2Institute of Automat...`
- `Unlike classifiers, MLLM s generate text sequences conditioned on visual inputs, resulting in deep cross-modal coupling between images and text.`
### 3. 방법

방법:
- 전제: 미리 학습된 MLLM이 있고, 원본 개인 데이터로 학습되었다는 설정(Mθ, D={(Ii,Ti)}Ni=1)이 제공된 근거에 등장한다. 언유닝 시에는 target 시각 데이터를 직접 접근하지 못하는 조건이 핵심이다.
- 텍스트-유도 프록시 앵커 선택(TPAS): target 원본 이미지 접근이 불가능할 때, 공용 데이터 Dpub에서 후보를 뽑아 목표 개념과 관련된 프록시 앵커를 검색·선택하는 단계가 제시된다. 또한 ‘나이브 랜덤 샘플링은 의미 정렬이 깨져 비효율’이라는 문제를 해결하기 위해 TPAS가 필요하다고 설명된다.
- 의미적 분리(DCSI): 선택된 프록시 앵커를 최적화해 목표 개념 임베딩(“ec is the target concept embedding.”)과의 결합이 약화되도록 유도하는 구성으로 설명된다.
- 손실 구성의 예시: 제공된 근거에는 전체 손실 Ltotal이 작업 손실(Ltask)과 앵커 관련 항, 분리 관련 항(λanc, λdiv 등)으로 구성된 형태가 제시되며, Ltask는 프록시 앵커 P에 대해 표준 크로스엔트로피를 수행한다고 적혀 있다.
- 잔존 지식 보존을 위한 제약: 안전 기저 벡터 UN이 생성하는 선형부분공간 Span(UN)에 맞춰 업데이트를 ‘투영’하는 방식이 등장한다. 또한 DCSI가 잔존 지식의 널 공간에 업데이트를 가둔다고 요약된다.
- 최적화 절차: “Projected Gradient Descent” 전략을 사용하며, 각 단계에서 Ltotal의 그라디언트를 계산한 뒤 안전 맨폴드(안전 제약)에 명시적으로 투영하여 파라미터를 업데이트한다고 제공된 근거에 서술된다.
- 업데이트 방향의 의도: 제공된 근거에서는 기존 MU의 ‘잊기 극대화(gradient ascent)’와 달리, 프록시 앵커를 더 잘 기억하도록 하여 원래의 민감 표현을 덮어쓴다는 방향이 대비로 제시된다.

주요 근거:
- `However, existing MU methods typically rely on visual data of the target concepts, which is often unavailable due to strict data retention policies, thus creating a demand for source-free unlearning approaches that oper...`
- `Furthermore, extensive experiments across six datasets show that SPACE achieves performance comparable to that of state-of-the-art data-dependent methods, validating its effectiveness in source-free MU scenarios.`
- `Generation of Synthetic Data Images of Trump Proxy Anchors Existing machine unlearning methods Existing sourcefree unlearning methods SPACE Unlearned Unforgotten Input: Require Target Concept Images source-free It is no...`
### 4. 실험/결과

실험/결과:
- 데이터셋: 제공된 근거에는 SPACE가 6개 데이터셋에서 평가된다고 하며, 구체적으로 Celebrities, Stanford Dogs, WikiArt, ImageNet-1k, SUN397, VegFru가 열거된다. 세부 사항은 Appendix D에 있다고 하나, 여기서는 확인 불가로 남긴다.
- 평가 지표: 제공된 근거에 “Experimental Setup Datasets and Evaluation Metrics” 항목이 언급되지만, 실제 지표 이름/정의는 제공된 텍스트 범위에 나타나지 않는다(추가 확인 필요).
- 기본 비교 맥락: source-free와 data-dependent(기존) 방법의 비교가 Figure 1 등에서 언급되며, 실험적으로는 ‘데이터 의존 SOTA와 성능이 비슷’하다고 주장한다. 다만 어떤 지표에서 어느 정도의 수치가 나왔는지는 제공된 근거 범위에서 구체적으로 확인되지 않는다(“comparable” 수준의 서술만 확인됨).
- 기존 source-free 대비: 제공된 근거에는 “current source-free unlearning methods are ineffective for MLLM s”라고 문제 제기가 등장하지만, 어떤 기존 방법과의 정량 비교가 제공된 근거에 직접 제시되었는지는 확인 불가다.
- 애블레이션/실패 신호: 제공된 근거에는 실패/제거 실험의 일부 결과가 나타난다. 예를 들어 Text-Anchor Repulsion(Lorth)을 제외하면 FA가 48.0%로 증가한다고 적혀 있다. 또한 |P|=1이면 삭제가 실패하는 취지의 설명이 있다(“|P|= 1 fails to erase.”).
- 하이퍼파라미터 민감도 신호: 제공된 근거에는 특정 Sth 값 범위(0.10~0.16)에서는 지우기(erasure)가 유도되지 않는 실패가 언급된다. 또한 λanc/λdiv의 의미는 손실 식에 등장하나, 각 값이 성능에 미치는 구체적 결과는 본 범위에서 추가 확인이 필요하다.
- 공용 데이터 활용: TPAS에서 공용 데이터 Dpub를 사용한다는 점이 한계로도 연결되며, 실험 설정이 이 전제를 기반으로 구성된 것으로 보인다.

주요 근거:
- `Emerging benchmarks have refined the evaluation landscape by establishing protocols to assess the efficacy and robustness of unlearning mechanisms (Maini et al., 2024; Xu et al., 2025a; b; c; Zheng et al., 2025; Liu et...`
- `To circumvent data reliance, source-free strategies focus on synthesizing surrogate super-2 Text of Target Concepts Images of Target Concepts Source-Free Unlearning Dogs FruitsLandmarks Tools Only Text of Target Concept...`
- `Preliminaries Let Mθ be a pre-trained MLLM trained on a private dataset D={(I i, Ti)}N i=1.`
### 5. 한계와 확인 필요

한계와 확인 필요:
- 공용 데이터에 의존: SPACE는 공용 데이터 Dpub를 이용해 프록시 앵커 P를 검색한다(“Limitations … retrieves proxy anchors P” 관련 문장). 즉, Dpub의 커버리지/품질이 간접적으로 성능에 영향을 줄 수 있다.
- 무작위 프록시 생성의 비효율: 제공된 근거에서는 나이브 랜덤 샘플링이 목표-특화 표현을 활성화하지 못해(semantic misalignment) 효과가 낮다고 명시한다. 따라서 프록시 선택의 품질이 중요하다.
- 텍스트 앵커 반발 항 제거 시 실패: Text-Anchor Repulsion(Lorth)을 제외하면 FA가 48.0%로 증가하며, 이는 구성요소가 삭제 성능에 필수적임을 시사한다(정확한 맥락/지표 정의는 추가 확인 필요).
- 특정 임계값 범위에서 불충분: Sth 값이 0.10~0.16 범위일 때는 erasure를 유도하지 못한다고 언급된다. 이는 하이퍼파라미터 선택 민감성을 시사하나, 어떤 설정에서 어떤 방식으로 튜닝했는지는 제공된 근거 범위에 없다.
- 프록시 앵커 수의 제약: |P|=1에서는 삭제가 실패한다고 제시된다. 즉, 최소한의 프록시 앵커 다양성/수량이 필요할 가능성이 있다.
- 제공된 근거에는 대표적 추가 한계(예: 어떤 시나리오/개념 유형에서 취약한지, 장기적/다중 개념 삭제에서의 거동, 실패 원인 정밀 분석)가 구체적으로 나타나지 않아 추가 확인이 필요하다.

근거/검증 메모:
- 제공된 근거는 논문 초록과 일부 본문/식/실험 관련 발췌로 구성되어 있으며(“PDF 20/27페이지”), 정량 수치·지표 정의·비교 기준은 근거 범위에서 충분히 확인되지 않는다.
- “여섯 데이터셋”, “데이터 의존 SOTA와 비슷”, “source-free 프레임워크 최초(MLLM 특화)”, “이론적 보장(잔존 지식 섭동 경계, 스펙트럴 엔트로피 최대화)” 같은 핵심 주장은 초록/서술에서 확인된다.
- 손실 구성 식(Ltotal의 형태), Projected Gradient Descent, Span(UN) 및 안전 제약 투영 같은 학습/최적화 메커니즘은 제공된 근거에서 확인된다.
- 애블레이션의 일부 수치(예: FA가 48.0%로 증가, |P|=1 실패)와 특정 하이퍼파라미터 범위(Sth 0.10~0.16 실패)가 제공된 근거에 포함되어 있다.
- 정확히 어떤 평가지표(예: FA가 의미하는 바, 유해/삭제/보존을 어떻게 수치화하는지), 각 데이터셋에서 어떤 수치로 비교했는지는 제공된 근거에 나타나지 않아 추가 확인 필요로 남긴다.
- 정리(예: Theorem 3.1)의 정확한 문장/가정/증명 내용은 근거 범위에서 완전한 형태로 확인되지 않는다.
주요 근거:
- `Emerging benchmarks have refined the evaluation landscape by establishing protocols to assess the efficacy and robustness of unlearning mechanisms (Maini et al., 2024; Xu et al., 2025a; b; c; Zheng et al., 2025; Liu et...`
- `To circumvent data reliance, source-free strategies focus on synthesizing surrogate super-2 Text of Target Concepts Images of Target Concepts Source-Free Unlearning Dogs FruitsLandmarks Tools Only Text of Target Concept...`
- `Preliminaries Let Mθ be a pre-trained MLLM trained on a private dataset D={(I i, Ti)}N i=1.`
