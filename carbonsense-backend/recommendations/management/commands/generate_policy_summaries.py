"""
Management command to generate detailed policy document summaries using Gemini AI.

For documents where PDFs cannot be auto-downloaded, this command uses the LLM
to generate comprehensive text summaries based on the document title and metadata.
These summaries serve as the knowledge base for the RAG pipeline.

Usage:
    python manage.py generate_policy_summaries [--tier 1] [--overwrite] [--dry-run]
"""

import json
import os
import time
from django.core.management.base import BaseCommand
from django.conf import settings

import google.generativeai as genai

from recommendations.policy_registry import POLICY_REGISTRY


SUMMARY_PROMPT_TEMPLATE = """You are a climate policy research assistant. Generate a comprehensive, detailed summary of the following policy document. This summary will be used as a reference document in a knowledge base for generating carbon emission reduction recommendations for cities in Pakistan, specifically Lahore.

Document Information:
- Title: {title}
- Country/Region: {country} {region}
- City: {city}
- Year: {year}
- Type: {policy_type}
- Scale: {scale}
- Sectors: {sectors}
- Organization: {source_organization}

Write a detailed 800-1500 word summary covering ALL of the following:

1. **Purpose & Scope**: What is this document about? What problem does it address? What geography/sectors does it cover?

2. **Key Targets & Commitments**: Specific numerical targets, deadlines, emission reduction goals, renewable energy percentages, etc. Be as specific as possible with numbers.

3. **Policy Mechanisms & Instruments**: What specific policy tools does it use? (e.g., carbon pricing, regulations, subsidies, standards, cap-and-trade, taxes, mandates)

4. **Sector-Specific Measures**: Detail specific measures for each relevant sector (transport, industry, energy, waste, buildings). Include concrete actions, not just vague goals.

5. **Implementation Framework**: How is it structured for implementation? What institutions are responsible? What timelines are defined?

6. **Financial Mechanisms**: Funding sources, budget allocations, international finance commitments, green bonds, carbon credits, etc.

7. **Monitoring & Reporting**: How is progress tracked? What metrics and KPIs are used?

8. **Relevance to Pakistan/Lahore**: How does this document relate to Pakistan's climate challenges? What lessons or mechanisms are transferable to Lahore specifically? Consider urban air quality, industrial emissions, transport, waste management, and energy transition.

9. **Key Statistics & Data Points**: Include any important numbers, percentages, or data points from the document.

10. **Effectiveness Assessment**: What evidence exists about the effectiveness of the measures? What has worked and what hasn't?

Write in a factual, policy-analysis style. Include specific numbers, dates, and details wherever possible. Do NOT add disclaimers about your knowledge — write as if you are summarizing the actual document.
"""


