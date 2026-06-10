# PaperPilot Run Log: dllm Unlearning
- Selected papers: 3
- Min relevance: 0.350
- Categories: Any
- Search mode: strict title/abstract
- Agentic mode: policy, max steps 8
- Unique candidates: 98
- Duplicates merged: 47
- PDF evidence: Enabled, max pages 20, max chars 64000
- Summary backend: factchat, detail ultra, model gpt-5.4-nano

## Search Attempts

| Source | Query | Status | Results | Note |
| --- | --- | --- | ---: | --- |
| arxiv | Machine Unlearning in Masked Diffusion Language Models | too_few_results | 1 | Too few recent candidates; trying another source or broader query. |
| openalex | Machine Unlearning in Masked Diffusion Language Models | success | 20 | Enough recent candidates found. |
| arxiv | Machine Unlearning in Masked DLMs | too_few_results | 0 | Too few recent candidates; trying another source or broader query. |
| openalex | Machine Unlearning in Masked DLMs | too_few_results | 1 | Too few recent candidates; trying another source or broader query. |
| arxiv | diffusion language model unlearning | success | 3 | Enough recent candidates found. |
| openalex | diffusion language model unlearning | success | 20 | Enough recent candidates found. |
| arxiv | discrete diffusion language model unlearning | too_few_results | 0 | Too few recent candidates; trying another source or broader query. |
| openalex | discrete diffusion language model unlearning | success | 20 | Enough recent candidates found. |
| arxiv | language model unlearning | success | 20 | Enough recent candidates found. |
| openalex | language model unlearning | success | 20 | Enough recent candidates found. |
| arxiv | LLM unlearning | success | 20 | Enough recent candidates found. |
| openalex | LLM unlearning | success | 20 | Enough recent candidates found. |

## Agent Trace

### Plan

| Step | Action | Input | Observation | Decision | Status |
| --- | --- | --- | --- | --- | --- |
| plan_query | Plan bounded query variants | Machine Unlearning in Masked Diffusion Language Models | 6 query variant(s) attempted | Use deterministic expansion and stop when the candidate budget is filled. | completed |

### Search/Observe

