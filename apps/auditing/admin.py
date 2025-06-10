from django.contrib import admin
from django.utils.translation import gettext_lazy as _
from .models import AuditLog

@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
    list_display = ('timestamp', 'user_display', 'action_type_display', 'target_link', 'ip_address', 'short_details')
    list_filter = ('action_type', 'timestamp', 'user', ('target_content_type', admin.RelatedOnlyFieldListFilter))
    search_fields = ('user__username', 'user__email', 'action_type', 'target_object_repr', 'ip_address', 'details__icontains') # Example for JSONField search
    readonly_fields = ('user', 'action_type', 'timestamp', 'ip_address',
                        'target_content_type', 'target_object_id', 'target_object_repr',
                        'target_link', 'details_pretty')
    date_hierarchy = 'timestamp'
    list_per_page = 30
    fieldsets = (
        (_('Log Info'), {'fields': ('timestamp', 'user_display', 'action_type_display', 'ip_address')}),
        (_('Target Object (if any)'), {'fields': ('target_link', 'target_object_repr')}),
        (_('Details'), {'fields': ('details_pretty',)}),
    )


    def user_display(self, obj):
        return obj.user.get_username() if obj.user else _('Anonymous/System')
    user_display.short_description = _('User')
    user_display.admin_order_field = 'user'

    def action_type_display(self, obj):
        return obj.get_action_type_display()
    action_type_display.short_description = _('Action Type')
    action_type_display.admin_order_field = 'action_type'

    def target_link(self, obj):
        from django.urls import reverse
        from django.utils.html import format_html
        if obj.target_object and hasattr(obj.target_object, 'get_absolute_url'):
            url = obj.target_object.get_absolute_url()
            return format_html('<a href="{}">{}</a>', url, obj.target_object_repr)
        elif obj.target_content_type and obj.target_object_id:
            try:
                # Try to generate admin URL if get_absolute_url is not available
                admin_url = reverse(f'admin:{obj.target_content_type.app_label}_{obj.target_content_type.model}_change', args=[obj.target_object_id])
                return format_html('<a href="{}">{} (Admin)</a>', admin_url, obj.target_object_repr or _("View in Admin"))
            except: # noqa
                pass
        return obj.target_object_repr or "N/A"
    target_link.short_description = _('Target Object')

    def short_details(self, obj):
        import json
        if obj.details:
            try:
                # If details is already a dict/list, format it. Otherwise, try to parse if it's a string.
                details_str = json.dumps(obj.details, indent=2, ensure_ascii=False) if isinstance(obj.details, (dict, list)) else str(obj.details)
            except TypeError:
                details_str = str(obj.details)
            return (details_str[:75] + '...') if len(details_str) > 75 else details_str
        return "N/A"
    short_details.short_description = _('Details')

    def details_pretty(self, obj):
        import json
        from django.utils.safestring import mark_safe
        if obj.details:
            try:
                pretty_json = json.dumps(obj.details, indent=2, ensure_ascii=False)
                return mark_safe(f"<pre>{pretty_json}</pre>")
            except TypeError:
                return str(obj.details)
        return None
    details_pretty.short_description = _('Details (Formatted)')


    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        # Consider allowing deletion for superusers or specific roles if needed for GDPR/cleanup
        return request.user.is_superuser
