from django.db import models
from django.conf import settings
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.utils.translation import gettext_lazy as _

class AuditLog(models.Model):
    ACTION_LOGIN_SUCCESS = 'LOGIN_SUCCESS'
    ACTION_LOGIN_FAILED = 'LOGIN_FAILED'
    ACTION_LOGOUT = 'LOGOUT'
    ACTION_CREATED = 'CREATED'
    ACTION_UPDATED = 'UPDATED'
    ACTION_DELETED = 'DELETED'
    ACTION_VIEWED = 'VIEWED'
    ACTION_EXPORTED = 'EXPORTED'
    # Add more specific actions as needed

    ACTION_TYPE_CHOICES = [
        (ACTION_LOGIN_SUCCESS, _('Login Successful')),
        (ACTION_LOGIN_FAILED, _('Login Failed')),
        (ACTION_LOGOUT, _('Logout')),
        (ACTION_CREATED, _('Object Created')),
        (ACTION_UPDATED, _('Object Updated')),
        (ACTION_DELETED, _('Object Deleted')),
        (ACTION_VIEWED, _('Object/View Accessed')),
        (ACTION_EXPORTED, _('Data Exported')),
    ]

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name=_('user'),
        related_name='audit_logs'
    )
    action_type = models.CharField(
        _('action type'),
        max_length=50, # Increased length for potentially longer custom action types
        choices=ACTION_TYPE_CHOICES,
        db_index=True
    )
    timestamp = models.DateTimeField(_('timestamp'), auto_now_add=True, db_index=True)
    ip_address = models.GenericIPAddressField(_('IP address'), null=True, blank=True)

    target_content_type = models.ForeignKey(
        ContentType,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name=_('target content type')
    )
    target_object_id = models.CharField( # Changed to CharField to accommodate non-integer PKs if ever needed
        _('target object ID'),
        max_length=255, # General purpose length
        null=True,
        blank=True,
        db_index=True
    )
    target_object = GenericForeignKey('target_content_type', 'target_object_id')

    target_object_repr = models.CharField(
        _('target object representation'),
        max_length=255,
        blank=True,
        null=True,
        help_text=_("String representation of the target object at the time of logging.")
    )

    details = models.JSONField(
        _('details'),
        null=True,
        blank=True,
        help_text=_("Additional details about the action, e.g., changed fields, parameters.")
    )

    class Meta:
        verbose_name = _('Audit Log')
        verbose_name_plural = _('Audit Logs')
        ordering = ['-timestamp']
        indexes = [
            models.Index(fields=['target_content_type', 'target_object_id']),
            models.Index(fields=['action_type', 'timestamp']), # Index for filtering by action and time
        ]
        # app_label = 'auditing' # Not needed as apps.py has label = 'auditing'

    def __str__(self):
        user_str = self.user.get_username() if self.user else _('Anonymous/System')
        return f"{self.timestamp} - {user_str} - {self.get_action_type_display()} - Obj: {self.target_object_repr or 'N/A'}"
