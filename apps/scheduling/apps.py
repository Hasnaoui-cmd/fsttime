from django.apps import AppConfig


class SchedulingConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.scheduling'
    verbose_name = 'Planification'
    
    def ready(self):
        # Signals merged into apps/notifications/signals.py
        pass
