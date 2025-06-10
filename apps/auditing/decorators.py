import functools
from .utils import log_action
from .models import AuditLog # AuditLog might be used if action_types are directly referenced

def audit_view_action(action_type, target_object_getter=None, details_extractor=None):
    """
    Decorator to log an audit action when a view method is successfully executed.

    Args:
        action_type (str): The type of action to log (e.g., AuditLog.ACTION_EXPORTED).
        target_object_getter (callable, optional): A function that takes (view_instance, *args, **kwargs)
                                                   and returns the target object for auditing.
        details_extractor (callable, optional): A function that takes (view_instance, request, response, *args, **kwargs)
                                                and returns a dictionary of details to log.
    """
    def decorator(func):
        @functools.wraps(func)
        def wrapper(view_instance, request, *args, **kwargs):
            response = func(view_instance, request, *args, **kwargs)

            # Log only for successful actions (e.g., 2xx status codes)
            if 200 <= response.status_code < 300:
                target_object = None
                if target_object_getter:
                    try:
                        # Pass necessary arguments to the getter
                        # For class-based views, args might be empty, kwargs contain URL params
                        target_object = target_object_getter(view_instance, request, *args, **kwargs)
                    except Exception:
                        # Log or handle error in getter if necessary
                        target_object = None

                details = None
                if details_extractor:
                    try:
                        details = details_extractor(view_instance, request, response, *args, **kwargs)
                    except Exception:
                        details = {"error": "Failed to extract details for audit log"}

                log_action(
                    user=request.user if request.user.is_authenticated else None,
                    action_type=action_type,
                    request=request, # Pass the whole request for IP etc.
                    target_object=target_object,
                    details=details
                )
            return response
        return wrapper
    return decorator
