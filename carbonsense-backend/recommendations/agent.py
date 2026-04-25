"""
Agentic RAG recommendation pipeline.

Six-step loop driven by PipelineTracer:
  1. Build place context (UC JSON + coordinates).
  2. Plan tool calls with the LLM (JSON).
  3. Execute tools: PolicyRetriever, NewsRetriever, WebSearch.
  4. Synthesize the structured 6-section recommendation, optionally injecting
     thumbs-up few-shot examples for (sector, country).
  5. Critic pass — if the draft is too generic or contradicts the place data,
     run one re-synthesis turn.
  6. Persist a Recommendation row so chat / feedback can reference it.
"""

from __future__ import annotations

import json
import logging
import time
from datetime import datetime, timezone
from typing import Any, Dict, List

from django.conf import settings

from recommendations.feedback import FeedbackService
from recommendations.llm_client import LLMClient
from recommendations.models import Recommendation
from recommendations.pipeline_tracer import PipelineTracer
from recommendations.tools.emission_context import (
    build_place_context,
    summarize_for_prompt,
)
from recommendations.tools.policy_retriever import NewsRetriever, PolicyRetriever
from recommendations.tools.web_search import WebSearch

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------- #
# Prompts
# ---------------------------------------------------------------------- #

PLANNER_SYSTEM = (
    "You decide which retrieval tools to invoke for an emission-reduction "
    "recommendation request. Reply with strict JSON only."
)


def _planner_prompt(ctx: Dict[str, Any]) -> str:
    return (
        "Given this place context, decide which search queries to issue.\n"
        f"PLACE CONTEXT:\n{summarize_for_prompt(ctx)}\n\n"
        "Return JSON with this exact schema:\n"
        "{\n"
        "  \"policy_query\": \"short string focused on long-lived policy\",\n"
        "  \"news_query\": \"short string focused on 2025-2026 news / pilots\",\n"
        "  \"web_query\": \"short string for current global references\"\n"
        "}\n"
        "Each query must mention the dominant emitter and at least one risk flag if any."
    )


SYNTH_SYSTEM = (
    "You are a senior climate policy advisor for the Government of Punjab. "
    "Produce site-specific, IMPLEMENTABLE emission-reduction recommendations "
    "for the named Union Council. Every action must reference real numbers "
    "from the data block. Cite policies that actually appear in the retrieved "
    "context. Reply with valid JSON only — no markdown, no explanations."
)


def _synth_prompt(ctx: Dict[str, Any], policies_block: str, news_block: str,
                  web_block: str, examples: List[dict]) -> str:
    area = ctx.get('area_name') or 'this UC'
    sector = ctx.get('sector') or 'transport'
    transport = ctx.get('transport') or {}
    forecast_total = transport.get('forecast_annual_t', 0)
    rank = transport.get('rank_in_division', 0)

    examples_block = ''
    if examples:
        examples_block += (
            "\n\nFor calibration, here are previously high-rated outputs for "
            f"similar contexts ({sector}). MATCH this quality bar; do NOT copy specifics:\n"
        )
        for ex in examples[:2]:
            examples_block += f"- Section: {ex.get('section')}\n  {json.dumps(ex.get('content'))[:500]}\n"

    return (
        f"AREA: {area}\nSECTOR: {sector}\n\n"
        f"PLACE CONTEXT:\n{summarize_for_prompt(ctx)}\n\n"
        f"RETRIEVED POLICIES:\n{policies_block}\n\n"
        f"RECENT NEWS / PILOTS:\n{news_block}\n\n"
        f"GLOBAL WEB REFERENCES (2025/2026):\n{web_block}\n"
        f"{examples_block}\n"
        "Return JSON exactly in this schema. Every recommendation MUST name "
        f"{area} specifically and reference numeric data above:\n"
        "{\n"
        f"  \"summary\": \"3-4 sentences. Start with: '{area} UC emits [total] tonnes CO2e annually, ranking #[rank]/151 in Lahore District.' Use exact numbers from the data ({forecast_total:,.0f} t, rank #{rank}).\",\n"
        "  \"immediate_actions\": [\n"
        "    \"5 actions. Format: **Bold Title** - [Expected Impact]: X% reduction of [N tonnes] - [Estimated Cost Range]: PKR X Million - [Implementation Priority]: High/Medium/Low. Each must reference a specific number from the place context.\"\n"
        "  ],\n"
        "  \"long_term_strategies\": [\n"
        "    \"3-4 strategies. Format: **Bold Title** - [Timeline]: X years - [Expected Reduction]: X% - [Key Milestones]: Year 1: ... Year 2: ...\"\n"
        "  ],\n"
        "  \"policy_recommendations\": [\n"
        "    \"3-4 items. Each MUST cite either a real Pakistan/Punjab law (e.g. 'Punjab Environmental Protection Act 1997 Sec 11', 'Pakistan Climate Change Act 2017', 'NEV Policy 2019') OR a global policy that appeared in the retrieved context. Explain how it applies to this UC.\"\n"
        "  ],\n"
        "  \"monitoring_metrics\": [\n"
        "    \"3-4 KPIs measurable at the UC level with baseline values from the data above.\"\n"
        "  ],\n"
        "  \"risk_factors\": [\n"
        "    \"3-4 risks specific to this UC's geography or risk flags (cite them).\"\n"
        "  ]\n"
        "}\n"
        "Return ONLY valid JSON."
    )


