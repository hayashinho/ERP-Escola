from django.db import models
from django.conf import settings
from django.utils.translation import gettext_lazy as _
from django.utils import timezone # Needed for Message.save() to update thread

class MessageThread(models.Model):
    subject = models.CharField(
        _('subject'),
        max_length=255,
        blank=True,
        null=True,
        help_text=_('Optional subject for the conversation thread.')
    )
    participants = models.ManyToManyField(
        settings.AUTH_USER_MODEL,
        related_name='message_threads',
        verbose_name=_('participants')
    )
    created_at = models.DateTimeField(_('created at'), auto_now_add=True)
    updated_at = models.DateTimeField(_('updated at'), auto_now=True)

    class Meta:
        verbose_name = _('Message Thread')
        verbose_name_plural = _('Message Threads')
        ordering = ['-updated_at']
        app_label = 'communications' # Explicitly set app_label

    def __str__(self):
        if self.subject:
            return self.subject
        # Ensure participants related manager can be accessed even if instance is not fully loaded
        # or if participants haven't been added yet (e.g. during creation in some scenarios)
        if self.pk and self.participants.exists():
            participant_names = ", ".join([user.get_username() for user in self.participants.all()[:3]])
            return f"Thread with {participant_names}"
        return f"Thread {self.pk or 'New'}"


class Message(models.Model):
    thread = models.ForeignKey(
        MessageThread,
        on_delete=models.CASCADE,
        related_name='messages',
        verbose_name=_('thread')
    )
    sender = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True, # Allows messages to remain if sender's account is deleted
        blank=True, # For system messages or if sender is not a regular user
        related_name='sent_messages',
        verbose_name=_('sender')
    )
    content = models.TextField(_('content'))
    timestamp = models.DateTimeField(_('timestamp'), auto_now_add=True)
    read_by = models.ManyToManyField(
        settings.AUTH_USER_MODEL,
        related_name='read_messages',
        blank=True,
        verbose_name=_('read by')
    )

    class Meta:
        verbose_name = _('Message')
        verbose_name_plural = _('Messages')
        ordering = ['timestamp']
        app_label = 'communications' # Explicitly set app_label

    def __str__(self):
        sender_username = self.sender.get_username() if self.sender else "System"
        return f"Message from {sender_username} in thread {self.thread_id} at {self.timestamp}"

    def save(self, *args, **kwargs):
        is_new = self._state.adding
        super().save(*args, **kwargs) # Save first to get a Message ID and timestamp
        if is_new: # Only on first save
            if self.thread:
                # Update thread's updated_at timestamp
                # Use self.timestamp which is set by auto_now_add
                MessageThread.objects.filter(pk=self.thread.pk).update(updated_at=self.timestamp)

            # Automatically mark message as read by sender
            if self.sender:
                self.read_by.add(self.sender) # M2M add requires instance to have PK
