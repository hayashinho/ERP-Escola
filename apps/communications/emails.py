# apps/communications/emails.py
from django.core.mail import send_mail
from django.conf import settings
from django.template.loader import render_to_string # If using templates
from django.utils.translation import gettext_lazy as _

# Assuming User model is in apps.accounts.models
from apps.accounts.models import User

def send_new_message_email_notification(recipient_user, sender_user, thread, message):
    """
    Sends an email notification to a recipient about a new message.
    """
    if not recipient_user.email:
        # Cannot send email if user has no email address
        # Optionally, log this event or handle it as needed
        print(f"User {recipient_user.username} has no email address. Skipping notification.") # Simple print for dev
        return

    subject = _("You have a new message in ERP Escolar")

    # Determine sender name safely
    if sender_user:
        sender_name = sender_user.get_full_name() or sender_user.username
    else:
        # Handle cases where sender might be None (e.g., system messages, though current model requires sender)
        sender_name = _("System Notification")

    thread_subject_display = thread.subject if thread.subject else _("a new conversation")
    message_content_snippet = message.content[:100] + ('...' if len(message.content) > 100 else '')

    # Construct login URL, ensuring SITE_URL ends with a slash and login path starts without one
    site_url = settings.SITE_URL.rstrip('/')
    login_path = 'login/' # Assuming this is the path; adjust if different
    full_login_url = f"{site_url}/{login_path}"

    context = {
        'recipient_name': recipient_user.get_full_name() or recipient_user.username,
        'sender_name': sender_name,
        'thread_subject': thread_subject_display,
        'message_content_snippet': message_content_snippet,
        'login_url': full_login_url,
        'site_name': _("ERP Escolar"), # Example site name
    }

    # Simple text body (can be replaced with render_to_string for a template)
    # Using f-strings for clarity here; consider Django templates for more complex emails
    body = _(
        "Hi {recipient_name},\n\n"
        "You have received a new message from {sender_name} "
        "regarding '{thread_subject}'.\n\n"
        "Snippet: \"{message_content_snippet}\"\n\n"
        "Please log in to {site_name} to view your messages: {login_url}\n\n"
        "Thank you."
    ).format(**context)

    # For development, this will print to console due to EMAIL_BACKEND setting
    try:
        send_mail(
            subject,
            body,
            settings.DEFAULT_FROM_EMAIL,
            [recipient_user.email],
            fail_silently=False, # Set to True in production if some failures are okay
        )
        print(f"Email notification sent to {recipient_user.email} (printed to console)") # For dev feedback
    except Exception as e:
        # Log the exception in a real application
        print(f"Error sending email to {recipient_user.email}: {e}")
