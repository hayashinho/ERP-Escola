from rest_framework import serializers
# from django.contrib.auth import get_user_model # Using direct import below
from django.contrib.contenttypes.models import ContentType
from apps.accounts.models import User # Consistent with project structure
from .models import AuditLog

# User = get_user_model() # Replaced by direct import

class AuditLogUserSerializer(serializers.ModelSerializer):
    """Simplified User serializer for audit log display."""
    class Meta:
        model = User
        fields = ['id', 'username', 'email']
        help_text = "Basic information about the user associated with an audit log entry."

class ContentTypeSerializer(serializers.ModelSerializer):
    """Serializer for ContentType model, showing app label and model name."""
    class Meta:
        model = ContentType
        fields = ['id', 'app_label', 'model']
        help_text = "Represents the content type (model) of a target object in an audit log."

class AuditLogSerializer(serializers.ModelSerializer):
    """
    Serializer for AuditLog entries, providing detailed read-only information.
    Used for displaying audit logs. All fields are read-only as logs are immutable.
    """
    user = AuditLogUserSerializer(read_only=True, help_text="The user who performed the action, if authenticated and available.")
    target_content_type = ContentTypeSerializer(read_only=True, help_text="The content type (model) of the object that was acted upon, if any.")
    action_type_display = serializers.CharField(source='get_action_type_display', read_only=True, help_text="Human-readable description of the action performed.")
    target_object_repr = serializers.CharField(read_only=True, help_text="String representation of the target object at the time of logging, if any.")
    details = serializers.JSONField(read_only=True, help_text="A JSON object containing additional, action-specific details about the logged event.")
    ip_address = serializers.IPAddressField(read_only=True, help_text="IP address from which the action was initiated, if available.")
    timestamp = serializers.DateTimeField(read_only=True, help_text="Date and time when the action occurred.")
    target_object_id = serializers.CharField(read_only=True, help_text="Primary key of the target object, if any.") # Model has CharField

    class Meta:
        model = AuditLog
        fields = [
            'id', 'user', 'action_type', 'action_type_display', 'timestamp',
            'ip_address', 'target_content_type', 'target_object_id',
            'target_object_repr', 'details'
        ]
        read_only_fields = fields # All fields are effectively read-only for this serializer
