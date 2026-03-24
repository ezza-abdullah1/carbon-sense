from django.apps import AppConfig


class ApiConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'api'

    def ready(self):
        """Clear Redis cache on server startup to avoid stale data."""
        try:
            from django.core.cache import cache
            cache.clear()
        except Exception:
            pass
