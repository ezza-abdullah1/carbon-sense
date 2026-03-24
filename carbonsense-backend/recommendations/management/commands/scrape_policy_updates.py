"""
Management command to scrape latest climate policy news and ingest into vector DB.

Scrapes from RSS feeds and news sites, classifies by relevance, stores in DB,
and indexes relevant articles into ChromaDB for RAG retrieval.

Usage:
    python manage.py scrape_policy_updates [--max-age 7] [--min-relevance 0.15]
"""

import json
import os
import re
from datetime import datetime

from django.core.management.base import BaseCommand
from django.conf import settings

from recommendations.models import ScrapedArticle
from recommendations.scraper import PolicyScraper
from recommendations.vector_store import VectorStore


class Command(BaseCommand):
    help = 'Scrape latest climate policy news and ingest into vector DB'

    def add_arguments(self, parser):
        parser.add_argument(
            '--max-age',
            type=int,
            default=7,
            help='Maximum age of articles in days (default: 7)',
        )
        parser.add_argument(
            '--min-relevance',
            type=float,
            default=0.15,
            help='Minimum relevance score to index (default: 0.15)',
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Scrape but do not save to DB or index',
        )

    def handle(self, *args, **options):
        max_age = options.get('max_age', 7)
        min_relevance = options.get('min_relevance', 0.15)
        dry_run = options.get('dry_run', False)

        self.stdout.write(f'Scraping climate policy news (max age: {max_age} days)...')

        # Get existing URLs to avoid duplicates
        existing_urls = set(
            ScrapedArticle.objects.values_list('url', flat=True)
        )
        self.stdout.write(f'Existing articles in DB: {len(existing_urls)}')

        # Run scraper
        scraper = PolicyScraper(max_age_days=max_age)
        articles = scraper.scrape_all(existing_urls=existing_urls)

        self.stdout.write(f'Found {len(articles)} relevant new articles')

        if dry_run:
            for article in articles:
                self.stdout.write(
                    f'  [{article["source"]}] (relevance: {article["relevance_score"]:.2f}) '
                    f'{article["title"][:80]}'
                )
            return

        # Save to database
        saved = 0
        for article in articles:
            try:
                ScrapedArticle.objects.create(
                    title=article['title'],
                    url=article['url'],
                    source=article['source'],
                    content=article['content'],
                    published_date=article.get('published_date'),
                    country=article.get('country', 'Global'),
                    sectors=article.get('sectors', []),
                    relevance_score=article.get('relevance_score', 0),
                )
                saved += 1
            except Exception as e:
                # Skip duplicates or other DB errors
                self.stdout.write(self.style.WARNING(f'  Skip {article["url"][:60]}: {e}'))

        self.stdout.write(self.style.SUCCESS(f'Saved {saved} new articles to DB'))

        # Index high-relevance articles into ChromaDB
        to_index = ScrapedArticle.objects.filter(
            is_indexed=False,
            relevance_score__gte=min_relevance,
        ).order_by('-relevance_score')

        if not to_index.exists():
            self.stdout.write('No new articles to index.')
            return

        self.stdout.write(f'Indexing {to_index.count()} articles into vector store...')

        store = VectorStore()
        indexed = 0

        for article in to_index:
            try:
                chunks = self._chunk_article(article)
                if not chunks:
                    continue

                chunk_ids = []
                documents = []
                metadatas = []

                sectors_str = ','.join(article.sectors) if article.sectors else 'energy'
                pub_year = article.published_date.year if article.published_date else datetime.now().year

                for i, chunk in enumerate(chunks):
                    chunk_ids.append(f"scraped_{article.id}_chunk_{i}")
                    documents.append(chunk)
                    metadatas.append({
                        'document_id': str(article.id),
                        'document_title': article.title[:200],
                        'country': article.country,
                        'region': '',
                        'city': '',
                        'sectors': sectors_str,
                        'year': pub_year,
                        'policy_type': 'technical_report',
                        'scale': 'international',
                        'effectiveness_rating': '',
                        'source_organization': article.source,
                        'is_scraped': 'true',
                    })

                store.add_chunks(chunk_ids, documents, metadatas)
                article.is_indexed = True
                article.save(update_fields=['is_indexed'])
                indexed += 1

            except Exception as e:
                self.stdout.write(self.style.WARNING(
                    f'  Error indexing article {article.id}: {e}'
                ))

        self.stdout.write(self.style.SUCCESS(
            f'Indexed {indexed} articles. '
            f'Total chunks in vector store: {store.count()}'
        ))

    def _chunk_article(self, article):
        """Split article content into chunks for embedding."""
        text = f"{article.title}\n\n{article.content}"
        text = re.sub(r'\n{3,}', '\n\n', text)
        text = re.sub(r' {2,}', ' ', text)

        # Simple paragraph-based chunking (articles are shorter than PDFs)
        paragraphs = text.split('\n\n')
        chunks = []
        current = ''

        for para in paragraphs:
            para = para.strip()
            if not para:
                continue

            if len(current.split()) + len(para.split()) > 400:
                if current.strip():
                    chunks.append(current.strip())
                current = para
            else:
                current = f"{current}\n\n{para}" if current else para

        if current.strip():
            chunks.append(current.strip())

        return chunks
