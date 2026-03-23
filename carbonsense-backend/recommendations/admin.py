from django.contrib import admin
from .models import PolicyDocument, RecommendationCache


@admin.register(PolicyDocument)
class PolicyDocumentAdmin(admin.ModelAdmin):
    list_display = ['title', 'country', 'year', 'policy_type', 'scale', 'chunk_count', 'is_indexed']
    list_filter = ['policy_type', 'scale', 'country', 'is_indexed', 'year']
    search_fields = ['title', 'country', 'source_organization']
    readonly_fields = ['id', 'chunk_count', 'is_indexed', 'ingested_at', 'updated_at']


@admin.register(RecommendationCache)
class RecommendationCacheAdmin(admin.ModelAdmin):
    list_display = ['area', 'sector', 'created_at', 'expires_at', 'policy_doc_count']
    list_filter = ['sector', 'created_at']
    readonly_fields = ['id', 'created_at']
