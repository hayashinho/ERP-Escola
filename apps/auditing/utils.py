from django.contrib.contenttypes.models import ContentType
from .models import AuditLog # Assuming AuditLog is in the same app

def get_client_ip(request):
    if not request:
        return None
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        ip = x_forwarded_for.split(',')[0].strip()
    else:
        ip = request.META.get('REMOTE_ADDR')
    return ip

def log_action(user, action_type, request=None, target_object=None, details=None, target_object_repr_override=None):
    ip_address = get_client_ip(request) if request else None

    target_ct = None
    target_id = None
    target_repr = target_object_repr_override # Use override if provided

    if target_object:
        target_ct = ContentType.objects.get_for_model(target_object)
        target_id = str(target_object.pk) # Ensure PK is string for CharField target_object_id
        if target_repr is None: # Only use object's __str__ if no override
            try:
                target_repr = str(target_object)[:255] # Limit length
            except Exception:
                target_repr = f"Object of type {target_ct.model if target_ct else 'Unknown'}"


    AuditLog.objects.create(
        user=user if user and user.is_authenticated else None,
        action_type=action_type,
        ip_address=ip_address,
        target_content_type=target_ct,
        target_object_id=target_id,
        target_object_repr=target_repr,
        details=details or {} # Ensure details is at least an empty dict
    )
