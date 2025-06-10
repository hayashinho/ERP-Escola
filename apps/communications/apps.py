from django.apps import AppConfig
from django.utils.translation import gettext_lazy as _

class CommunicationsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.communications'
    verbose_name = _('Communications') # Added verbose_name
    label = 'communications' # Explicitly set app_label

    def ready(self):
        import apps.communications.signals # Connect signals
