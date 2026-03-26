"""
ResponseFormatter — builds recommendations from templates + data, validates,
and computes confidence scores.  No LLM required for the core output.
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

# ---------------------------------------------------------------------------
# Sector-specific recommendation templates
# Placeholders: {area_name}, {sector}, {total}, {sector_value}, {sector_pct}
# ---------------------------------------------------------------------------

SECTOR_TEMPLATES = {
    'transport': {
        'immediate_actions': [
            '**Anti-Idling Campaign at Major Intersections** - [Expected Impact]: Reduce roadside CO2 by 8-12% in {area_name} - [Estimated Cost Range]: PKR 5-10 Million for signage and enforcement - [Implementation Priority]: High',
            '**CNG/Electric Rickshaw Transition Program** - [Expected Impact]: Cut per-trip emissions by 40% for 3-wheelers - [Estimated Cost Range]: PKR 20-30 Million subsidy program - [Implementation Priority]: High',
            '**Congestion Pricing Pilot Zone** - [Expected Impact]: Reduce peak traffic volume 15-20% in {area_name} - [Estimated Cost Range]: PKR 50-80 Million infrastructure setup - [Implementation Priority]: Medium',
            '**Public Transit Frequency Boost** - [Expected Impact]: Shift 10-15% of private vehicle trips to transit - [Estimated Cost Range]: PKR 30-50 Million for additional fleet - [Implementation Priority]: High',
        ],
        'long_term_strategies': [
            '**BRT/Metro Network Expansion** - [Timeline]: 3-5 years - [Expected Reduction]: 20-30% in transport emissions - [Key Milestones]: Year 1: Route planning and environmental assessment. Year 2: Construction begins. Year 3-5: Phased opening of new lines.',
            '**Electric Bus Fleet Procurement** - [Timeline]: 2-4 years - [Expected Reduction]: 15-25% per route converted - [Key Milestones]: Year 1: Pilot with 20 e-buses. Year 2: Charging infrastructure. Year 3-4: Scale to 200+ buses.',
            '**Non-Motorized Transport Infrastructure** - [Timeline]: 2-5 years - [Expected Reduction]: 5-10% from mode shift - [Key Milestones]: Year 1: Protected bike lanes on 3 corridors. Year 2: Bike-sharing program. Year 3-5: Connected cycling network.',
        ],
        'monitoring_metrics': [
            '**Average Traffic Speed**: Track changes in peak-hour vehicle speeds across {area_name} corridors as proxy for congestion reduction',
            '**Public Transit Ridership**: Monthly passenger counts on BRT and feeder routes serving {area_name}',
            '**Vehicle Fleet Composition**: Quarterly survey of CNG/electric vs diesel/petrol vehicle ratios in the area',
        ],
        'risk_factors': [
            '**Rapid Motorization**: Pakistan\'s vehicle fleet grows 10-15% annually — modal shift programs must outpace new registrations to achieve net reductions',
            '**Fuel Subsidy Dependence**: Any increase in fuel prices faces political resistance, making economic incentives for clean vehicles more practical than punitive measures',
            '**Infrastructure Gaps**: Lahore\'s road network may not support dedicated bus/cycle lanes without impacting existing traffic flow — phased implementation with traffic modeling is essential',
        ],
    },
    'industry': {
        'immediate_actions': [
            '**Energy Audit Program for Major Emitters** - [Expected Impact]: Identify 15-25% energy savings potential in {area_name} industrial units - [Estimated Cost Range]: PKR 2-5 Million for audit team - [Implementation Priority]: High',
            '**Brick Kiln Zigzag Technology Conversion** - [Expected Impact]: Reduce per-kiln emissions by 40-60% - [Estimated Cost Range]: PKR 8-12 Million per kiln retrofit - [Implementation Priority]: High',
            '**Industrial Waste Heat Recovery** - [Expected Impact]: Recover 10-20% of thermal energy in manufacturing - [Estimated Cost Range]: PKR 15-30 Million for heat exchangers - [Implementation Priority]: Medium',
            '**Fuel Switching to Natural Gas** - [Expected Impact]: Reduce CO2 intensity by 30-40% per unit energy - [Estimated Cost Range]: PKR 10-20 Million for pipeline connections - [Implementation Priority]: High',
        ],
        'long_term_strategies': [
            '**Industrial Cluster Decarbonization** - [Timeline]: 3-5 years - [Expected Reduction]: 25-35% in industrial emissions - [Key Milestones]: Year 1: Baseline assessment of all units. Year 2: Shared clean energy infrastructure. Year 3-5: Full cluster conversion.',
            '**Circular Economy Integration** - [Timeline]: 2-5 years - [Expected Reduction]: 15-20% through waste reduction - [Key Milestones]: Year 1: Industrial symbiosis mapping. Year 2: By-product exchange platform. Year 3-5: Zero-waste industrial zones.',
            '**Clean Technology Adoption Fund** - [Timeline]: 1-4 years - [Expected Reduction]: 20-30% for participating units - [Key Milestones]: Year 1: Fund setup with PKR 500M. Year 2: First grants disbursed. Year 3-4: Scale to 100+ beneficiaries.',
        ],
        'monitoring_metrics': [
            '**Industrial Energy Intensity**: kWh and fuel consumed per unit of output across {area_name} industrial facilities',
            '**Stack Emission Levels**: SO2, NOx, and particulate readings from continuous monitoring systems',
            '**Technology Adoption Rate**: Percentage of units that have adopted clean technology or efficiency upgrades',
        ],
        'risk_factors': [
            '**Competitiveness Concerns**: Stricter emission standards may increase production costs — phased implementation with SME support packages can mitigate industry resistance',
            '**Informal Sector Challenges**: Unregistered industrial activity in {area_name} makes enforcement difficult — incentive-based approaches may work better than regulation alone',
            '**Energy Supply Reliability**: Clean technology adoption depends on reliable electricity and gas — backup and distributed generation should be part of the transition plan',
        ],
    },
    'energy': {
        'immediate_actions': [
            '**Rooftop Solar Installation Drive** - [Expected Impact]: Offset 20-30% of grid electricity for participating buildings in {area_name} - [Estimated Cost Range]: PKR 15-25 Million for 1MW community program - [Implementation Priority]: High',
            '**LED Street Lighting Conversion** - [Expected Impact]: Reduce public lighting energy use by 60-70% - [Estimated Cost Range]: PKR 8-15 Million for {area_name} coverage - [Implementation Priority]: High',
            '**Net Metering Awareness Campaign** - [Expected Impact]: Increase distributed solar adoption by 30-40% - [Estimated Cost Range]: PKR 2-5 Million for outreach - [Implementation Priority]: Medium',
            '**Power Factor Correction for Commercial Buildings** - [Expected Impact]: Reduce grid losses by 5-10% - [Estimated Cost Range]: PKR 3-8 Million for capacitor banks - [Implementation Priority]: Medium',
        ],
        'long_term_strategies': [
            '**Community Solar Farm Development** - [Timeline]: 2-4 years - [Expected Reduction]: 25-35% grid dependence for {area_name} - [Key Milestones]: Year 1: Site selection and grid study. Year 2: Install 5MW facility. Year 3-4: Expand to 15MW with storage.',
            '**Smart Grid and Demand Response** - [Timeline]: 3-5 years - [Expected Reduction]: 15-20% peak demand reduction - [Key Milestones]: Year 1: Smart meter deployment. Year 2: Demand response pilot. Year 3-5: AI-driven load optimization.',
            '**Building Energy Efficiency Retrofit Program** - [Timeline]: 2-5 years - [Expected Reduction]: 20-30% energy consumption in retrofitted buildings - [Key Milestones]: Year 1: Audit 100 largest consumers. Year 2: Retrofit 25 buildings. Year 3-5: Scale to 200+.',
        ],
        'monitoring_metrics': [
            '**Grid Electricity Consumption**: Monthly kWh consumed from grid vs distributed generation in {area_name}',
            '**Solar Capacity Installed**: Cumulative MW of rooftop and community solar within the area',
            '**Peak Demand Reduction**: Percentage decrease in peak electricity demand during summer months',
        ],
        'risk_factors': [
            '**Grid Infrastructure Limitations**: Lahore\'s distribution network may not support high solar penetration without upgrades — grid reinforcement must precede large-scale generation',
            '**Upfront Cost Barrier**: Solar and efficiency investments require capital that many residents lack — green loans and on-bill financing are critical enablers',
            '**Policy Uncertainty**: Changes in net metering rates or renewable energy incentives could slow adoption — stable, long-term policy signals are needed',
        ],
    },
    'waste': {
        'immediate_actions': [
            '**Source Segregation Pilot Program** - [Expected Impact]: Divert 30-40% of organic waste from landfill in {area_name} - [Estimated Cost Range]: PKR 10-20 Million for bins, collection, awareness - [Implementation Priority]: High',
            '**Composting Facility for Organic Waste** - [Expected Impact]: Reduce methane emissions by converting 50% of organic waste - [Estimated Cost Range]: PKR 25-40 Million for community-scale facility - [Implementation Priority]: High',
            '**Informal Recycler Integration Program** - [Expected Impact]: Increase recycling rates by 20-30% through formal partnerships - [Estimated Cost Range]: PKR 5-10 Million for cooperative formation - [Implementation Priority]: Medium',
            '**Anti-Open-Burning Enforcement** - [Expected Impact]: Eliminate 80-90% of open waste burning incidents in {area_name} - [Estimated Cost Range]: PKR 3-5 Million for monitoring - [Implementation Priority]: High',
        ],
        'long_term_strategies': [
            '**Waste-to-Energy Facility** - [Timeline]: 3-5 years - [Expected Reduction]: 40-50% of landfill methane eliminated - [Key Milestones]: Year 1: Feasibility study and site selection. Year 2: EIA and financing. Year 3-5: Construction and commissioning.',
            '**City-Wide Zero Waste Program** - [Timeline]: 3-5 years - [Expected Reduction]: 50-60% waste diversion from landfill - [Key Milestones]: Year 1: Ward-level segregation rollout. Year 2: Materials recovery facility. Year 3-5: Extended producer responsibility.',
            '**Landfill Gas Capture System** - [Timeline]: 2-4 years - [Expected Reduction]: 60-70% of existing landfill methane - [Key Milestones]: Year 1: Gas well installation. Year 2: Collection operational. Year 3-4: Power generation from captured gas.',
        ],
        'monitoring_metrics': [
            '**Landfill Diversion Rate**: Percentage of total waste diverted through recycling, composting, and reuse in {area_name}',
            '**Methane Emission Levels**: CH4 concentration measurements at landfill boundaries and dump sites',
            '**Open Burning Incidents**: Monthly count of reported waste burning events in the area',
        ],
        'risk_factors': [
            '**Behavioral Change Resistance**: Source segregation requires sustained community engagement — pilot programs with visible benefits build momentum better than top-down mandates',
            '**Informal Sector Disruption**: Formalizing waste management must include existing waste pickers — exclusion leads to both social harm and reduced collection efficiency',
            '**Financing Gaps**: Waste infrastructure requires significant upfront investment — public-private partnerships and carbon credit revenues can bridge the gap',
        ],
    },
    'buildings': {
        'immediate_actions': [
            '**Building Energy Audit Campaign** - [Expected Impact]: Identify 20-35% energy savings in commercial buildings in {area_name} - [Estimated Cost Range]: PKR 3-8 Million for audit team - [Implementation Priority]: High',
            '**Cool Roof Initiative** - [Expected Impact]: Reduce cooling energy demand by 20-30% in treated buildings - [Estimated Cost Range]: PKR 5-12 Million for reflective coating program - [Implementation Priority]: High',
            '**HVAC Efficiency Upgrade Incentive** - [Expected Impact]: Cut cooling/heating energy by 25-40% per upgraded system - [Estimated Cost Range]: PKR 15-25 Million rebate program - [Implementation Priority]: Medium',
            '**Window Film and Insulation Retrofit** - [Expected Impact]: Reduce heat gain by 30-40% in older buildings - [Estimated Cost Range]: PKR 8-15 Million for targeted commercial buildings - [Implementation Priority]: Medium',
        ],
        'long_term_strategies': [
            '**Green Building Code Adoption** - [Timeline]: 2-4 years - [Expected Reduction]: 30-40% energy reduction in new construction - [Key Milestones]: Year 1: Code development with stakeholders. Year 2: Voluntary adoption. Year 3-4: Mandatory for all new commercial.',
            '**District Cooling System** - [Timeline]: 3-5 years - [Expected Reduction]: 35-45% cooling energy reduction for connected buildings - [Key Milestones]: Year 1: Demand assessment for {area_name}. Year 2: Central plant design. Year 3-5: Phased building connections.',
            '**Net-Zero Building Demonstration Projects** - [Timeline]: 2-4 years - [Expected Reduction]: 80-100% operational emissions for demo buildings - [Key Milestones]: Year 1: Design competition. Year 2: Build 3 demo buildings. Year 3-4: Replication framework.',
        ],
        'monitoring_metrics': [
            '**Building Energy Use Intensity**: kWh per square meter per year for commercial and residential buildings in {area_name}',
            '**Green Building Certifications**: Number of buildings with certified green/energy-efficient ratings',
            '**Cooling Degree Days vs Energy Use**: Correlation tracking between temperature and consumption to measure efficiency gains',
        ],
        'risk_factors': [
            '**Split Incentive Problem**: Building owners bear retrofit costs while tenants benefit from lower bills — green lease frameworks and shared-savings models can align incentives',
            '**Construction Capacity**: Local contractors may lack experience with green building techniques — training programs and technology transfer partnerships are essential',
            '**Urban Heat Island Effect**: Lahore\'s rising temperatures increase cooling demand faster than efficiency gains — passive cooling and green infrastructure must complement mechanical solutions',
        ],
    },
}


class ResponseFormatter:
    """Builds recommendations from templates + data, validates, and caches."""

    # ------------------------------------------------------------------ #
    # Template-based builder (NO LLM needed)
    # ------------------------------------------------------------------ #

    def build_from_template(self, area_name, area_id, sector, coordinates,
                            policy_results, emissions_analysis):
        """Build full recommendations from data + templates without any LLM.

        Returns:
            Dict matching the RecommendationsResponse interface.
        """
        total = emissions_analysis.get('total_emissions', 0)
        sector_totals = emissions_analysis.get('sector_totals', {})
        sector_value = sector_totals.get(sector, 0)
        sector_pct = (sector_value / total * 100) if total > 0 else 0

        params = {
            'area_name': area_name,
            'sector': sector,
            'total': f'{total:.0f}',
            'sector_value': f'{sector_value:.0f}',
            'sector_pct': f'{sector_pct:.0f}',
        }

        templates = SECTOR_TEMPLATES.get(sector, SECTOR_TEMPLATES['energy'])

        summary = self._build_summary(
            area_name, sector, total, sector_value, sector_pct,
            emissions_analysis, policy_results,
        )

        recommendations = {
            'summary': summary,
            'immediate_actions': [t.format(**params) for t in templates['immediate_actions']],
            'long_term_strategies': [t.format(**params) for t in templates['long_term_strategies']],
            'policy_recommendations': self._build_policy_recs(policy_results, area_name, sector),
            'monitoring_metrics': [t.format(**params) for t in templates['monitoring_metrics']],
            'risk_factors': [t.format(**params) for t in templates['risk_factors']],
        }

        confidence = self._compute_confidence(policy_results, emissions_analysis)

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
            'raw_response': 'template_generated',
            'generated_at': datetime.utcnow().isoformat() + 'Z',
        }

        self._cache_result(result, area_id, sector, confidence,
                           policy_results, emissions_analysis)

        return result

    def _build_summary(self, area_name, sector, total, sector_value, sector_pct,
                       emissions_analysis, policy_results):
        """Build a data-driven summary paragraph."""
        trend = emissions_analysis.get('trend_direction', 'stable')
        trend_pct = emissions_analysis.get('trend_percentage', 0)
        forecast = emissions_analysis.get('forecast_direction', 'stable')

        trend_desc = {
            'increasing': f'emissions are rising ({trend_pct:+.1f}% year-over-year)',
            'decreasing': f'emissions are declining ({trend_pct:+.1f}% year-over-year)',
            'stable': 'emissions have remained relatively stable',
        }.get(trend, 'emissions trend data is limited')

        forecast_desc = {
            'increasing': 'projected to continue rising without intervention',
            'decreasing': 'projected to decline with current measures',
            'stable': 'projected to remain at current levels',
            'no_forecast': 'with limited forecast data available',
        }.get(forecast, '')

        policy_mention = ''
        if policy_results:
            titles = [
                r['metadata'].get('document_title', '')
                for r in policy_results[:3]
                if r['metadata'].get('document_title')
            ]
            if titles:
                policy_mention = f' Relevant policy frameworks include {", ".join(titles)}.'

        return (
            f"{area_name}'s {sector} sector accounts for {sector_pct:.0f}% "
            f"({sector_value:.0f}t CO2e) of total area emissions ({total:.0f}t CO2e). "
            f"Analysis shows {trend_desc}, and emissions are {forecast_desc}. "
            f"Immediate action is needed to address key emission drivers in this sector."
            f"{policy_mention} "
            f"The following recommendations are tailored to {area_name}'s context in "
            f"Lahore, Pakistan, combining quick-win interventions with long-term changes."
        )

    def _build_policy_recs(self, policy_results, area_name, sector):
        """Build policy recommendations from retrieved documents."""
        if not policy_results:
            return [
                f'**National Climate Policy Alignment**: Align local {sector} measures '
                f'with Pakistan\'s Updated NDC targets and NCCP framework',
                f'**Provincial Coordination**: Coordinate with Punjab EPA on {sector} '
                f'emission standards and enforcement mechanisms',
                f'**International Best Practices**: Adopt proven {sector} decarbonization '
                f'strategies from comparable South Asian cities',
            ]

        recs = []
        for r in policy_results[:3]:
            title = r['metadata'].get('document_title', 'Policy Framework')
            snippet = r['text'][:150].strip()
            last_period = snippet.rfind('.')
            if last_period > 40:
                snippet = snippet[:last_period + 1]
            recs.append(f'**{title}**: {snippet}')

        recs.append(
            f'**Local Implementation Framework**: Develop {area_name}-specific '
            f'{sector} emission targets aligned with retrieved policy frameworks'
        )

        return recs[:4]

    # ------------------------------------------------------------------ #
    # Legacy LLM-based format (kept for compatibility)
    # ------------------------------------------------------------------ #

    def format(self, raw_response, area_name, area_id, sector, coordinates,
               policy_results, emissions_analysis=None):
        """Parse, validate, compute confidence, and cache an LLM response."""
        recommendations = self._parse_response(raw_response)

        confidence = self._compute_confidence(
            policy_results, emissions_analysis or {}
        )

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

        self._cache_result(result, area_id, sector, confidence, policy_results,
                           emissions_analysis)

        return result

    def _parse_response(self, raw_response):
        """Parse the LLM response string into a structured dict."""
        text = raw_response.strip()

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
            start = text.find('{')
            end = text.rfind('}')
            if start != -1 and end != -1:
                try:
                    data = json.loads(text[start:end + 1])
                except json.JSONDecodeError:
                    data = {}
            else:
                data = {}

        recommendations = {
            'summary': data.get('summary', 'Unable to generate analysis summary.'),
            'immediate_actions': data.get('immediate_actions', []),
            'long_term_strategies': data.get('long_term_strategies', []),
            'policy_recommendations': data.get('policy_recommendations', []),
            'monitoring_metrics': data.get('monitoring_metrics', []),
            'risk_factors': data.get('risk_factors', []),
        }

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

    # ------------------------------------------------------------------ #
    # Confidence scoring
    # ------------------------------------------------------------------ #

    def _compute_confidence(self, policy_results, emissions_analysis):
        """Compute confidence scores for the recommendations."""
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

        hist_count = emissions_analysis.get('historical_count', 0)
        forecast_count = emissions_analysis.get('forecast_count', 0)
        has_historical = 1.0 if hist_count > 12 else (hist_count / 12.0)
        has_forecast = 1.0 if forecast_count > 0 else 0.0

        sector_totals = emissions_analysis.get('sector_totals', {})
        sectors_with_data = sum(1 for s in SECTORS if sector_totals.get(s, 0) > 0)
        has_all_sectors = sectors_with_data / 5.0

        data_score = has_historical * 0.4 + has_forecast * 0.3 + has_all_sectors * 0.3

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

        overall = evidence_score * 0.4 + data_score * 0.35 + geo_score * 0.25

        return {
            'overall': round(overall, 2),
            'evidence_strength': round(evidence_score, 2),
            'data_completeness': round(data_score, 2),
            'geographic_relevance': round(geo_score, 2),
        }

    # ------------------------------------------------------------------ #
    # Caching
    # ------------------------------------------------------------------ #

    def _cache_result(self, result, area_id, sector, confidence, policy_results,
                      emissions_analysis):
        """Cache the recommendation result in the database."""
        try:
            ttl_hours = getattr(settings, 'RECOMMENDATION_CACHE_TTL_HOURS', 24)
            expires_at = timezone.now() + timedelta(hours=ttl_hours)

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
            pass
