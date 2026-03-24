"""
Background scheduler that runs the policy scraper every 72 hours.

Usage:
    python manage.py run_scraper_scheduler [--interval 72] [--run-now]

Run this in a separate terminal or as a background process.
It will scrape climate policy news sources, save new articles,
and index them into the vector database on the configured interval.
"""

import signal
import sys
import time
from datetime import datetime

from django.core.management.base import BaseCommand
from django.core.management import call_command


class Command(BaseCommand):
    help = 'Run the policy scraper on a recurring schedule (default: every 72 hours)'

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._shutdown = False

    def add_arguments(self, parser):
        parser.add_argument(
            '--interval',
            type=int,
            default=72,
            help='Scraping interval in hours (default: 72)',
        )
        parser.add_argument(
            '--run-now',
            action='store_true',
            help='Run the scraper immediately on startup before entering the loop',
        )
        parser.add_argument(
            '--max-age',
            type=int,
            default=4,
            help='Max article age in days per scrape cycle (default: 4)',
        )

    def handle(self, *args, **options):
        interval_hours = options.get('interval', 72)
        run_now = options.get('run_now', True)
        max_age = options.get('max_age', 4)
        interval_seconds = interval_hours * 3600

        # Handle graceful shutdown
        signal.signal(signal.SIGINT, self._handle_shutdown)
        signal.signal(signal.SIGTERM, self._handle_shutdown)

        self.stdout.write(self.style.SUCCESS(
            f'Policy scraper scheduler started\n'
            f'  Interval: every {interval_hours} hours\n'
            f'  Max article age: {max_age} days\n'
            f'  Press Ctrl+C to stop'
        ))

        if run_now:
            self._run_scrape(max_age)

        while not self._shutdown:
            # Sleep in small increments so we can catch shutdown signals
            next_run = datetime.now().timestamp() + interval_seconds
            next_run_str = datetime.fromtimestamp(next_run).strftime('%Y-%m-%d %H:%M:%S')
            self.stdout.write(f'\nNext scrape at: {next_run_str}')

            while not self._shutdown and time.time() < next_run:
                time.sleep(30)  # Check every 30 seconds

            if not self._shutdown:
                self._run_scrape(max_age)

        self.stdout.write(self.style.SUCCESS('\nScheduler stopped gracefully.'))

    def _run_scrape(self, max_age):
        """Execute one scraping cycle."""
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        self.stdout.write(f'\n{"=" * 60}')
        self.stdout.write(f'Scrape cycle started at {timestamp}')
        self.stdout.write(f'{"=" * 60}')

        try:
            call_command('scrape_policy_updates', max_age=max_age)
            self.stdout.write(self.style.SUCCESS(
                f'Scrape cycle completed at {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}'
            ))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'Scrape cycle failed: {e}'))

    def _handle_shutdown(self, signum, frame):
        """Handle shutdown signals gracefully."""
        self.stdout.write('\nShutdown signal received, finishing current cycle...')
        self._shutdown = True