CRITIC_SYSTEM = (
    "You audit a draft recommendation JSON. Judge whether it is place-specific, "
    "uses the actual numbers from the data block, cites real policies, and "
    "stays current (2025-2026). Reply with strict JSON."
)


def _critic_prompt(ctx: Dict[str, Any], draft: dict) -> str:
    return (
        "Evaluate this draft. Look for these failure modes:\n"
        " - generic advice that could apply to any city,\n"
        " - missing or wrong numbers,\n"
        " - made-up policies / laws not present in the retrieved context,\n"
        " - outdated references.\n\n"
        f"PLACE CONTEXT:\n{summarize_for_prompt(ctx)}\n\n"
        f"DRAFT:\n{json.dumps(draft, indent=2)[:6000]}\n\n"
        "Return JSON: {\n"
        "  \"needs_revision\": bool,\n"
        "  \"issues\": [string, ...],\n"
        "  \"score\": int 1-10\n"
        "}"
    )


def _resynth_prompt(draft: dict, issues: List[str], synth_user_prompt: str) -> str:
    return (
        "Your previous draft had these issues. Fix them while keeping the same JSON schema:\n"
        + "\n".join(f"- {i}" for i in issues)
        + "\n\nORIGINAL DRAFT:\n"
        + json.dumps(draft, indent=2)[:4000]
        + "\n\nORIGINAL CONTEXT (re-read):\n"
        + synth_user_prompt[:3000]
        + "\n\nReturn ONLY the corrected JSON."
    )


# ---------------------------------------------------------------------- #
# Helpers
# ---------------------------------------------------------------------- #

def _parse_json(raw: str) -> dict:
    cleaned = (raw or '').strip()
    if cleaned.startswith('```'):
        cleaned = cleaned.split('\n', 1)[-1]
        cleaned = cleaned.rsplit('```', 1)[0]
    parsed = json.loads(cleaned)
    # Some free-tier LLMs wrap their reply as a single-element array even
    # when the schema asks for an object. Unwrap so callers can treat it
    # as a dict uniformly.
    if isinstance(parsed, list):
        parsed = parsed[0] if parsed else {}
    if not isinstance(parsed, dict):
        return {}
    return parsed


def _format_results_block(items: List[dict]) -> str:
    if not items:
        return "(none)"
    lines = []
    for i, item in enumerate(items, 1):
        meta = item.get('metadata') or {}
        title = meta.get('document_title', '?')
        year = meta.get('year', '')
        country = meta.get('country', '')
        text = (item.get('text') or '')[:240].strip()
        lines.append(f"[{i}] {title} ({year}, {country}): {text}")
    return "\n".join(lines)


# ---------------------------------------------------------------------- #
# Agent
# ---------------------------------------------------------------------- #

