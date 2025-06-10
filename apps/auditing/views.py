from rest_framework import viewsets, permissions, filters
from django_filters.rest_framework import DjangoFilterBackend # Correct import
from .models import AuditLog
from .serializers import AuditLogSerializer
from .utils import log_action # Keep existing utils if any, though not used by ViewSet directly
from .decorators import audit_view_action # Keep existing decorators if any

class AuditLogViewSet(viewsets.ReadOnlyModelViewSet):
    """
    Provides read-only access to AuditLog entries.

    Audit logs record various actions performed within the system, such as user logins,
    object creations, updates, deletions, and specific view accesses.

    **Permissions:** Requires admin user status.

    **Supported Actions:**
    - `list`: Retrieve a paginated list of audit log entries.
      Supports extensive filtering (by user, action type, timestamp, IP, target model, etc.)
      and searching across multiple fields.
    - `retrieve`: Get details of a specific audit log entry by its ID.

    All data is read-only as audit logs are immutable once created.
    """
    queryset = AuditLog.objects.all().select_related('user', 'target_content_type').order_by('-timestamp')
    serializer_class = AuditLogSerializer
    permission_classes = [permissions.IsAdminUser]

    filter_backends = [
        DjangoFilterBackend,
        filters.SearchFilter,
        filters.OrderingFilter
    ]
    filterset_fields = {
        'user__username': ['exact', 'icontains'],
        'user__email': ['exact', 'icontains'],
        'action_type': ['exact', 'in'],
        'timestamp': ['date', 'year', 'month', 'day', 'gte', 'lte', 'range'],
        'ip_address': ['exact', 'startswith'],
        'target_content_type__app_label': ['exact'],
        'target_content_type__model': ['exact'],
        'target_object_id': ['exact'],
    }
    search_fields = [
        'user__username',
        'user__email',
        'action_type',
        'target_object_repr',
        'ip_address',
        'details', # Basic search on JSONField (may cast to text, db dependent)
    ]
    ordering_fields = ['timestamp', 'user__username', 'action_type']
    # Default ordering is already set in queryset.
