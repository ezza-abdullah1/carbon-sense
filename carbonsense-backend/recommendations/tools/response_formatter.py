"""
ResponseFormatter — validates LLM output and computes confidence scores.
"""

import json
import hashlib
from datetime import datetime, timedelta
from django.utils import timezone
from django.conf import settings

from recommendations.models import RecommendationCache

SECTORS = ['transport', 'industry', 'energy', 'waste', 'buildings']

REQUIRED_FIELDS = [
    'summary',
    'immediate_actions',
    'long_term_strategies',
    'policy_recommendations',
    'monitoring_metrics',
    'risk_factors',
]


class ResponseFormatter:
    """Validates, formats, and caches recommendation responses."""

    def format(self, raw_response, area_name, area_id, sector, coordinates,
               policy_results, emissions_analysis=None):
        """Parse, validate, compute confidence, and cache the response.

        Args:
            raw_response: Raw string response from the LLM.
            area_name: Name of the area.
            area_id: ID of the area.
            sector: Target sector.
            coordinates: Dict with lat/lng.
            policy_results: List of retrieved policy chunks (from PolicyRetriever).
            emissions_analysis: Dict from EmissionsAnalyzer (optional, for confidence).

        Returns:
            Dict matching the RecommendationsResponse interface.
        """
        # Parse JSON from LLM response
        recommendations = self._parse_response(raw_response)

        # Compute confidence scores
        confidence = self._compute_confidence(
            policy_results, emissions_analysis or {}
        )

        # Build the full response
        result = {
            'success': True,
            'query': {
                'area_name': area_name,
                'area_id': area_id,
                'sector': sector,
                'coordinates': coordinates,
            },
            'recommendations': recommendations,
            'confidence': confidence,
            'raw_response': raw_response,
            'generated_at': datetime.utcnow().isoformat() + 'Z',
        }

        # Cache the result
        self._cache_result(result, area_id, sector, confidence, policy_results,
                           emissions_analysis)

        return result

    def _parse_response(self, raw_response):
        """Parse the LLM response string into a structured dict."""
        # Try to extract JSON from the response
        text = raw_response.strip()

        # Remove markdown code fences if present
        if text.startswith('```json'):
            text = text[7:]
        elif text.startswith('```'):
            text = text[3:]
        if text.endswith('```'):
            text = text[:-3]
        text = text.strip()

        try:
            data = json.loads(text)
        except json.JSONDecodeError:
            # Try to find JSON object in the response
            start = text.find('{')
            end = text.rfind('}')
            if start != -1 and end != -1:
                try:
                    data = json.loads(text[start:end + 1])
                except json.JSONDecodeError:
                    data = {}
            else:
                data = {}

        # Ensure all required fields exist with defaults
        recommendations = {
            'summary': data.get('summary', 'Unable to generate analysis summary.'),
            'immediate_actions': data.get('immediate_actions', []),
            'long_term_strategies': data.get('long_term_strategies', []),
            'policy_recommendations': data.get('policy_recommendations', []),
            'monitoring_metrics': data.get('monitoring_metrics', []),
            'risk_factors': data.get('risk_factors', []),
        }

        # Ensure all list fields are actually lists of strings
        for field in REQUIRED_FIELDS:
            if field == 'summary':
                if not isinstance(recommendations[field], str):
                    recommendations[field] = str(recommendations[field])
            else:
                if not isinstance(recommendations[field], list):
                    recommendations[field] = []
                recommendations[field] = [
                    str(item) for item in recommendations[field]
                ]

        return recommendations

    def _compute_confidence(self, policy_results, emissions_analysis):
        """Compute confidence scores for the recommendations.

        Returns:
            Dict with overall, evidence_strength, data_completeness,
            geographic_relevance scores (each 0-1).
        """
        # Factor 1: Evidence strength (quality of retrieved documents)
        if not policy_results:
            evidence_score = 0.2
        else:
            avg_relevance = sum(r.get('score', 0) for r in policy_results) / len(policy_results)
            pakistan_count = sum(
                1 for r in policy_results
                if r.get('metadata', {}).get('country', '').lower() == 'pakistan'
            )
            pakistan_ratio = pakistan_count / len(policy_results) if policy_results else 0
            evidence_score = min(1.0, avg_relevance * 0.6 + pakistan_ratio * 0.4)

        # Factor 2: Data completeness (emissions data quality)
        hist_count = emissions_analysis.get('historical_count', 0)
        forecast_count = emissions_analysis.get('forecast_count', 0)
        has_historical = 1.0 if hist_count > 12 else (hist_count / 12.0)
        has_forecast = 1.0 if forecast_count > 0 else 0.0

        sector_totals = emissions_analysis.get('sector_totals', {})
        sectors_with_data = sum(1 for s in SECTORS if sector_totals.get(s, 0) > 0)
        has_all_sectors = sectors_with_data / 5.0

        data_score = has_historical * 0.4 + has_forecast * 0.3 + has_all_sectors * 0.3

        # Factor 3: Geographic relevance
        if not policy_results:
            geo_score = 0.1
        else:
            lahore_docs = sum(
                1 for r in policy_results
                if 'lahore' in r.get('metadata', {}).get('city', '').lower()
            )
            pakistan_docs = sum(
                1 for r in policy_results
                if r.get('metadata', {}).get('country', '').lower() == 'pakistan'
            )
            geo_score = min(1.0, lahore_docs * 0.3 + pakistan_docs * 0.1)

        # Overall weighted score
        overall = evidence_score * 0.4 + data_score * 0.35 + geo_score * 0.25

        return {
            'overall': round(overall, 2),
            'evidence_strength': round(evidence_score, 2),
            'data_completeness': round(data_score, 2),
            'geographic_relevance': round(geo_score, 2),
        }

    def _cache_result(self, result, area_id, sector, confidence, policy_results,
                      emissions_analysis):
        """Cache the recommendation result in the database."""
        try:
            ttl_hours = getattr(settings, 'RECOMMENDATION_CACHE_TTL_HOURS', 24)
            expires_at = timezone.now() + timedelta(hours=ttl_hours)

            # Compute emissions data hash for cache invalidation
            data_hash = ''
            if emissions_analysis:
                hash_input = json.dumps(
                    emissions_analysis.get('sector_totals', {}), sort_keys=True
                )
                data_hash = hashlib.sha256(hash_input.encode()).hexdigest()[:16]

            RecommendationCache.objects.update_or_create(
                area_id=area_id,
                sector=sector,
                defaults={
                    'response_data': result,
                    'confidence_scores': confidence,
                    'expires_at': expires_at,
                    'policy_doc_count': len(policy_results) if policy_results else 0,
                    'emissions_data_hash': data_hash,
                }
            )
        except Exception:
            # Caching failure should not break the response
            pass
