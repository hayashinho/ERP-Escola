from rest_framework import serializers
from django.conf import settings
# Assuming User is in apps.accounts.models based on prior work:
from apps.accounts.models import User
from .models import MessageThread, Message
from django.utils.translation import gettext_lazy as _

class MessageUserSerializer(serializers.ModelSerializer):
    """Serializer for basic user representation in messaging."""
    full_name = serializers.CharField(source='get_full_name', read_only=True, help_text=_("Full name of the user."))
    class Meta:
        model = User
        fields = ['id', 'username', 'full_name']
        help_text = _("Basic user information including ID, username, and full name.")

class MessageSerializer(serializers.ModelSerializer):
    """
    Serializer for individual messages.
    Sender and thread are typically set by the view logic, not direct client input here.
    'read_by' is managed by system based on access.
    """
    sender = MessageUserSerializer(read_only=True, help_text=_("The user who sent the message. Set by the system."))
    content = serializers.CharField(help_text=_("Text content of the message."))
    read_by = MessageUserSerializer(many=True, read_only=True, help_text=_("List of users who have read this message."))
    thread = serializers.PrimaryKeyRelatedField(queryset=MessageThread.objects.all(), help_text=_("ID of the thread this message belongs to. Required when replying directly to a thread if not set by URL."))


    class Meta:
        model = Message
        fields = ['id', 'thread', 'sender', 'content', 'timestamp', 'read_by']
        read_only_fields = ['timestamp', 'sender', 'read_by']
        # 'thread' is writable for replies if not set by URL, but usually set by view.
        # For 'reply_to_thread' action, 'thread' is taken from URL.
        # For a hypothetical direct message creation endpoint, 'thread' would be required.

    # def get_is_read_by_current_user(self, obj):
    #     # Example: Check if current user (from context) is in obj.read_by.all()
    #     user = self.context.get('request').user if self.context.get('request') else None
    #     if user and user.is_authenticated:
    #         return obj.read_by.filter(id=user.id).exists()
    #     return False


class MessageThreadListSerializer(serializers.ModelSerializer):
    """
    Serializer for listing message threads with summary information.
    Includes details like the last message, unread count for the current user,
    and information about other participants if the subject is empty.
    """
    participants = MessageUserSerializer(many=True, read_only=True, help_text=_("List of users participating in this thread."))
    subject = serializers.CharField(read_only=True, help_text=_("Subject of the message thread, if any."))
    last_message = serializers.SerializerMethodField(method_name='get_last_message_typed', help_text=_("A snippet of the last message in the thread, including sender and timestamp."))
    unread_count = serializers.SerializerMethodField(method_name='get_unread_count_typed', help_text=_("Number of unread messages for the current authenticated user in this thread."))
    first_participant_for_subject = serializers.SerializerMethodField(method_name='get_first_participant_for_subject_typed', help_text=_("If the thread has no subject, this provides details of the first other participant to help identify the chat (e.g., 'Chat with User X')."))
    created_at = serializers.DateTimeField(read_only=True, help_text=_("Timestamp of when the thread was created."))
    updated_at = serializers.DateTimeField(read_only=True, help_text=_("Timestamp of the last activity in the thread (e.g., new message)."))

    class Meta:
        model = MessageThread
        fields = [
            'id', 'subject', 'participants', 'created_at', 'updated_at',
            'last_message', 'unread_count', 'first_participant_for_subject'
        ]
        read_only_fields = ['created_at', 'updated_at'] # Already implied by field definitions above

    def get_last_message_typed(self, obj: MessageThread) -> dict | None:
        last_msg = obj.messages.order_by('-timestamp').first()
        if last_msg:
            return {
                'content': last_msg.content[:100], # Snippet
                'sender_username': last_msg.sender.get_username() if last_msg.sender else "System",
                'timestamp': last_msg.timestamp
            }
        return None

    def get_unread_count_typed(self, obj: MessageThread) -> int:
        user = self.context.get('request').user if self.context.get('request') else None
        if user and user.is_authenticated:
            # Ensure messages related_name is 'messages' and sender has 'read_by' M2M
            return obj.messages.exclude(read_by=user).count()
        return 0

    def get_first_participant_for_subject_typed(self, obj: MessageThread) -> dict | None:
        user = self.context.get('request').user if self.context.get('request') else None
        if not obj.subject and user and user.is_authenticated:
            first_other_participant = obj.participants.exclude(id=user.id).first()
            if first_other_participant:
                return MessageUserSerializer(first_other_participant).data
        return None


class MessageThreadDetailSerializer(serializers.ModelSerializer):
    """
    Serializer for the detailed view of a message thread.
    Primarily shows participants and subject. Messages are typically handled by a separate endpoint.
    """
    participants = MessageUserSerializer(many=True, read_only=True, help_text=_("List of users participating in this thread."))
    subject = serializers.CharField(read_only=True, help_text=_("Subject of the message thread, if any."))
    created_at = serializers.DateTimeField(read_only=True, help_text=_("Timestamp of when the thread was created."))
    updated_at = serializers.DateTimeField(read_only=True, help_text=_("Timestamp of the last activity in the thread."))


    class Meta:
        model = MessageThread
        fields = ['id', 'subject', 'participants', 'created_at', 'updated_at']
        read_only_fields = ['created_at', 'updated_at']


class MessageThreadCreateSerializer(serializers.Serializer):
    """Serializer for creating a new message thread along with its initial message."""
    recipients = serializers.ListField(
        child=serializers.PrimaryKeyRelatedField(queryset=User.objects.all(), help_text=_("User ID of a recipient.")),
        write_only=True,
        required=True,
        help_text=_("A list of user IDs for the recipients of the initial message.")
    )
    content = serializers.CharField(write_only=True, required=True, help_text=_("The content of the initial message."))
    subject = serializers.CharField(required=False, allow_blank=True, max_length=255, write_only=True, help_text=_("An optional subject for the new message thread."))

    def validate_recipients(self, value):
        if not value:
            raise serializers.ValidationError(_("Recipients list cannot be empty."))

        # Value is already a list of User instances due to PrimaryKeyRelatedField
        # No need to check if users exist again.

        request_user = self.context.get('request').user
        if request_user and request_user in value: # Check if sender User instance is in list of recipient User instances
            raise serializers.ValidationError(_("You cannot include yourself in the recipients list."))
        return value
