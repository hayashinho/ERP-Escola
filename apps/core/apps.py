from django.apps import AppConfig
from django.utils.translation import gettext_lazy as _

class CoreConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.core' # Corrected name to include 'apps.' prefix
    verbose_name = _('Core')
    label = 'core' # Explicitly set app_label if needed, though name often suffices