| Step | Action | Input | Observation | Decision | Status |
| --- | --- | --- | --- | --- | --- |
| observe | Observe search result | arxiv: Machine Unlearning in Masked Diffusion Language Models | arxiv produced 1 result(s) for `Machine Unlearning in Masked Diffusion Language Models`. | Pass observation to CurationPolicyAgent. | replanned |
| observe | Observe search result | openalex: Machine Unlearning in Masked Diffusion Language Models | openalex produced 20 result(s) for `Machine Unlearning in Masked Diffusion Language Models`. | Pass observation to CurationPolicyAgent. | continued |
| decide | CurationPolicyAgent selected `continue` | openalex: Machine Unlearning in Masked Diffusion Language Models | openalex produced 20 result(s) for `Machine Unlearning in Masked Diffusion Language Models`. | Continue merging candidates and evaluating the current candidate pool. | continued |
| observe | Observe search result | arxiv: Machine Unlearning in Masked DLMs | arxiv produced 0 result(s) for `Machine Unlearning in Masked DLMs`. | Pass observation to CurationPolicyAgent. | replanned |
| observe | Observe search result | openalex: Machine Unlearning in Masked DLMs | openalex produced 1 result(s) for `Machine Unlearning in Masked DLMs`. | Pass observation to CurationPolicyAgent. | replanned |
| observe | Observe search result | arxiv: diffusion language model unlearning | arxiv produced 3 result(s) for `diffusion language model unlearning`. | Pass observation to CurationPolicyAgent. | continued |
| decide | CurationPolicyAgent selected `continue` | arxiv: diffusion language model unlearning | arxiv produced 3 result(s) for `diffusion language model unlearning`. | Continue merging candidates and evaluating the current candidate pool. | continued |
| observe | Observe search result | openalex: diffusion language model unlearning | openalex produced 20 result(s) for `diffusion language model unlearning`. | Pass observation to CurationPolicyAgent. | continued |
| decide | CurationPolicyAgent selected `continue` | openalex: diffusion language model unlearning | openalex produced 20 result(s) for `diffusion language model unlearning`. | Continue merging candidates and evaluating the current candidate pool. | continued |
| observe | Observe search result | arxiv: discrete diffusion language model unlearning | arxiv produced 0 result(s) for `discrete diffusion language model unlearning`. | Pass observation to CurationPolicyAgent. | replanned |
| observe | Observe search result | openalex: discrete diffusion language model unlearning | openalex produced 20 result(s) for `discrete diffusion language model unlearning`. | Pass observation to CurationPolicyAgent. | continued |
| decide | CurationPolicyAgent selected `continue` | openalex: discrete diffusion language model unlearning | openalex produced 20 result(s) for `discrete diffusion language model unlearning`. | Continue merging candidates and evaluating the current candidate pool. | continued |
| observe | Observe search result | arxiv: language model unlearning | arxiv produced 20 result(s) for `language model unlearning`. | Pass observation to CurationPolicyAgent. | continued |
| decide | CurationPolicyAgent selected `continue` | arxiv: language model unlearning | arxiv produced 20 result(s) for `language model unlearning`. | Continue merging candidates and evaluating the current candidate pool. | continued |
| observe | Observe search result | openalex: language model unlearning | openalex produced 20 result(s) for `language model unlearning`. | Pass observation to CurationPolicyAgent. | continued |
| decide | CurationPolicyAgent selected `continue` | openalex: language model unlearning | openalex produced 20 result(s) for `language model unlearning`. | Continue merging candidates and evaluating the current candidate pool. | continued |
| observe | Observe search result | arxiv: LLM unlearning | arxiv produced 20 result(s) for `LLM unlearning`. | Pass observation to CurationPolicyAgent. | continued |
| decide | CurationPolicyAgent selected `continue` | arxiv: LLM unlearning | arxiv produced 20 result(s) for `LLM unlearning`. | Continue merging candidates and evaluating the current candidate pool. | continued |
| observe | Observe search result | openalex: LLM unlearning | openalex produced 20 result(s) for `LLM unlearning`. | Pass observation to CurationPolicyAgent. | continued |
| decide | CurationPolicyAgent selected `continue` | openalex: LLM unlearning | openalex produced 20 result(s) for `LLM unlearning`. | Continue merging candidates and evaluating the current candidate pool. | continued |
| search_source | Search arxiv | Machine Unlearning in Masked Diffusion Language Models | 1 result(s), status=too_few_results | Too few recent candidates; trying another source or broader query. | too_few_results |
| observe_results | Inspect result count and source status | arxiv: Machine Unlearning in Masked Diffusion Language Models | 1 candidate(s) returned | Continue with another source or broader query variant. | too_few_results |
| search_source | Search openalex | Machine Unlearning in Masked Diffusion Language Models | 20 result(s), status=success | Enough recent candidates found. | success |
| observe_results | Inspect result count and source status | openalex: Machine Unlearning in Masked Diffusion Language Models | 20 candidate(s) returned | Keep candidates and continue merging metadata. | success |
| search_source | Search arxiv | Machine Unlearning in Masked DLMs | 0 result(s), status=too_few_results | Too few recent candidates; trying another source or broader query. | too_few_results |
| observe_results | Inspect result count and source status | arxiv: Machine Unlearning in Masked DLMs | 0 candidate(s) returned | Continue with another source or broader query variant. | too_few_results |
| search_source | Search openalex | Machine Unlearning in Masked DLMs | 1 result(s), status=too_few_results | Too few recent candidates; trying another source or broader query. | too_few_results |
| observe_results | Inspect result count and source status | openalex: Machine Unlearning in Masked DLMs | 1 candidate(s) returned | Continue with another source or broader query variant. | too_few_results |
| search_source | Search arxiv | diffusion language model unlearning | 3 result(s), status=success | Enough recent candidates found. | success |
| observe_results | Inspect result count and source status | arxiv: diffusion language model unlearning | 3 candidate(s) returned | Keep candidates and continue merging metadata. | success |
| search_source | Search openalex | diffusion language model unlearning | 20 result(s), status=success | Enough recent candidates found. | success |
| observe_results | Inspect result count and source status | openalex: diffusion language model unlearning | 20 candidate(s) returned | Keep candidates and continue merging metadata. | success |
| search_source | Search arxiv | discrete diffusion language model unlearning | 0 result(s), status=too_few_results | Too few recent candidates; trying another source or broader query. | too_few_results |
| observe_results | Inspect result count and source status | arxiv: discrete diffusion language model unlearning | 0 candidate(s) returned | Continue with another source or broader query variant. | too_few_results |
| search_source | Search openalex | discrete diffusion language model unlearning | 20 result(s), status=success | Enough recent candidates found. | success |
| observe_results | Inspect result count and source status | openalex: discrete diffusion language model unlearning | 20 candidate(s) returned | Keep candidates and continue merging metadata. | success |
| search_source | Search arxiv | language model unlearning | 20 result(s), status=success | Enough recent candidates found. | success |
| observe_results | Inspect result count and source status | arxiv: language model unlearning | 20 candidate(s) returned | Keep candidates and continue merging metadata. | success |
| search_source | Search openalex | language model unlearning | 20 result(s), status=success | Enough recent candidates found. | success |
| observe_results | Inspect result count and source status | openalex: language model unlearning | 20 candidate(s) returned | Keep candidates and continue merging metadata. | success |
| search_source | Search arxiv | LLM unlearning | 20 result(s), status=success | Enough recent candidates found. | success |
| observe_results | Inspect result count and source status | arxiv: LLM unlearning | 20 candidate(s) returned | Keep candidates and continue merging metadata. | success |
| search_source | Search openalex | LLM unlearning | 20 result(s), status=success | Enough recent candidates found. | success |
| observe_results | Inspect result count and source status | openalex: LLM unlearning | 20 candidate(s) returned | Keep candidates and continue merging metadata. | success |
| summarize | Generate Korean five-part summaries | backend=factchat, detail=ultra, model=gpt-5.4-nano | 3 summary item(s) generated | Keep summaries structured as problem, contribution, method, results, and limitations. | completed |

