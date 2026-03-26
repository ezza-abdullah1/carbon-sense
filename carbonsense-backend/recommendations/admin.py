from django.contrib import admin
from .models import PolicyDocument, RecommendationCache, ScrapedArticle


@admin.register(PolicyDocument)
class PolicyDocumentAdmin(admin.ModelAdmin):
    list_display = ['title', 'country', 'year', 'policy_type', 'scale', 'chunk_count', 'is_indexed']
    list_filter = ['policy_type', 'scale', 'country', 'is_indexed', 'year']
    search_fields = ['title', 'country', 'source_organization']
    readonly_fields = ['id', 'chunk_count', 'is_indexed', 'ingested_at', 'updated_at']


@admin.register(RecommendationCache)
class RecommendationCacheAdmin(admin.ModelAdmin):
    list_display = ['area_id', 'sector', 'created_at', 'expires_at', 'policy_doc_count']
    list_filter = ['sector', 'created_at']
    readonly_fields = ['id', 'created_at']


@admin.register(ScrapedArticle)
class ScrapedArticleAdmin(admin.ModelAdmin):
    list_display = ['title_short', 'source', 'country', 'relevance_score', 'is_indexed', 'published_date']
    list_filter = ['source', 'country', 'is_indexed']
    search_fields = ['title', 'content']
    readonly_fields = ['id', 'scraped_at']

    def title_short(self, obj):
        return obj.title[:80] + '...' if len(obj.title) > 80 else obj.title
    title_short.short_description = 'Title'