class Command(BaseCommand):
    help = 'Generate AI-powered policy summaries for documents without PDFs'

    def add_arguments(self, parser):
        parser.add_argument(
            '--tier',
            type=int,
            default=None,
            help='Only process documents from a specific tier (1-4)',
        )
        parser.add_argument(
            '--overwrite',
            action='store_true',
            help='Overwrite existing summary files',
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be generated without actually generating',
        )
        parser.add_argument(
            '--all',
            action='store_true',
            help='Generate summaries for ALL documents, even those with PDFs',
        )

    def handle(self, *args, **options):
        tier = options.get('tier')
        overwrite = options.get('overwrite', False)
        dry_run = options.get('dry_run', False)
        process_all = options.get('all', False)

        # Configure Gemini
        api_key = settings.GEMINI_API_KEY
        if not api_key or api_key == 'your-gemini-api-key-here':
            self.stdout.write(self.style.ERROR(
                'GEMINI_API_KEY is not configured. Set it in your .env file.'
            ))
            return

        genai.configure(api_key=api_key)
        model = genai.GenerativeModel('gemini-2.0-flash')

        docs_dir = settings.POLICY_DOCUMENTS_DIR
        os.makedirs(docs_dir, exist_ok=True)

        # Filter entries
        entries = POLICY_REGISTRY
        if tier is not None:
            entries = [e for e in entries if e.get('tier') == tier]

        # Filter to only those missing files (unless --all)
        to_process = []
        for entry in entries:
            doc_id = entry['id']
            pdf_path = os.path.join(docs_dir, f'{doc_id}.pdf')
            txt_path = os.path.join(docs_dir, f'{doc_id}.txt')

            if not process_all and os.path.exists(pdf_path):
                continue  # Already have the real PDF

            if os.path.exists(txt_path) and not overwrite:
                continue  # Already have a summary

            to_process.append(entry)

        if not to_process:
            self.stdout.write(self.style.SUCCESS('Nothing to process — all documents already have files.'))
            return

        self.stdout.write(f'Will generate summaries for {len(to_process)} documents')
        if dry_run:
            for entry in to_process:
                self.stdout.write(f'  [DRY RUN] {entry["id"]}: {entry["title"]}')
            return

        generated = 0
        failed = 0

        for i, entry in enumerate(to_process, 1):
            doc_id = entry['id']
            title = entry.get('title', doc_id)

            self.stdout.write(f'  [{i}/{len(to_process)}] Generating: {title}')

            try:
                summary = self._generate_summary(model, entry)

                # Save as .txt file
                txt_path = os.path.join(docs_dir, f'{doc_id}.txt')
                with open(txt_path, 'w', encoding='utf-8') as f:
                    f.write(f"# {title}\n\n")
                    f.write(f"Year: {entry.get('year', 'Unknown')} | "
                            f"Country: {entry.get('country', 'Unknown')} | "
                            f"Organization: {entry.get('source_organization', 'Unknown')}\n")
                    f.write(f"Sectors: {', '.join(entry.get('sectors', []))}\n")
                    f.write(f"Type: {entry.get('policy_type', '')} | "
                            f"Scale: {entry.get('scale', '')}\n\n")
                    f.write("---\n\n")
                    f.write(summary)

                # Create .meta.json if it doesn't exist
                meta_path = os.path.join(docs_dir, f'{doc_id}.meta.json')
                if not os.path.exists(meta_path):
                    meta = {
                        'title': entry.get('title', ''),
                        'country': entry.get('country', ''),
                        'region': entry.get('region', ''),
                        'city': entry.get('city', ''),
                        'sectors': entry.get('sectors', []),
                        'year': entry.get('year', 2020),
                        'policy_type': entry.get('policy_type', 'guideline'),
                        'scale': entry.get('scale', 'international'),
                        'effectiveness_rating': entry.get('effectiveness_rating', ''),
                        'source_organization': entry.get('source_organization', ''),
                        'source_url': entry.get('url', ''),
                    }
                    with open(meta_path, 'w', encoding='utf-8') as f:
                        json.dump(meta, f, indent=2, ensure_ascii=False)

                generated += 1
                self.stdout.write(self.style.SUCCESS(f'    Saved: {doc_id}.txt'))

            except Exception as e:
                self.stdout.write(self.style.ERROR(f'    Failed: {e}'))
                failed += 1

            # Rate limiting — Gemini free tier allows 15 RPM
            if i < len(to_process):
                time.sleep(4)

        self.stdout.write(self.style.SUCCESS(
            f'\nGeneration complete: {generated} summaries created, {failed} failed'
        ))
        self.stdout.write(
            'Now run: python manage.py ingest_policies --rebuild'
        )

    def _generate_summary(self, model, entry):
        """Generate a detailed policy summary using Gemini."""
        prompt = SUMMARY_PROMPT_TEMPLATE.format(
            title=entry.get('title', ''),
            country=entry.get('country', ''),
            region=entry.get('region', ''),
            city=entry.get('city', ''),
            year=entry.get('year', ''),
            policy_type=entry.get('policy_type', ''),
            scale=entry.get('scale', ''),
            sectors=', '.join(entry.get('sectors', [])),
            source_organization=entry.get('source_organization', ''),
        )

        response = model.generate_content(
            prompt,
            generation_config=genai.types.GenerationConfig(
                temperature=0.3,  # Lower temp for factual content
                max_output_tokens=4096,
            ),
        )

        return response.text
