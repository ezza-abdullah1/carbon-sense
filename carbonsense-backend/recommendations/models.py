import uuid
from django.db import models


class PolicyDocument(models.Model):
    """Tracks ingested policy documents and their metadata."""

    POLICY_TYPE_CHOICES = [
        ('legislation', 'Legislation'),
        ('framework', 'Framework'),
        ('guideline', 'Guideline'),
        ('case_study', 'Case Study'),
        ('technical_report', 'Technical Report'),
    ]

    SCALE_CHOICES = [
        ('local', 'Local'),
        ('national', 'National'),
        ('regional', 'Regional'),
        ('international', 'International'),
    ]

    EFFECTIVENESS_CHOICES = [
        ('proven', 'Proven'),
        ('promising', 'Promising'),
        ('theoretical', 'Theoretical'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    title = models.CharField(max_length=500)
    file_path = models.CharField(max_length=500, blank=True)
    source_url = models.URLField(max_length=1000, blank=True, null=True)
    country = models.CharField(max_length=100)
    region = models.CharField(max_length=100, blank=True, default='')
    city = models.CharField(max_length=100, blank=True, default='')
    sectors = models.JSONField(default=list)
    year = models.IntegerField()
    policy_type = models.CharField(max_length=50, choices=POLICY_TYPE_CHOICES)
    scale = models.CharField(max_length=20, choices=SCALE_CHOICES)
    effectiveness_rating = models.CharField(
        max_length=20, choices=EFFECTIVENESS_CHOICES, blank=True, default=''
    )
    source_organization = models.CharField(max_length=255)
    chunk_count = models.IntegerField(default=0)
    is_indexed = models.BooleanField(default=False)
    ingested_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'policy_documents'
        ordering = ['-year', 'title']

    def __str__(self):
        return f"{self.title} ({self.year})"


class RecommendationCache(models.Model):
    """Cache generated recommendations to avoid redundant LLM calls."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    area_id = models.CharField(max_length=255, default='')
    sector = models.CharField(max_length=50)
    response_data = models.JSONField()
    confidence_scores = models.JSONField(default=dict)
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()
    policy_doc_count = models.IntegerField(default=0)
    emissions_data_hash = models.CharField(max_length=64)

    class Meta:
        db_table = 'recommendation_cache'
        indexes = [
            models.Index(fields=['area_id', 'sector']),
            models.Index(fields=['expires_at']),
        ]
        unique_together = [('area_id', 'sector')]

    def __str__(self):
        return f"Cache: {self.area_id} - {self.sector}"


class ScrapedArticle(models.Model):
    """Tracks articles scraped from climate policy news sources."""

    SOURCE_CHOICES = [
        ('carbon_brief', 'Carbon Brief'),
        ('climate_home', 'Climate Home News'),
        ('unfccc', 'UNFCCC News'),
        ('iea', 'IEA News'),
        ('dawn_climate', 'Dawn (Pakistan) Climate'),
        ('the_news_pk', 'The News International Pakistan'),
        ('world_bank', 'World Bank Climate'),
        ('reuters_climate', 'Reuters Climate'),
        ('pakistan_govt', 'Pakistan Government'),
        ('unep', 'UNEP News'),
        ('irena', 'IRENA News'),
        ('custom_rss', 'Custom RSS Feed'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    title = models.CharField(max_length=1000)
    url = models.URLField(max_length=2000, unique=True)
    source = models.CharField(max_length=50, choices=SOURCE_CHOICES)
    content = models.TextField()
    summary = models.TextField(blank=True, default='')
    published_date = models.DateTimeField(null=True, blank=True)

    # Classification (auto-detected or set by Gemini)
    country = models.CharField(max_length=100, default='Global')
    sectors = models.JSONField(default=list)
    relevance_score = models.FloatField(default=0.0)  # 0-1, how relevant to CarbonSense

    # Ingestion tracking
    is_indexed = models.BooleanField(default=False)
    scraped_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'scraped_articles'
        ordering = ['-published_date']
        indexes = [
            models.Index(fields=['source', '-published_date']),
            models.Index(fields=['is_indexed']),
            models.Index(fields=['-relevance_score']),
        ]

    def __str__(self):
        return f"[{self.source}] {self.title[:80]}"
