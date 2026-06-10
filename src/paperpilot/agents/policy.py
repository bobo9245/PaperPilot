"""Deterministic policy decisions for the PaperPilot agent loop."""

from __future__ import annotations

import json
import os

from paperpilot.models import PolicyDecision, SearchAttempt


AGENTIC_MODES = {"off", "policy", "hybrid"}
POLICY_ACTIONS = {
    "continue",
    "expand_query",
    "try_broad_search",
    "skip_rate_limited_source",
    "use_abstract_fallback",
    "use_heuristic_summary_fallback",
    "stop_with_failure_analysis",
}


class CurationPolicyAgent:
    """Choose the next curation action from observable workflow state."""

    def decide_after_search(
        self,
        attempt: SearchAttempt,
        *,
        candidate_count: int,
        strict_search: bool,
        broad_search_used: bool,
        has_more_query_variants: bool,
        max_agent_steps_reached: bool,
    ) -> PolicyDecision:
        """Choose a next search action from one search observation."""

        if _is_rate_limit(attempt):
            return PolicyDecision(
                action="skip_rate_limited_source",
                observation=f"{attempt.source} returned a rate-limit error.",
                decision="Disable this source for the remaining run and continue with other sources.",
                status="recovered",
            )

        if max_agent_steps_reached and candidate_count == 0:
            return PolicyDecision(
                action="stop_with_failure_analysis",
                observation="The agent step budget was exhausted before any candidate passed collection.",
                decision="Stop active search and report why the run failed.",
                status="stopped",
            )

        if attempt.results_count == 0 and strict_search and not broad_search_used and not has_more_query_variants:
            return PolicyDecision(
                action="try_broad_search",
                observation="Strict title/abstract search returned no candidates across planned queries.",
                decision="Retry the original query once with broad all-fields search.",
                status="replanned",
            )

        if attempt.status in {"too_few_results", "error"} and has_more_query_variants:
            return PolicyDecision(
                action="expand_query",
                observation=f"{attempt.source} produced {attempt.results_count} result(s) for `{attempt.query}`.",
                decision="Try the next planned query variant before accepting a weak candidate pool.",
                status="replanned",
            )

        return PolicyDecision(
            action="continue",
            observation=f"{attempt.source} produced {attempt.results_count} result(s) for `{attempt.query}`.",
            decision="Continue merging candidates and evaluating the current candidate pool.",
            status="continued",
        )

    def decide_after_pdf(self, *, selected_count: int, pdf_successes: int) -> PolicyDecision:
        """Choose an evidence recovery action after PDF extraction."""

        if selected_count and pdf_successes < selected_count:
            return PolicyDecision(
                action="use_abstract_fallback",
                observation=f"{pdf_successes}/{selected_count} PDF extraction(s) succeeded.",
                decision="Use available PDF evidence and fall back to abstracts for missing PDFs.",
                status="recovered",
            )
        return PolicyDecision(
            action="continue",
            observation=f"{pdf_successes}/{selected_count} PDF extraction(s) succeeded.",
            decision="Use extracted PDF evidence for selected papers.",
            status="continued",
        )

    def decide_after_summary(
        self,
        *,
        selected_count: int,
        reflection_passes: int,
        fallback_reason: str | None,
    ) -> PolicyDecision:
        """Choose a summary recovery action after reflection/fallback checks."""

        if fallback_reason:
            return PolicyDecision(
                action="use_heuristic_summary_fallback",
                observation=fallback_reason,
                decision="Keep the report runnable by using deterministic summaries where needed.",
                status="fallback",
            )
        if selected_count and reflection_passes < selected_count:
            return PolicyDecision(
                action="use_heuristic_summary_fallback",
                observation=f"{reflection_passes}/{selected_count} summary reflection(s) passed.",
                decision="Patch summaries with explicit caveats and keep the report evidence-bounded.",
                status="recovered",
            )
        return PolicyDecision(
            action="continue",
            observation=f"{reflection_passes}/{selected_count} summary reflection(s) passed.",
            decision="Publish summaries after reflection checks.",
            status="continued",
        )

    def decide_zero_selected(
        self,
        *,
        candidate_count: int,
        min_relevance: float,
        rate_limited_sources: tuple[str, ...],
    ) -> PolicyDecision:
        """Explain why a run ended without selected papers."""

        if rate_limited_sources:
            reason = f"rate-limited sources: {', '.join(rate_limited_sources)}"
        elif candidate_count == 0:
            reason = "no unique candidates were collected"
        else:
            reason = f"{candidate_count} candidate(s) were collected but none passed relevance {min_relevance:.3f}"
        return PolicyDecision(
            action="stop_with_failure_analysis",
            observation=reason,
            decision="Report failure causes and suggest broadening the query, lowering min relevance, or adding sources.",
            status="stopped",
        )


class AdvisorAgent:
    """Optional LLM action advisor guarded by the deterministic policy."""

    def __init__(self, *, client=None, model: str | None = None) -> None:
        self.client = client
        self.model = model

    def advise(
        self,
        *,
        observation: str,
        policy_action: str,
        allowed_actions: tuple[str, ...],
    ) -> str:
        """Suggest one allowed action, or return the policy action on any failure."""

        if policy_action not in allowed_actions:
            return allowed_actions[0]
        client = self.client or _advisor_client()
        if client is None:
            return policy_action
        model = self.model or _advisor_model()
        try:
            response = client.chat.completions.create(
                model=model,
                messages=[
                    {
                        "role": "system",
                        "content": (
                            "You are a conservative workflow advisor. "
                            "Return JSON only with an action from allowed_actions."
                        ),
                    },
                    {
                        "role": "user",
                        "content": json.dumps(
                            {
                                "observation": observation,
                                "policy_action": policy_action,
                                "allowed_actions": allowed_actions,
                            },
                            ensure_ascii=False,
                        ),
                    },
                ],
                response_format={"type": "json_object"},
            )
            content = response.choices[0].message.content
            data = json.loads(content)
            action = data.get("action")
        except Exception:
            return policy_action
        return action if action in allowed_actions else policy_action


def validate_agentic_mode(mode: str) -> None:
    if mode not in AGENTIC_MODES:
        raise ValueError("agentic_mode must be one of: off, policy, hybrid")


def _is_rate_limit(attempt: SearchAttempt) -> bool:
    text = f"{attempt.status} {attempt.message}".lower()
    return "429" in text or "rate limit" in text or "too many requests" in text


def _advisor_client():
    try:
        from openai import OpenAI
    except ImportError:
        return None
    factchat_key = os.environ.get("FACTCHAT_API_KEY") or os.environ.get("PAPERPILOT_FACTCHAT_API_KEY")
    if factchat_key:
        base_url = os.environ.get("PAPERPILOT_FACTCHAT_BASE_URL") or "https://factchat-cloud.mindlogic.ai/v1/gateway"
        return OpenAI(api_key=factchat_key, base_url=base_url)
    openai_key = os.environ.get("OPENAI_API_KEY")
    if openai_key:
        return OpenAI(api_key=openai_key)
    return None


def _advisor_model() -> str:
    if os.environ.get("FACTCHAT_API_KEY") or os.environ.get("PAPERPILOT_FACTCHAT_API_KEY"):
        return os.environ.get("PAPERPILOT_FACTCHAT_MODEL") or "gpt-5.4-nano"
    return os.environ.get("PAPERPILOT_OPENAI_MODEL") or "gpt-5.2"
