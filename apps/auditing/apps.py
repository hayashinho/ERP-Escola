from django.apps import AppConfig
from django.utils.translation import gettext_lazy as _

class AuditingConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.auditing'
    verbose_name = _('Auditing')
    label = 'auditing' # Explicitly set app_label

    def ready(self):
        import apps.auditing.signals # Connect signals when app is ready
