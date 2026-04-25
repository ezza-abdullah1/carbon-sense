"""
Aggregate positive RecommendationFeedback into a few-shot examples file
that the synthesizer prompt loads on the next generation.

Usage:
    python manage.py rebuild_few_shot_examples [--k 2]
"""

from __future__ import annotations

import json

from django.core.management.base import BaseCommand

from recommendations.feedback import FeedbackService


class Command(BaseCommand):
    help = "Rebuild the few-shot examples file from RecommendationFeedback."

    def add_arguments(self, parser):
        parser.add_argument('--k', type=int, default=2,
                            help='Examples per (sector, country) group (default 2).')

    def handle(self, *args, **options):
        groups = FeedbackService.rebuild_few_shot_index(k_per_group=options['k'])
        total = sum(len(v) for v in groups.values())
        self.stdout.write(self.style.SUCCESS(
            f"Wrote {total} example(s) across {len(groups)} group(s) to few_shot_examples.json"
        ))
        for key, items in groups.items():
            self.stdout.write(f"  {key}: {len(items)}")
