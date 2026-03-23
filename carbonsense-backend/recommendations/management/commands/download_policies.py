"""
Management command to download policy documents from known public URLs.

Usage:
    python manage.py download_policies [--tier 1] [--dry-run] [--list]
"""

import json
import os
import time
from django.core.management.base import BaseCommand
from django.conf import settings

try:
    import requests
except ImportError:
    requests = None

from recommendations.policy_registry import POLICY_REGISTRY


class Command(BaseCommand):
    help = 'Download policy documents from public URLs defined in policy_registry.py'

    def add_arguments(self, parser):
        parser.add_argument(
            '--tier',
            type=int,
            default=None,
            help='Only download documents from a specific tier (1-4)',
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be downloaded without actually downloading',
        )
        parser.add_argument(
            '--list',
            action='store_true',
            help='List all documents in the registry with their status',
        )

    def handle(self, *args, **options):
        if requests is None:
            self.stdout.write(self.style.ERROR(
                'The "requests" package is required. Install with: pip install requests'
            ))
            return

        tier = options.get('tier')
        dry_run = options.get('dry_run', False)
        list_only = options.get('list', False)

        docs_dir = settings.POLICY_DOCUMENTS_DIR
        os.makedirs(docs_dir, exist_ok=True)

        # Filter registry
        entries = POLICY_REGISTRY
        if tier is not None:
            entries = [e for e in entries if e.get('tier') == tier]

        # Enforce 2020+ year constraint
        pre_2020 = [e for e in entries if e.get('year', 2020) < 2020]
        if pre_2020:
            self.stdout.write(self.style.WARNING(
                f'Skipping {len(pre_2020)} entries with year < 2020'
            ))
            entries = [e for e in entries if e.get('year', 2020) >= 2020]

        if list_only:
            self._list_entries(entries, docs_dir)
            return

        self.stdout.write(f'Registry contains {len(entries)} documents')
        if dry_run:
            self.stdout.write(self.style.WARNING('DRY RUN - no files will be downloaded'))

        downloaded = 0
        skipped = 0
        manual_needed = 0
        failed = 0

        for entry in entries:
            doc_id = entry['id']
            url = entry.get('url')
            title = entry.get('title', doc_id)

            # Determine file extension from URL
            ext = '.pdf'
            if url and '.txt' in url:
                ext = '.txt'

            filename = f'{doc_id}{ext}'
            filepath = os.path.join(docs_dir, filename)
            meta_path = os.path.join(docs_dir, f'{doc_id}.meta.json')

            # Skip if already downloaded
            if os.path.exists(filepath):
                self.stdout.write(f'  [EXISTS] {doc_id}')
                # Still create meta.json if missing
                if not os.path.exists(meta_path):
                    self._write_meta(meta_path, entry)
                skipped += 1
                continue

            if url is None:
                manual_note = entry.get('manual_note', 'URL not available')
                self.stdout.write(self.style.WARNING(
                    f'  [MANUAL] {doc_id}: {manual_note}'
                ))
                # Write meta.json anyway for manual downloads
                if not dry_run:
                    self._write_meta(meta_path, entry)
                manual_needed += 1
                continue

            self.stdout.write(f'  Downloading: {title}')
            if dry_run:
                downloaded += 1
                continue

            # Download the file
            try:
                success = self._download_file(url, filepath)
                if success:
                    self._write_meta(meta_path, entry)
                    downloaded += 1
                    self.stdout.write(self.style.SUCCESS(f'    Saved: {filename}'))
                else:
                    failed += 1
            except Exception as e:
                self.stdout.write(self.style.ERROR(f'    Failed: {e}'))
                failed += 1

            # Be polite with rate limiting
            time.sleep(1)

        self.stdout.write(self.style.SUCCESS(
            f'\nDownload complete: '
            f'{downloaded} downloaded, '
            f'{skipped} already exist, '
            f'{manual_needed} need manual download, '
            f'{failed} failed'
        ))

        if manual_needed > 0:
            self.stdout.write(self.style.WARNING(
                '\nManual downloads needed. Run with --list to see details.'
            ))

    def _download_file(self, url, filepath):
        """Download a file from URL with retry logic."""
        headers = {
            'User-Agent': 'CarbonSense/1.0 (Climate Policy Research; https://github.com/carbonsense)'
        }

        for attempt in range(3):
            try:
                response = requests.get(url, headers=headers, timeout=60, stream=True)
                response.raise_for_status()

                with open(filepath, 'wb') as f:
                    for chunk in response.iter_content(chunk_size=8192):
                        f.write(chunk)

                # Verify file is not empty
                if os.path.getsize(filepath) < 100:
                    os.remove(filepath)
                    self.stdout.write(self.style.WARNING(
                        f'    Downloaded file too small, retrying...'
                    ))
                    continue

                return True
            except requests.exceptions.RequestException as e:
                if attempt < 2:
                    self.stdout.write(f'    Retry {attempt + 1}/3: {e}')
                    time.sleep(2 ** attempt)
                else:
                    self.stdout.write(self.style.ERROR(f'    All retries failed: {e}'))
                    # Clean up partial download
                    if os.path.exists(filepath):
                        os.remove(filepath)
                    return False
        return False

    def _write_meta(self, meta_path, entry):
        """Write the .meta.json file for a document."""
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

    def _list_entries(self, entries, docs_dir):
        """List all entries with their download status."""
        self.stdout.write(f'\n{"ID":<45} {"Year":<6} {"Tier":<6} {"Status":<12} {"Title"}')
        self.stdout.write('-' * 120)

        for entry in entries:
            doc_id = entry['id']
            year = entry.get('year', '?')
            tier_num = entry.get('tier', '?')
            title = entry.get('title', doc_id)[:50]

            filepath = os.path.join(docs_dir, f'{doc_id}.pdf')
            txt_path = os.path.join(docs_dir, f'{doc_id}.txt')

            if os.path.exists(filepath) or os.path.exists(txt_path):
                status = self.style.SUCCESS('DOWNLOADED')
            elif entry.get('url') is None:
                status = self.style.WARNING('MANUAL')
            else:
                status = 'PENDING'

            self.stdout.write(f'{doc_id:<45} {year:<6} {tier_num:<6} {status:<12} {title}')

        self.stdout.write(f'\nTotal: {len(entries)} documents')
