# apps/communications/signals.py
from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import Message
# Assuming emails.py is in the same app directory
from .emails import send_new_message_email_notification

# Import User model to handle potential sender=None case if needed, though Message model requires sender
# from django.conf import settings
# User = settings.AUTH_USER_MODEL # Not strictly needed if sender cannot be None

@receiver(post_save, sender=Message)
def new_message_created_notification(sender, instance, created, **kwargs):
    """
    Signal handler to send email notifications when a new message is created.
    """
    if created: # Only for new messages
        message = instance
        thread = message.thread
        message_sender = message.sender # User who sent this message (guaranteed by model)

        # Iterate over all participants in the thread
        for participant in thread.participants.all():
            # Don't send notification to the sender of this specific message
            if message_sender and participant.id == message_sender.id:
                continue

            # Optional: Check if user has already read this message
            # This check might be complex or less relevant for immediate email notifications.
            # If a user reads a message almost instantly, they might still get an email.
            # A more robust "unread" check might involve tracking last_seen_timestamp per user per thread.
            # For now, we'll notify for all new messages not sent by the recipient.
            # if message.read_by.filter(id=participant.id).exists():
            #    continue

            # TODO: Ideal place for asynchronous task call (e.g., Celery)
            # Example: send_new_message_email_notification_task.delay(participant.id, message_sender.id, thread.id, message.id)
            # This would require setting up Celery or another task queue.
            # For now, call synchronously as per the plan:

            print(f"Signal triggered: New message {message.id} in thread {thread.id}. Preparing to notify {participant.username}.")

            send_new_message_email_notification(
                recipient_user=participant,
                sender_user=message_sender, # message.sender is a User instance
                thread=thread,
                message=message
            )
            print(f"Signal handler finished processing for participant {participant.username}.")
        print(f"Signal handler new_message_created_notification completed for message {message.id}.")
