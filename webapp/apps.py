from django.apps import AppConfig


class WebappConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'webapp'
    verbose_name = "HealthMap"
    app_subtitle = "Locate and navigate to health facilities"
