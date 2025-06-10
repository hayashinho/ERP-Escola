from django.db import models
from django.utils.translation import gettext_lazy as _

class SchoolUnit(models.Model):
    name = models.CharField(_('school name'), max_length=255, unique=True)
    address = models.TextField(_('address'), blank=True, null=True)
    phone_number = models.CharField(_('phone number'), max_length=30, blank=True, null=True)
    email = models.EmailField(_('email address'), blank=True, null=True)
    is_active = models.BooleanField(_('is active'), default=True, help_text=_('Is this school unit currently active?'))
    # Add other relevant fields like principal_name, website, etc. later if needed

    class Meta:
        verbose_name = _('School Unit')
        verbose_name_plural = _('School Units')
        ordering = ['name']
        app_label = 'core' # Explicitly set app_label

    def __str__(self):
        return self.name
