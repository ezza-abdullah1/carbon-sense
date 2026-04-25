"""
Embed already-scraped (or freshly-scraped) ScrapedArticle rows into the
`recent_news` ChromaDB collection used by the agentic RAG NewsRetriever.

Usage:
    python manage.py refresh_recent_news [--scrape] [--max-age 7] [--limit 200]
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import chromadb
from chromadb.utils import embedding_functions
from django.conf import settings
from django.core.management import call_command
from django.core.management.base import BaseCommand

from recommendations.models import ScrapedArticle


_BATCH_SIZE = 64
_MAX_CHARS = 1800  # one chunk per article — these are short news bodies already


class Command(BaseCommand):
    help = "Embed ScrapedArticle rows into the recent_news ChromaDB collection."

    def add_arguments(self, parser):
        parser.add_argument(
            '--scrape',
            action='store_true',
            help='Run scrape_policy_updates first to fetch fresh articles.',
        )
        parser.add_argument('--max-age', type=int, default=7,
                            help='Days to look back when --scrape is set (default 7).')
        parser.add_argument('--min-relevance', type=float, default=0.15,
                            help='Forward to scrape_policy_updates (default 0.15).')
        parser.add_argument('--limit', type=int, default=500,
                            help='Max articles to embed in one run (default 500).')
        parser.add_argument('--reindex', action='store_true',
                            help='Re-embed even articles already marked is_indexed.')

    def handle(self, *args, **options):
        if options['scrape']:
            self.stdout.write(self.style.NOTICE("Running scrape_policy_updates ..."))
            call_command(
                'scrape_policy_updates',
                f"--max-age={options['max_age']}",
                f"--min-relevance={options['min_relevance']}",
            )

        collection = self._open_collection()

        qs = ScrapedArticle.objects.all().order_by('-published_date', '-scraped_at')
        if not options['reindex']:
            qs = qs.filter(is_indexed=False)
        qs = qs[: options['limit']]

        total = qs.count()
        if total == 0:
            self.stdout.write(self.style.WARNING(
                "No new articles to embed. Use --reindex to rebuild."
            ))
            return

        ids: list[str] = []
        documents: list[str] = []
        metadatas: list[dict] = []
        flushed = 0

        for article in qs:
            text = (article.content or article.summary or article.title or '').strip()
            if not text:
                continue
            text = text[:_MAX_CHARS]
            ids.append(f"news_{article.id}")
            documents.append(text)
            year = (article.published_date or article.scraped_at).year
            metadatas.append({
                'document_title': (article.title or '')[:160],
                'document_id': str(article.id),
                'country': article.country or 'Global',
                'region': '',
                'city': '',
                'sectors': ','.join(article.sectors or []) if isinstance(article.sectors, list) else str(article.sectors or ''),
                'year': year,
                'policy_type': 'news_article',
                'scale': 'international',
                'source': article.source,
                'source_url': article.url,
                'effectiveness_rating': '',
                'source_organization': dict(article._meta.get_field('source').choices).get(article.source, article.source),
            })
            article.is_indexed = True
            article.save(update_fields=['is_indexed'])

            if len(ids) >= _BATCH_SIZE:
                collection.add(ids=ids, documents=documents, metadatas=metadatas)
                flushed += len(ids)
                ids, documents, metadatas = [], [], []

        if ids:
            collection.add(ids=ids, documents=documents, metadatas=metadatas)
            flushed += len(ids)

        self.stdout.write(self.style.SUCCESS(
            f"Embedded {flushed} article(s) into recent_news collection."
        ))

    def _open_collection(self):
        client = chromadb.PersistentClient(path=settings.CHROMA_PERSIST_DIR)
        emb = embedding_functions.SentenceTransformerEmbeddingFunction(
            model_name=settings.EMBEDDING_MODEL,
        )
        return client.get_or_create_collection(
            name=getattr(settings, 'RECOMMENDATION_RECENT_NEWS_COLLECTION', 'recent_news'),
            metadata={"hnsw:space": "cosine"},
            embedding_function=emb,
        )
