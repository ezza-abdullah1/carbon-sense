"""
Management command to rebuild the entire vector index from scratch.

Usage:
    python manage.py rebuild_vector_index [--delete-all]
"""

from django.core.management.base import BaseCommand
from django.core.management import call_command

from recommendations.vector_store import VectorStore
from recommendations.models import PolicyDocument


class Command(BaseCommand):
    help = 'Rebuild the ChromaDB vector index from all indexed policy documents'

    def add_arguments(self, parser):
        parser.add_argument(
            '--delete-all',
            action='store_true',
            help='Delete all chunks and re-ingest everything',
        )

    def handle(self, *args, **options):
        delete_all = options.get('delete_all', False)
        store = VectorStore()

        current_count = store.count()
        self.stdout.write(f'Current vector store: {current_count} chunks')

        if delete_all:
            self.stdout.write('Deleting all chunks...')
            store.delete_all()
            PolicyDocument.objects.update(is_indexed=False, chunk_count=0)
            self.stdout.write(self.style.SUCCESS('All chunks deleted'))

        # Re-ingest using the ingest_policies command with --rebuild
        self.stdout.write('Re-ingesting all documents...')
        call_command('ingest_policies', rebuild=True)

        new_count = store.count()
        self.stdout.write(self.style.SUCCESS(
            f'\nRebuild complete. Vector store: {new_count} chunks'
        ))
