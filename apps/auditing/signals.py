from django.contrib.auth.signals import user_logged_in, user_logged_out, user_login_failed
from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from django.conf import settings

from apps.accounts.models import User # Direct import as per established project pattern
from apps.students.models import Student
from apps.academics.models import Enrollment, Announcement, SchoolClass, SchoolYear, Subject, Grade, Attendance, DidacticMaterial, TeacherAssignment, GradingPeriod
from apps.communications.models import MessageThread, Message
# Assuming Financials models might also be relevant
from apps.financials.models import Fee, Payment

from .utils import log_action
from .models import AuditLog

# For trying to get request context in signals (advanced, needs middleware like django-crum)
# try:
#     from crum import get_current_request
# except ImportError:
#     get_current_request = None

# def get_actor_and_request():
#     """Helper to get current user and request from thread local storage if available."""
#     request = None
#     user = None
#     if get_current_request:
#         request = get_current_request()
#         if request and hasattr(request, 'user') and request.user.is_authenticated:
#             user = request.user
#     return user, request

@receiver(user_logged_in)
def log_user_login(sender, request, user, **kwargs):
    log_action(user, AuditLog.ACTION_LOGIN_SUCCESS, request=request, details={'username': user.get_username()})

@receiver(user_login_failed)
def log_user_login_failed(sender, credentials, request, **kwargs):
    username_attempted = credentials.get('username', 'Unknown') if credentials else 'Unknown'
    log_action(
        user=None,
        action_type=AuditLog.ACTION_LOGIN_FAILED,
        request=request,
        details={'attempted_username': username_attempted}
    )

@receiver(user_logged_out)
def log_user_logout(sender, request, user, **kwargs):
    # User might be None if session expired. If user is None, request.user might also be AnonymousUser.
    current_user = user if user and user.is_authenticated else None
    log_action(current_user, AuditLog.ACTION_LOGOUT, request=request, details={'username': current_user.get_username() if current_user else 'N/A'})

# Define a more comprehensive list of models to audit
MODELS_TO_AUDIT = [
    User, Student, Enrollment, Announcement, MessageThread, Message,
    SchoolClass, SchoolYear, Subject, Grade, Attendance, DidacticMaterial,
    TeacherAssignment, GradingPeriod, Fee, Payment
    # Add UserProfile if direct changes to it are significant
    # from apps.accounts.models import UserProfile
    # UserProfile,
]

def get_changed_data_simple(instance):
    """
    A very simple way to represent changes.
    Does not store old/new values. Just indicates that an update happened.
    For more detailed diff, a more complex approach or a library like django-dirtyfields
    would be needed, along with careful handling in signals.
    """
    return {"message": "Object updated. Specific field changes are not detailed in this log entry."}

@receiver(post_save)
def log_post_save(sender, instance, created, using, update_fields, **kwargs):
    if sender in MODELS_TO_AUDIT:
        # Attempt to determine the actor (user performing the action)
        # This is challenging in signals. For now, we log None if not directly available.
        # A middleware like django-crum could make request.user available via thread locals.
        actor = None
        request = None # We don't have request here
        # if get_current_request: # If using django-crum or similar
        #    request = get_current_request()
        #    if request and hasattr(request, 'user') and request.user.is_authenticated:
        #        actor = request.user

        action = AuditLog.ACTION_CREATED if created else AuditLog.ACTION_UPDATED
        details_data = {}
        if not created:
            details_data = {"updated_fields": list(update_fields) if update_fields else "N/A"}
        else:
            details_data = {"message": "Object created."}

        log_action(
            user=actor, # Will be None unless a mechanism to get current user is implemented
            action_type=action,
            request=request, # Will be None
            target_object=instance,
            details=details_data
        )

@receiver(post_delete)
def log_post_delete(sender, instance, using, **kwargs):
    if sender in MODELS_TO_AUDIT:
        actor = None # Same challenge as in post_save for actor and request
        request = None
        # if get_current_request:
        #    request = get_current_request()
        #    if request and hasattr(request, 'user') and request.user.is_authenticated:
        #        actor = request.user

        # For delete, target_object_repr is important as the object is gone.
        # log_action already handles str(instance) for target_object_repr.
        log_action(
            user=actor,
            action_type=AuditLog.ACTION_DELETED,
            request=request,
            target_object=instance, # log_action will get its repr before it's truly gone from DB context
            details={"message": "Object deleted."}
        )

# Note: For a production system, reliably getting the 'actor' in post_save/post_delete
# often requires middleware (e.g., django-crum) to store the current request/user
# in thread-local storage so signals can access it. The provided solution will log
# these actions with user=None unless actor can be inferred differently.
# The 'get_changed_data' function for post_save is also simplified; a full diff is complex.