class RecommendationAgent:
    """Six-step agentic RAG recommendation generator."""

    def __init__(self):
        self.llm = LLMClient()
        self.critic = LLMClient(provider=getattr(settings, 'LLM_CRITIC_PROVIDER', None))
        self.policy_retriever = PolicyRetriever()
        self.news_retriever = NewsRetriever()
        self.web = WebSearch()

    # ------------------------------------------------------------------ #
    # Public API
    # ------------------------------------------------------------------ #

    def generate(self, area_id: str, area_name: str, sector: str,
                 coordinates: Dict[str, Any], trace: bool = True) -> Dict[str, Any]:
        tracer = PipelineTracer()
        started = time.time()

        # Step 1 — place context
        with tracer.step(1, "Build place context") as t:
            ctx = build_place_context(area_name, sector, coordinates)
            t.add_data({
                'has_transport': ctx['transport'] is not None,
                'has_buildings': ctx['buildings'] is not None,
                'has_waste': ctx['waste'] is not None,
                'risk_flags': ctx.get('risk_flags', []),
                'top_emitters': ctx.get('top_emitters', []),
                'rank_in_division': ctx.get('rank_in_division'),
            })

        # Step 2 — planner
        with tracer.step(2, "Plan tool calls") as t:
            plan = self._plan(ctx)
            t.add_data({
                'provider': self.llm.provider_name,
                'model': self.llm.model_name,
                'plan': plan,
            })

        # Step 3 — tools
        with tracer.step(3, "Retrieve policies, news, web") as t:
            policies = self._safe(lambda: self.policy_retriever.retrieve(ctx, n_results=5)) or []
            news = self._safe(lambda: self.news_retriever.retrieve(ctx, n_results=3)) or []
            web_results = self._safe(
                lambda: self.web.search(plan.get('web_query') or self._fallback_web_query(ctx),
                                       max_results=4, days=365)
            ) or []
            t.add_data({
                'policy_count': len(policies),
                'news_count': len(news),
                'web_count': len(web_results),
                'top_policy_titles': [
                    (p.get('metadata') or {}).get('document_title') for p in policies[:5]
                ],
            })

        # Step 4 — synthesize
        with tracer.step(4, "Synthesize recommendation") as t:
            country = (ctx.get('country') or 'Pakistan')
            examples = FeedbackService.get_examples_for(sector, country, max_examples=2)
            synth_user = _synth_prompt(
                ctx,
                self.policy_retriever.format_for_prompt(policies),
                _format_results_block(news),
                _format_results_block(web_results),
                examples,
            )
            try:
                draft_text = self.llm.generate(SYNTH_SYSTEM, synth_user,
                                               json_mode=True, max_tokens=2200,
                                               temperature=0.55)
                draft = _parse_json(draft_text)
            except Exception as exc:
                t.add_data({'status': 'error', 'error': str(exc)})
                raise
            t.add_data({
                'examples_injected': len(examples),
                'draft_keys': list(draft.keys()),
                'synth_prompt_preview': synth_user[:1500],
            })

        # Step 5 — critic
        critic_payload: Dict[str, Any] = {'enabled': False}
        if getattr(settings, 'RECOMMENDATION_CRITIC_ENABLED', True):
            with tracer.step(5, "Critique and (optionally) revise") as t:
                try:
                    critique_text = self.critic.generate(
                        CRITIC_SYSTEM,
                        _critic_prompt(ctx, draft),
                        json_mode=True,
                        max_tokens=600,
                        temperature=0.2,
                    )
                    critique = _parse_json(critique_text)
                except Exception as exc:
                    logger.warning("Critic failed: %s", exc)
                    critique = {'needs_revision': False, 'issues': [], 'score': 7}

                critic_payload = {
                    'enabled': True,
                    'provider': self.critic.provider_name,
                    'critique': critique,
                }

                if critique.get('needs_revision') and critique.get('issues'):
                    try:
                        revised_text = self.llm.generate(
                            SYNTH_SYSTEM,
                            _resynth_prompt(draft, critique['issues'], synth_user),
                            json_mode=True,
                            max_tokens=2200,
                            temperature=0.45,
                        )
                        revised = _parse_json(revised_text)
                        if isinstance(revised, dict) and revised:
                            draft = revised
                            critic_payload['revised'] = True
                    except Exception as exc:
                        logger.warning("Re-synthesis failed: %s", exc)
                t.add_data(critic_payload)

        # Step 6 — persist
        elapsed_ms = int((time.time() - started) * 1000)
        with tracer.step(6, "Persist Recommendation") as t:
            recommendations = {
                'summary': draft.get('summary', ''),
                'immediate_actions': draft.get('immediate_actions', []),
                'long_term_strategies': draft.get('long_term_strategies', []),
                'policy_recommendations': draft.get('policy_recommendations', []),
                'monitoring_metrics': draft.get('monitoring_metrics', []),
                'risk_factors': draft.get('risk_factors', []),
            }
            retrieved_context = {
                'policies': policies,
                'news': news,
                'web': web_results,
            }
            rec = Recommendation.objects.create(
                area_id=area_id,
                area_name=area_name,
                sector=sector,
                coordinates=coordinates or {},
                content_json=recommendations,
                retrieved_context=retrieved_context,
                model_used=self.llm.model_name,
                provider=self.llm.provider_name,
                generation_ms=elapsed_ms,
            )
            t.add_data({'recommendation_id': str(rec.id), 'generation_ms': elapsed_ms})

        result = {
            'success': True,
            'recommendation_id': str(rec.id),
            'query': {
                'area_name': area_name,
                'area_id': area_id,
                'sector': sector,
                'coordinates': coordinates,
            },
            'recommendations': recommendations,
            'confidence': self._confidence(ctx, critic_payload, len(policies)),
            'retrieved_context': {
                'policy_titles': [
                    (p.get('metadata') or {}).get('document_title') for p in policies
                ],
                'news_titles': [
                    (n.get('metadata') or {}).get('document_title') for n in news
                ],
                'web_titles': [
                    (w.get('metadata') or {}).get('document_title') for w in web_results
                ],
            },
            'critic': critic_payload,
            'generated_at': datetime.now(timezone.utc).isoformat(),
        }
        if trace:
            result['pipeline_trace'] = tracer.get_trace()
        return result

    # ------------------------------------------------------------------ #
    # Internals
    # ------------------------------------------------------------------ #

    def _plan(self, ctx: Dict[str, Any]) -> Dict[str, str]:
        try:
            text = self.llm.generate(
                PLANNER_SYSTEM,
                _planner_prompt(ctx),
                json_mode=True,
                max_tokens=400,
                temperature=0.2,
            )
            data = _parse_json(text)
            return {
                'policy_query': data.get('policy_query') or '',
                'news_query': data.get('news_query') or '',
                'web_query': data.get('web_query') or self._fallback_web_query(ctx),
            }
        except Exception as exc:
            logger.warning("Planner LLM call failed, using fallback: %s", exc)
            return {
                'policy_query': '',
                'news_query': '',
                'web_query': self._fallback_web_query(ctx),
            }

    def _fallback_web_query(self, ctx: Dict[str, Any]) -> str:
        sector = ctx.get('sector') or ''
        risks = ' '.join((ctx.get('risk_flags') or [])[:2])
        return f"{ctx.get('area_name', '')} Lahore Pakistan {sector} emission reduction 2026 {risks}".strip()

    def _safe(self, fn):
        try:
            return fn()
        except Exception as exc:
            logger.warning("Tool call failed: %s", exc)
            return None

    def _confidence(self, ctx: Dict[str, Any], critic_payload: Dict[str, Any],
                    policy_count: int) -> Dict[str, float]:
        sectors_present = sum([
            bool(ctx.get('transport')),
            bool(ctx.get('buildings')),
            bool(ctx.get('waste')),
        ])
        data_completeness = min(1.0, sectors_present / 3.0)
        evidence_strength = 0.5 + min(0.5, policy_count * 0.1)
        critic_score = critic_payload.get('critique', {}).get('score') if critic_payload.get('enabled') else 8
        try:
            critic_score = int(critic_score)
        except (TypeError, ValueError):
            critic_score = 7
        overall = 0.6 * (critic_score / 10.0) + 0.2 * evidence_strength + 0.2 * data_completeness
        return {
            'overall': round(min(0.99, max(0.3, overall)), 2),
            'evidence_strength': round(evidence_strength, 2),
            'data_completeness': round(data_completeness, 2),
            'geographic_relevance': 0.95,
        }
