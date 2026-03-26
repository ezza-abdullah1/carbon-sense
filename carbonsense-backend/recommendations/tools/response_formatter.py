"""
ResponseFormatter — builds recommendations from templates + data, validates,
and computes confidence scores.  No LLM required for the core output.

Templates are parameterized with actual emission values, trends, and area names
so each area gets unique, data-driven recommendations.
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
#
# Placeholders filled from actual emissions data:
#   {area_name}   — e.g. "Gulberg"
#   {sector}      — e.g. "transport"
#   {total}       — total emissions in tonnes, e.g. "140498"
#   {sector_value}— this sector's emissions in tonnes, e.g. "38200"
#   {sector_pct}  — this sector's share as %, e.g. "27"
#   {trend}       — "increasing" / "decreasing" / "stable"
#   {trend_pct}   — absolute trend %, e.g. "73.8"
#   {urgency}     — "Critical" / "High" / "Moderate" / "Improving"
#   {monthly_avg} — monthly average emissions for this sector
# ---------------------------------------------------------------------------

SECTOR_TEMPLATES = {
    'transport': {
        'immediate_actions': [
            '**Anti-Idling Enforcement in {area_name}** - [Expected Impact]: Reduce {area_name}\'s {sector_value}t annual transport CO2 by 8-12% at major intersections - [Estimated Cost Range]: PKR 5-10 Million for signage and enforcement - [Implementation Priority]: {urgency}',
            '**CNG/Electric Rickshaw Transition** - [Expected Impact]: Cut per-trip emissions by 40% for 3-wheelers operating in {area_name} - [Estimated Cost Range]: PKR 20-30 Million subsidy program - [Implementation Priority]: High',
            '**Congestion Pricing Pilot for {area_name}** - [Expected Impact]: Reduce peak traffic volume 15-20% targeting {sector_value}t annual emissions - [Estimated Cost Range]: PKR 50-80 Million infrastructure setup - [Implementation Priority]: {priority_medium}',
            '**Public Transit Frequency Boost** - [Expected Impact]: Shift 10-15% of {area_name} private vehicle trips to transit - [Estimated Cost Range]: PKR 30-50 Million for additional fleet - [Implementation Priority]: {urgency}',
        ],
        'long_term_strategies': [
            '**BRT/Metro Extension to {area_name}** - [Timeline]: 3-5 years - [Expected Reduction]: 20-30% of {area_name}\'s {sector_value}t transport emissions - [Key Milestones]: Year 1: Route planning and {area_name} corridor assessment. Year 2: Construction begins. Year 3-5: Phased opening.',
            '**Electric Bus Fleet for {area_name} Routes** - [Timeline]: 2-4 years - [Expected Reduction]: 15-25% per route converted - [Key Milestones]: Year 1: Pilot 20 e-buses on {area_name} routes. Year 2: Charging infrastructure. Year 3-4: Scale to 200+ buses.',
            '**Non-Motorized Transport in {area_name}** - [Timeline]: 2-5 years - [Expected Reduction]: 5-10% from mode shift - [Key Milestones]: Year 1: Protected bike lanes in {area_name}. Year 2: Bike-sharing stations. Year 3-5: Connected network.',
        ],
        'monitoring_metrics': [
            '**{area_name} Traffic Speed Index**: Track peak-hour vehicle speeds across {area_name} corridors — target 15% improvement from current baseline',
            '**Transit Ridership for {area_name}**: Monthly passenger counts on BRT/feeder routes — current transport emissions {sector_value}t need 20% modal shift',
            '**Fleet Electrification Rate**: Quarterly CNG/electric vs diesel vehicle ratio surveys in {area_name} — track against {trend} emission trend',
        ],
        'risk_factors': [
            '**Rapid Motorization**: With {area_name}\'s transport emissions at {sector_value}t ({trend} {trend_pct}% YoY), modal shift programs must outpace 10-15% annual vehicle fleet growth',
            '**Fuel Subsidy Dependence**: Political resistance to fuel pricing makes economic incentives for clean vehicles more practical for {area_name}',
            '**Infrastructure Constraints**: {area_name}\'s road network may not support dedicated bus/cycle lanes — phased implementation with traffic modeling is essential',
        ],
    },
    'industry': {
        'immediate_actions': [
            '**Energy Audit for {area_name} Industrial Units** - [Expected Impact]: Identify 15-25% savings from {area_name}\'s {sector_value}t industrial emissions - [Estimated Cost Range]: PKR 2-5 Million for audit team - [Implementation Priority]: {urgency}',
            '**Brick Kiln Zigzag Technology Conversion** - [Expected Impact]: Reduce per-kiln emissions by 40-60% for kilns near {area_name} - [Estimated Cost Range]: PKR 8-12 Million per kiln retrofit - [Implementation Priority]: High',
            '**Waste Heat Recovery for {area_name} Factories** - [Expected Impact]: Recover 10-20% of thermal energy from {sector_value}t emission base - [Estimated Cost Range]: PKR 15-30 Million for heat exchangers - [Implementation Priority]: {priority_medium}',
            '**Fuel Switching to Natural Gas** - [Expected Impact]: Reduce CO2 intensity by 30-40% per unit energy in {area_name} industrial zone - [Estimated Cost Range]: PKR 10-20 Million for pipeline connections - [Implementation Priority]: {urgency}',
        ],
        'long_term_strategies': [
            '**{area_name} Industrial Cluster Decarbonization** - [Timeline]: 3-5 years - [Expected Reduction]: 25-35% of {sector_value}t industrial emissions - [Key Milestones]: Year 1: Baseline assessment of {area_name} units. Year 2: Shared clean energy infrastructure. Year 3-5: Full cluster conversion.',
            '**Circular Economy for {area_name}** - [Timeline]: 2-5 years - [Expected Reduction]: 15-20% through waste reduction - [Key Milestones]: Year 1: Industrial symbiosis mapping in {area_name}. Year 2: By-product exchange platform. Year 3-5: Zero-waste zones.',
            '**Clean Technology Fund** - [Timeline]: 1-4 years - [Expected Reduction]: 20-30% for participating {area_name} units - [Key Milestones]: Year 1: Fund setup with PKR 500M. Year 2: First grants to {area_name} factories. Year 3-4: Scale to 100+ beneficiaries.',
        ],
        'monitoring_metrics': [
            '**{area_name} Industrial Energy Intensity**: kWh per unit of output — baseline from {sector_value}t total industrial emissions',
            '**Stack Emission Compliance**: SO2, NOx, and particulate readings for {area_name} industrial units vs PEQS standards',
            '**Technology Adoption Rate**: Percentage of {area_name} units with clean technology — track against {trend} ({trend_pct}% YoY) trend',
        ],
        'risk_factors': [
            '**Competitiveness Impact**: With {sector_value}t emissions ({trend} {trend_pct}% YoY), {area_name}\'s industries need phased compliance timelines with SME support packages',
            '**Informal Sector**: Unregistered industrial activity near {area_name} makes enforcement difficult — incentive-based approaches work better than regulation alone',
            '**Energy Supply Gaps**: Clean technology adoption in {area_name} depends on reliable electricity/gas — distributed generation should be part of the transition',
        ],
    },
    'energy': {
        'immediate_actions': [
            '**Rooftop Solar Drive for {area_name}** - [Expected Impact]: Offset 20-30% of grid electricity from {area_name}\'s {sector_value}t energy emissions - [Estimated Cost Range]: PKR 15-25 Million for 1MW program - [Implementation Priority]: {urgency}',
            '**LED Street Lighting in {area_name}** - [Expected Impact]: Reduce public lighting energy by 60-70% in the area - [Estimated Cost Range]: PKR 8-15 Million for {area_name} coverage - [Implementation Priority]: High',
            '**Net Metering Awareness for {area_name}** - [Expected Impact]: Increase distributed solar adoption by 30-40% - [Estimated Cost Range]: PKR 2-5 Million for outreach - [Implementation Priority]: {priority_medium}',
            '**Power Factor Correction** - [Expected Impact]: Reduce grid losses by 5-10% for {area_name} commercial buildings - [Estimated Cost Range]: PKR 3-8 Million for capacitor banks - [Implementation Priority]: {priority_medium}',
        ],
        'long_term_strategies': [
            '**{area_name} Community Solar Farm** - [Timeline]: 2-4 years - [Expected Reduction]: 25-35% of {area_name}\'s {sector_value}t energy emissions - [Key Milestones]: Year 1: Site selection near {area_name}. Year 2: Install 5MW facility. Year 3-4: Expand to 15MW with storage.',
            '**Smart Grid for {area_name}** - [Timeline]: 3-5 years - [Expected Reduction]: 15-20% peak demand reduction - [Key Milestones]: Year 1: Smart meters in {area_name}. Year 2: Demand response pilot. Year 3-5: AI-driven optimization.',
            '**Building Energy Retrofit in {area_name}** - [Timeline]: 2-5 years - [Expected Reduction]: 20-30% consumption in retrofitted buildings - [Key Milestones]: Year 1: Audit 100 largest {area_name} consumers. Year 2: Retrofit 25 buildings. Year 3-5: Scale to 200+.',
        ],
        'monitoring_metrics': [
            '**{area_name} Grid Consumption**: Monthly kWh from grid vs distributed generation — baseline {sector_value}t annual emissions',
            '**Solar Capacity in {area_name}**: Cumulative MW installed — track against {sector_value}t baseline to measure displacement',
            '**Peak Demand Trend**: {area_name} peak electricity demand — current energy trend is {trend} ({trend_pct}% YoY)',
        ],
        'risk_factors': [
            '**Grid Limitations**: With {sector_value}t energy emissions ({trend} {trend_pct}% YoY), {area_name}\'s distribution network needs upgrades before large-scale solar integration',
            '**Capital Barrier**: Solar investments require upfront capital — green loans and on-bill financing are critical for {area_name} residents and SMEs',
            '**Policy Uncertainty**: Changes in net metering rates could slow {area_name}\'s renewable adoption — stable long-term incentives are needed',
        ],
    },
    'waste': {
        'immediate_actions': [
            '**Source Segregation Pilot in {area_name}** - [Expected Impact]: Divert 30-40% of organic waste from landfill, reducing {area_name}\'s {sector_value}t waste emissions - [Estimated Cost Range]: PKR 10-20 Million for bins, collection, awareness - [Implementation Priority]: {urgency}',
            '**{area_name} Composting Facility** - [Expected Impact]: Convert 50% of organic waste, cutting methane from {sector_value}t emission base - [Estimated Cost Range]: PKR 25-40 Million for community-scale facility - [Implementation Priority]: High',
            '**Informal Recycler Integration** - [Expected Impact]: Increase {area_name} recycling rates by 20-30% through formal partnerships - [Estimated Cost Range]: PKR 5-10 Million for cooperative formation - [Implementation Priority]: {priority_medium}',
            '**Anti-Open-Burning in {area_name}** - [Expected Impact]: Eliminate 80-90% of open waste burning incidents - [Estimated Cost Range]: PKR 3-5 Million for monitoring - [Implementation Priority]: {urgency}',
        ],
        'long_term_strategies': [
            '**Waste-to-Energy for {area_name}** - [Timeline]: 3-5 years - [Expected Reduction]: 40-50% of {area_name}\'s {sector_value}t waste-sector methane - [Key Milestones]: Year 1: Feasibility study for {area_name}. Year 2: EIA and financing. Year 3-5: Construction and commissioning.',
            '**{area_name} Zero Waste Program** - [Timeline]: 3-5 years - [Expected Reduction]: 50-60% waste diversion from landfill - [Key Milestones]: Year 1: Ward-level segregation in {area_name}. Year 2: Materials recovery facility. Year 3-5: Extended producer responsibility.',
            '**Landfill Gas Capture** - [Timeline]: 2-4 years - [Expected Reduction]: 60-70% of landfill methane serving {area_name} - [Key Milestones]: Year 1: Gas well installation. Year 2: Collection operational. Year 3-4: Power generation.',
        ],
        'monitoring_metrics': [
            '**{area_name} Landfill Diversion**: Percentage of waste diverted — baseline from {sector_value}t annual waste emissions',
            '**Methane Levels near {area_name}**: CH4 measurements at nearby landfill boundaries — track against {trend} ({trend_pct}% YoY) trend',
            '**Open Burning Incidents**: Monthly count in {area_name} — target 90% reduction from current baseline',
        ],
        'risk_factors': [
            '**Behavioral Resistance**: With {area_name}\'s waste emissions at {sector_value}t ({trend} trend), community engagement through visible pilot benefits is critical',
            '**Informal Sector Impact**: Formalizing {area_name}\'s waste management must include existing waste pickers — exclusion reduces collection efficiency',
            '**Financing Gaps**: {area_name}\'s waste infrastructure needs significant investment — PPP models and carbon credit revenues can bridge the gap',
        ],
    },
    'buildings': {
        'immediate_actions': [
            '**Energy Audit for {area_name} Buildings** - [Expected Impact]: Identify 20-35% savings from {area_name}\'s {sector_value}t building emissions - [Estimated Cost Range]: PKR 3-8 Million for audit team - [Implementation Priority]: {urgency}',
            '**Cool Roof Initiative in {area_name}** - [Expected Impact]: Reduce cooling demand by 20-30% in treated buildings - [Estimated Cost Range]: PKR 5-12 Million for reflective coating program - [Implementation Priority]: High',
            '**HVAC Efficiency Upgrades** - [Expected Impact]: Cut cooling/heating energy by 25-40% per system in {area_name} - [Estimated Cost Range]: PKR 15-25 Million rebate program - [Implementation Priority]: {priority_medium}',
            '**Window Film and Insulation** - [Expected Impact]: Reduce heat gain by 30-40% in older {area_name} buildings - [Estimated Cost Range]: PKR 8-15 Million targeted program - [Implementation Priority]: {priority_medium}',
        ],
        'long_term_strategies': [
            '**Green Building Code for {area_name}** - [Timeline]: 2-4 years - [Expected Reduction]: 30-40% energy reduction in new {area_name} construction - [Key Milestones]: Year 1: Code development. Year 2: Voluntary adoption in {area_name}. Year 3-4: Mandatory for new commercial.',
            '**{area_name} District Cooling System** - [Timeline]: 3-5 years - [Expected Reduction]: 35-45% of {sector_value}t cooling-related emissions - [Key Milestones]: Year 1: Demand assessment for {area_name}. Year 2: Central plant design. Year 3-5: Phased connections.',
            '**Net-Zero Building Demos in {area_name}** - [Timeline]: 2-4 years - [Expected Reduction]: 80-100% operational emissions for demo buildings - [Key Milestones]: Year 1: Design competition. Year 2: Build 3 demos in {area_name}. Year 3-4: Replication framework.',
        ],
        'monitoring_metrics': [
            '**{area_name} Building Energy Intensity**: kWh/sqm/year for {area_name} buildings — baseline from {sector_value}t emissions',
            '**Green Certifications in {area_name}**: Number of buildings with energy-efficiency ratings — target 20% of commercial stock',
            '**Cooling vs Temperature**: {area_name} energy use correlated with cooling degree days — current trend is {trend} ({trend_pct}% YoY)',
        ],
        'risk_factors': [
            '**Split Incentive**: {area_name} building owners bear costs while tenants benefit — green lease frameworks needed to align incentives',
            '**Construction Capacity**: With {sector_value}t building emissions ({trend} trend), local contractors need green building training and technology transfer',
            '**Urban Heat Island**: Lahore\'s rising temperatures increase {area_name}\'s cooling demand — passive cooling and green infrastructure must complement mechanical solutions',
        ],
    },
}

# ---------------------------------------------------------------------------
# Real Pakistan policy frameworks per sector (used when RAG has no results)
# ---------------------------------------------------------------------------

SECTOR_POLICY_DEFAULTS = {
    'transport': [
        '**Pakistan National Electric Vehicle Policy**: Align {area_name}\'s fleet transition with the federal EV policy framework including import duty concessions and charging infrastructure mandates for Lahore',
        '**Lahore Transport Master Plan**: Implement dedicated BRT corridors and feeder routes planned for the {area_name} zone under LDA\'s transport master plan',
        '**Punjab Motor Vehicle Emission Standards**: Enforce emission testing under Punjab Environmental Protection Act for commercial vehicles operating in {area_name}',
        '**National Climate Change Policy (Transport)**: Align {area_name}\'s fuel efficiency and modal shift targets with Pakistan\'s Updated NDC commitments',
    ],
    'industry': [
        '**Punjab Environmental Quality Standards (PEQS)**: Enforce stack emission limits for industrial units in {area_name} per EPA Punjab regulations',
        '**NEECA Industrial Energy Efficiency**: Register {area_name}\'s major industrial units in the mandatory energy audit program for facilities consuming >1MW',
        '**Pakistan Climate Change Act (Industry)**: Align {area_name}\'s industrial emission reduction targets with national NDC commitments',
        '**UNIDO Cleaner Production Program**: Adopt cleaner production techniques from the UNIDO-Pakistan partnership for pollution prevention in {area_name}',
    ],
    'energy': [
        '**NEPRA Net Metering Regulations**: Leverage distributed generation policy for rooftop solar installations across {area_name} buildings and facilities',
        '**Alternative & Renewable Energy Policy 2019**: Contribute to Pakistan\'s 30% renewable energy target by 2030 through solar integration in {area_name}',
        '**NEECA Energy Conservation Act**: Implement mandatory energy efficiency standards for appliances and building systems in {area_name}',
        '**Punjab Energy Efficiency Action Plan**: Coordinate with provincial government on demand-side management targets for {area_name}',
    ],
    'waste': [
        '**Punjab Local Government Act (Waste)**: Implement municipal solid waste management provisions with source segregation mandates for {area_name}',
        '**Pakistan Environmental Protection Act**: Enforce disposal standards and anti-open-burning provisions for {area_name} waste streams',
        '**LWMC Waste Management Strategy**: Coordinate with Lahore Waste Management Company on expanded collection and recycling for {area_name}',
        '**National Climate Change Policy (Waste)**: Align {area_name}\'s methane capture targets with Pakistan\'s NDC commitments for the waste sector',
    ],
    'buildings': [
        '**Pakistan Building Energy Code (BEEC)**: Adopt minimum energy performance standards for new construction and major renovations in {area_name}',
        '**NEECA Building Efficiency Standards**: Implement mandatory energy labeling for HVAC and lighting in {area_name} commercial buildings',
        '**LDA Green Building Guidelines**: Require green building compliance for new commercial developments in {area_name}',
        '**National Climate Change Policy (Buildings)**: Align {area_name}\'s building efficiency targets with Pakistan\'s NDC and national cooling action plan',
    ],
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
        trend = emissions_analysis.get('trend_direction', 'stable')
        trend_pct = emissions_analysis.get('trend_percentage', 0)
        forecast = emissions_analysis.get('forecast_direction', 'stable')
        dominant = emissions_analysis.get('dominant_sector', sector)
        hist_count = emissions_analysis.get('historical_count', 1)
        monthly_avg = sector_value / max(hist_count, 1)

        # Determine urgency from actual trend data
        if trend == 'increasing' and abs(trend_pct) > 20:
            urgency = 'Critical'
        elif trend == 'increasing':
            urgency = 'High'
        elif trend == 'stable':
            urgency = 'Moderate'
        else:
            urgency = 'Improving'

        # Secondary priority adjusts with urgency
        priority_medium = 'High' if urgency == 'Critical' else 'Medium'

        params = {
            'area_name': area_name,
            'sector': sector,
            'total': f'{total:.0f}',
            'sector_value': f'{sector_value:.0f}',
            'sector_pct': f'{sector_pct:.0f}',
            'trend': trend,
            'trend_pct': f'{abs(trend_pct):.1f}',
            'forecast': forecast,
            'dominant': dominant,
            'urgency': urgency,
            'priority_medium': priority_medium,
            'monthly_avg': f'{monthly_avg:.0f}',
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

        return (
            f"{area_name}'s {sector} sector accounts for {sector_pct:.0f}% "
            f"({sector_value:.0f}t CO2e) of total area emissions ({total:.0f}t CO2e). "
            f"Analysis shows {trend_desc}, and emissions are {forecast_desc}. "
            f"Immediate action is needed to address key emission drivers in this sector. "
            f"The following recommendations are grounded in Pakistan's regulatory framework "
            f"including NEECA, Punjab EPA, and national NDC commitments, tailored to "
            f"{area_name}'s specific context in Lahore."
        )

    def _build_policy_recs(self, policy_results, area_name, sector):
        """Build policy recommendations from real Pakistan regulatory frameworks.

        RAG results are used for summary context only — not as recommendations,
        since the vector store contains news articles, not actionable policies.
        """
        defaults = SECTOR_POLICY_DEFAULTS.get(sector, SECTOR_POLICY_DEFAULTS['energy'])
        return [d.format(area_name=area_name) for d in defaults]

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
