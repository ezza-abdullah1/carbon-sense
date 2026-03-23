"""
Management command to ingest policy documents into the vector database.

Usage:
    python manage.py ingest_policies [--rebuild]
"""

import json
import os
import re
from django.core.management.base import BaseCommand
from django.conf import settings

from recommendations.models import PolicyDocument
from recommendations.vector_store import VectorStore

try:
    import tiktoken
    _encoder = tiktoken.get_encoding("cl100k_base")

    def count_tokens(text):
        return len(_encoder.encode(text))
except ImportError:
    def count_tokens(text):
        return len(text.split())

try:
    from PyPDF2 import PdfReader
except ImportError:
    PdfReader = None


CHUNK_SIZE = 512  # tokens
CHUNK_OVERLAP = 64  # tokens


class Command(BaseCommand):
    help = 'Ingest policy documents from policy_documents/ into ChromaDB vector store'

    def add_arguments(self, parser):
        parser.add_argument(
            '--rebuild',
            action='store_true',
            help='Re-ingest all documents, even if already indexed',
        )

    def handle(self, *args, **options):
        rebuild = options.get('rebuild', False)
        docs_dir = settings.POLICY_DOCUMENTS_DIR

        if not os.path.exists(docs_dir):
            self.stdout.write(self.style.WARNING(
                f'Policy documents directory not found: {docs_dir}'
            ))
            os.makedirs(docs_dir, exist_ok=True)
            self.stdout.write(f'Created directory: {docs_dir}')
            return

        store = VectorStore()

        if rebuild:
            self.stdout.write('Rebuild mode: clearing all existing chunks...')
            store.delete_all()
            PolicyDocument.objects.update(is_indexed=False, chunk_count=0)

        # Find all document files
        doc_files = []
        for fname in sorted(os.listdir(docs_dir)):
            if fname.endswith('.meta.json'):
                continue
            if fname.endswith(('.pdf', '.txt', '.md')):
                doc_files.append(fname)

        if not doc_files:
            self.stdout.write(self.style.WARNING(
                'No document files found in policy_documents/. '
                'Run "python manage.py download_policies" first.'
            ))
            return

        self.stdout.write(f'Found {len(doc_files)} document files')

        total_chunks = 0
        processed = 0
        skipped = 0
        errors = 0

        for fname in doc_files:
            file_path = os.path.join(docs_dir, fname)
            meta_path = os.path.join(docs_dir, self._meta_filename(fname))

            # Check for metadata
            if not os.path.exists(meta_path):
                self.stdout.write(self.style.WARNING(
                    f'  Skipping {fname}: no .meta.json found'
                ))
                skipped += 1
                continue

            # Load metadata
            with open(meta_path, 'r', encoding='utf-8') as f:
                meta = json.load(f)

            # Check if already indexed (unless rebuild)
            existing = PolicyDocument.objects.filter(file_path=fname).first()
            if existing and existing.is_indexed and not rebuild:
                self.stdout.write(f'  Skipping {fname}: already indexed')
                skipped += 1
                continue

            self.stdout.write(f'  Processing: {fname}')

            # Extract text
            try:
                text = self._extract_text(file_path)
            except Exception as e:
                self.stdout.write(self.style.ERROR(
                    f'    Error extracting text from {fname}: {e}'
                ))
                errors += 1
                continue

            if not text or len(text.strip()) < 50:
                self.stdout.write(self.style.WARNING(
                    f'    Skipping {fname}: too little text extracted'
                ))
                skipped += 1
                continue

            # Chunk the text
            chunks = self._chunk_text(text)
            self.stdout.write(f'    Extracted {count_tokens(text)} tokens -> {len(chunks)} chunks')

            # Create/update PolicyDocument record
            sectors = meta.get('sectors', [])
            if isinstance(sectors, str):
                sectors = [s.strip() for s in sectors.split(',')]

            doc, created = PolicyDocument.objects.update_or_create(
                file_path=fname,
                defaults={
                    'title': meta.get('title', fname),
                    'source_url': meta.get('source_url', ''),
                    'country': meta.get('country', 'Unknown'),
                    'region': meta.get('region', ''),
                    'city': meta.get('city', ''),
                    'sectors': sectors,
                    'year': meta.get('year', 2020),
                    'policy_type': meta.get('policy_type', 'guideline'),
                    'scale': meta.get('scale', 'international'),
                    'effectiveness_rating': meta.get('effectiveness_rating', ''),
                    'source_organization': meta.get('source_organization', 'Unknown'),
                }
            )

            # Delete old chunks if re-indexing
            if not created:
                store.delete_by_document_id(str(doc.id))

            # Prepare chunk data for ChromaDB
            chunk_ids = []
            documents = []
            metadatas = []

            sectors_str = ','.join(sectors) if isinstance(sectors, list) else sectors

            for i, chunk in enumerate(chunks):
                chunk_id = f"{doc.id}_chunk_{i}"
                chunk_ids.append(chunk_id)
                documents.append(chunk)
                metadatas.append({
                    'document_id': str(doc.id),
                    'document_title': meta.get('title', fname),
                    'country': meta.get('country', 'Unknown'),
                    'region': meta.get('region', ''),
                    'city': meta.get('city', ''),
                    'sectors': sectors_str,
                    'year': meta.get('year', 2020),
                    'policy_type': meta.get('policy_type', 'guideline'),
                    'scale': meta.get('scale', 'international'),
                    'effectiveness_rating': meta.get('effectiveness_rating', ''),
                    'source_organization': meta.get('source_organization', 'Unknown'),
                })

            # Add to vector store
            store.add_chunks(chunk_ids, documents, metadatas)

            # Update document record
            doc.chunk_count = len(chunks)
            doc.is_indexed = True
            doc.save()

            total_chunks += len(chunks)
            processed += 1

        self.stdout.write(self.style.SUCCESS(
            f'\nIngestion complete: '
            f'{processed} documents processed, '
            f'{total_chunks} chunks indexed, '
            f'{skipped} skipped, '
            f'{errors} errors'
        ))
        self.stdout.write(f'Total chunks in vector store: {store.count()}')

    def _meta_filename(self, fname):
        """Get the .meta.json filename for a document file."""
        base = os.path.splitext(fname)[0]
        return f'{base}.meta.json'

    def _extract_text(self, file_path):
        """Extract text from a PDF or text file."""
        if file_path.endswith('.pdf'):
            if PdfReader is None:
                raise ImportError('PyPDF2 is required for PDF processing. pip install PyPDF2')
            reader = PdfReader(file_path)
            pages = []
            for page in reader.pages:
                text = page.extract_text()
                if text:
                    pages.append(text)
            return '\n\n'.join(pages)
        else:
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                return f.read()

    def _chunk_text(self, text):
        """Split text into overlapping chunks of ~CHUNK_SIZE tokens.

        Uses recursive character splitting respecting paragraph and
        sentence boundaries.
        """
        # Clean up whitespace
        text = re.sub(r'\n{3,}', '\n\n', text)
        text = re.sub(r' {2,}', ' ', text)

        # Split into paragraphs first
        paragraphs = text.split('\n\n')

        chunks = []
        current_chunk = ''
        current_tokens = 0

        for para in paragraphs:
            para = para.strip()
            if not para:
                continue

            para_tokens = count_tokens(para)

            if para_tokens > CHUNK_SIZE:
                # Large paragraph: split by sentences
                if current_chunk:
                    chunks.append(current_chunk.strip())
                    current_chunk = ''
                    current_tokens = 0

                sentences = re.split(r'(?<=[.!?])\s+', para)
                for sent in sentences:
                    sent_tokens = count_tokens(sent)
                    if current_tokens + sent_tokens > CHUNK_SIZE and current_chunk:
                        chunks.append(current_chunk.strip())
                        # Overlap: keep last portion
                        overlap_text = self._get_overlap(current_chunk)
                        current_chunk = overlap_text + ' ' + sent
                        current_tokens = count_tokens(current_chunk)
                    else:
                        current_chunk = (current_chunk + ' ' + sent).strip()
                        current_tokens += sent_tokens
            elif current_tokens + para_tokens > CHUNK_SIZE:
                # Adding this paragraph would exceed limit
                if current_chunk:
                    chunks.append(current_chunk.strip())
                    overlap_text = self._get_overlap(current_chunk)
                    current_chunk = overlap_text + '\n\n' + para
                    current_tokens = count_tokens(current_chunk)
                else:
                    current_chunk = para
                    current_tokens = para_tokens
            else:
                current_chunk = (current_chunk + '\n\n' + para).strip()
                current_tokens += para_tokens

        if current_chunk.strip():
            chunks.append(current_chunk.strip())

        return chunks

    def _get_overlap(self, text):
        """Get the last CHUNK_OVERLAP tokens of text for overlap."""
        words = text.split()
        # Approximate: use last N words where N ≈ CHUNK_OVERLAP
        overlap_words = words[-CHUNK_OVERLAP:] if len(words) > CHUNK_OVERLAP else words[-10:]
        return ' '.join(overlap_words)
