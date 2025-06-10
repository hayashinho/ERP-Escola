from django.contrib import admin
from django.utils.translation import gettext_lazy as _
from .models import MessageThread, Message

class MessageInline(admin.StackedInline): # Or admin.TabularInline
    model = Message
    extra = 0 # Default to 0, admin can add if needed
    fields = ('sender', 'content', 'timestamp', 'read_by')
    readonly_fields = ('timestamp',)
    raw_id_fields = ('sender', 'read_by')
    ordering = ('timestamp',)

@admin.register(MessageThread)
class MessageThreadAdmin(admin.ModelAdmin):
    list_display = ('id', 'subject_display', 'created_at', 'updated_at', 'participant_count_display')
    search_fields = ('subject', 'participants__username', 'participants__email')
    filter_horizontal = ('participants',)
    inlines = [MessageInline]
    readonly_fields = ('created_at', 'updated_at')
    list_per_page = 25

    def subject_display(self, obj):
        return obj.subject if obj.subject else f"Thread ID: {obj.id}"
    subject_display.short_description = _('Subject / Thread ID')
    subject_display.admin_order_field = 'subject'


    def participant_count_display(self, obj):
        return obj.participants.count()
    participant_count_display.short_description = _('Participants')


@admin.register(Message)
class MessageAdmin(admin.ModelAdmin):
    list_display = ('id', 'thread_id_display', 'sender_display', 'timestamp', 'short_content', 'read_by_count_display')
    list_filter = ('timestamp', 'thread__subject')
    search_fields = ('content', 'sender__username', 'sender__email', 'thread__subject')
    raw_id_fields = ('thread', 'sender', 'read_by')
    readonly_fields = ('timestamp',)
    list_per_page = 25
    date_hierarchy = 'timestamp'

    def thread_id_display(self, obj):
        return obj.thread.id
    thread_id_display.short_description = _('Thread ID')
    thread_id_display.admin_order_field = 'thread__id'

    def sender_display(self, obj):
        return obj.sender.get_username() if obj.sender else _("System")
    sender_display.short_description = _('Sender')
    sender_display.admin_order_field = 'sender__username'


    def short_content(self, obj):
        return obj.content[:75] + '...' if len(obj.content) > 75 else obj.content
    short_content.short_description = _('Content')

    def read_by_count_display(self, obj):
        return obj.read_by.count()
    read_by_count_display.short_description = _('Read By Count')