### Replan

| Step | Action | Input | Observation | Decision | Status |
| --- | --- | --- | --- | --- | --- |
| decide | CurationPolicyAgent selected `expand_query` | arxiv: Machine Unlearning in Masked Diffusion Language Models | arxiv produced 1 result(s) for `Machine Unlearning in Masked Diffusion Language Models`. | Try the next planned query variant before accepting a weak candidate pool. | replanned |
| act | Apply `expand_query` | arxiv: Machine Unlearning in Masked Diffusion Language Models | arxiv produced 1 result(s) for `Machine Unlearning in Masked Diffusion Language Models`. | Try the next planned query variant before accepting a weak candidate pool. | replanned |
| decide | CurationPolicyAgent selected `expand_query` | arxiv: Machine Unlearning in Masked DLMs | arxiv produced 0 result(s) for `Machine Unlearning in Masked DLMs`. | Try the next planned query variant before accepting a weak candidate pool. | replanned |
| act | Apply `expand_query` | arxiv: Machine Unlearning in Masked DLMs | arxiv produced 0 result(s) for `Machine Unlearning in Masked DLMs`. | Try the next planned query variant before accepting a weak candidate pool. | replanned |
| decide | CurationPolicyAgent selected `expand_query` | openalex: Machine Unlearning in Masked DLMs | openalex produced 1 result(s) for `Machine Unlearning in Masked DLMs`. | Try the next planned query variant before accepting a weak candidate pool. | replanned |
| act | Apply `expand_query` | openalex: Machine Unlearning in Masked DLMs | openalex produced 1 result(s) for `Machine Unlearning in Masked DLMs`. | Try the next planned query variant before accepting a weak candidate pool. | replanned |
| decide | CurationPolicyAgent selected `expand_query` | arxiv: discrete diffusion language model unlearning | arxiv produced 0 result(s) for `discrete diffusion language model unlearning`. | Try the next planned query variant before accepting a weak candidate pool. | replanned |
| act | Apply `expand_query` | arxiv: discrete diffusion language model unlearning | arxiv produced 0 result(s) for `discrete diffusion language model unlearning`. | Try the next planned query variant before accepting a weak candidate pool. | replanned |
| replan | Recover from weak observation | arxiv: Machine Unlearning in Masked Diffusion Language Models | Too few recent candidates; trying another source or broader query. | Try the remaining planned source/query combinations. | continued |
| replan | Recover from weak observation | arxiv: Machine Unlearning in Masked DLMs | Too few recent candidates; trying another source or broader query. | Try the remaining planned source/query combinations. | continued |
| replan | Recover from weak observation | openalex: Machine Unlearning in Masked DLMs | Too few recent candidates; trying another source or broader query. | Try the remaining planned source/query combinations. | continued |
| replan | Recover from weak observation | arxiv: discrete diffusion language model unlearning | Too few recent candidates; trying another source or broader query. | Try the remaining planned source/query combinations. | continued |

### Review

| Step | Action | Input | Observation | Decision | Status |
| --- | --- | --- | --- | --- | --- |
| dedupe | Merge duplicate papers across sources | 145 raw result(s) | 47 duplicate result(s) merged | Review 98 unique candidate(s). | completed |
| review | Score relevance, novelty, and experimental strength | 98 candidate(s) | 64 candidate(s) passed min relevance 0.350 | Select top 3 paper(s) for summary. | completed |

### Evidence Recovery

| Step | Action | Input | Observation | Decision | Status |
| --- | --- | --- | --- | --- | --- |
| extract_pdf | Fetch selected-paper PDFs for grounded evidence | 3 selected paper(s) | 3/3 PDF extraction(s) succeeded | Use PDF text when available; otherwise keep abstract-only evidence. | success |
| observe | Observe workflow state | selected-paper PDFs | 3/3 PDF extraction(s) succeeded. | Pass observation to CurationPolicyAgent. | continued |
| decide | CurationPolicyAgent selected `continue` | selected-paper PDFs | 3/3 PDF extraction(s) succeeded. | Use extracted PDF evidence for selected papers. | continued |

### Summary Reflection

| Step | Action | Input | Observation | Decision | Status |
| --- | --- | --- | --- | --- | --- |
| reflect | Validate summary quality gates | 3 summary item(s) | 3/3 summary reflection(s) passed | Surface caveats or fallback reasons when quality checks fail. | completed |
| observe | Observe workflow state | summary reflection | 3/3 summary reflection(s) passed. | Pass observation to CurationPolicyAgent. | continued |
| decide | CurationPolicyAgent selected `continue` | summary reflection | 3/3 summary reflection(s) passed. | Publish summaries after reflection checks. | continued |
