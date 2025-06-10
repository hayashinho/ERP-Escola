from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase
from apps.accounts.models import User
from apps.communications.models import MessageThread, Message
from django.utils.translation import gettext_lazy as _ # For error messages if needed
from django.utils import timezone # For timestamp comparisons
from django.core import mail # For testing emails
from django.conf import settings # To access settings like SITE_URL, DEFAULT_FROM_EMAIL

# Import the email sending function to test directly or to mock
from .emails import send_new_message_email_notification


class MessageThreadViewSetTests(APITestCase):
    def setUp(self):
        self.user1 = User.objects.create_user(username='user1', email='user1@example.com', password='password123', user_type=User.USER_TYPE_TEACHER)
        self.user2 = User.objects.create_user(username='user2', email='user2@example.com', password='password123', user_type=User.USER_TYPE_PARENT)
        self.user3 = User.objects.create_user(username='user3', email='user3@example.com', password='password123', user_type=User.USER_TYPE_STUDENT)
        self.user_non_participant = User.objects.create_user(username='outsider', email='outsider@example.com', password='password123', user_type=User.USER_TYPE_STAFF)

        # URLs
        self.create_thread_url = reverse('communications:messagethread-create-thread-with-message') # Corrected URL name
        self.list_threads_url = reverse('communications:messagethread-list')

        # Authenticate as user1 by default
        self.client.force_authenticate(user=self.user1)

    def _create_thread_util(self, subject=None, participants_qs=None, first_message_content=None, sender=None):
        if sender is None:
            sender = self.user1 # Default sender

        thread_data = {}
        if subject:
            thread_data['subject'] = subject

        thread = MessageThread.objects.create(**thread_data)

        if participants_qs:
            thread.participants.set(participants_qs)
        else: # Default participants if none provided
            thread.participants.set([sender, self.user2])

        if first_message_content:
            Message.objects.create(thread=thread, sender=sender, content=first_message_content)
            # Message.save() handles thread.updated_at and sender read_by
        else:
            # Ensure thread.updated_at is set even if no initial message, for ordering tests
            thread.updated_at = timezone.now()
            thread.save(update_fields=['updated_at'])

        return thread

    # --- Test create_thread_with_message ---
    def test_create_thread_with_message_success(self):
        payload = {
            'recipients': [self.user2.pk, self.user3.pk],
            'content': "Hello team!",
            'subject': "Project Alpha"
        }
        response = self.client.post(self.create_thread_url, payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.data)
        self.assertEqual(response.data['subject'], "Project Alpha")

        thread_id = response.data['id']
        thread = MessageThread.objects.get(pk=thread_id)
        self.assertIn(self.user1, thread.participants.all())
        self.assertIn(self.user2, thread.participants.all())
        self.assertIn(self.user3, thread.participants.all())
        self.assertEqual(thread.messages.count(), 1)
        first_message = thread.messages.first()
        self.assertEqual(first_message.content, "Hello team!")
        self.assertEqual(first_message.sender, self.user1)
        self.assertIn(self.user1, first_message.read_by.all()) # Sender read their own message
        self.assertEqual(thread.updated_at, first_message.timestamp)

    def test_create_thread_without_subject(self):
        payload = {
            'recipients': [self.user2.pk],
            'content': "Hi User2"
        }
        response = self.client.post(self.create_thread_url, payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.data)
        self.assertIsNone(response.data['subject'])

    def test_create_thread_invalid_recipient_id(self):
        payload = {'recipients': [999], 'content': "Test"} # 999 is an invalid ID
        response = self.client.post(self.create_thread_url, payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('recipients', response.data)

    def test_create_thread_empty_recipients(self):
        payload = {'recipients': [], 'content': "Test"}
        response = self.client.post(self.create_thread_url, payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('recipients', response.data)

    def test_create_thread_no_content(self):
        payload = {'recipients': [self.user2.pk]}
        response = self.client.post(self.create_thread_url, payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('content', response.data)

    def test_create_thread_with_self_in_recipients(self):
        payload = {'recipients': [self.user1.pk, self.user2.pk], 'content': "Test"}
        response = self.client.post(self.create_thread_url, payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('recipients', response.data)

    # --- Test list threads ---
    def test_list_threads_for_participant(self):
        thread1 = self._create_thread_util(participants_qs=[self.user1, self.user2], first_message_content="Thread 1 msg 1", sender=self.user1)
        # Ensure thread1 is 'older' for updated_at sorting initially
        thread1.updated_at = timezone.now() - timezone.timedelta(minutes=5)
        thread1.save()

        msg_t1_u2 = Message.objects.create(thread=thread1, sender=self.user2, content="Thread 1 msg 2")
        # This will update thread1.updated_at to msg_t1_u2.timestamp

        thread2 = self._create_thread_util(participants_qs=[self.user1, self.user3], first_message_content="Thread 2 msg 1", sender=self.user3)
        # This will have a later updated_at than thread1's creation, but potentially earlier than msg_t1_u2

        # To ensure order for test, manually set updated_at if needed or rely on message creation order
        if thread1.updated_at < thread2.updated_at: # if thread1 (after user2's message) is still older
            thread1.updated_at = timezone.now() # Make thread1 most recent
            thread1.save()
        else: # thread2 is older or same
            thread2.updated_at = timezone.now() - timezone.timedelta(minutes=1) # Make thread2 older
            thread2.save()


        self._create_thread_util(participants_qs=[self.user2, self.user3]) # User1 not in this thread

        response = self.client.get(self.list_threads_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 2)

        # Check ordering by updated_at (most recent first)
        # This depends on which thread was made most recent by the logic above
        most_recent_thread_id = thread1.id if thread1.updated_at > thread2.updated_at else thread2.id
        self.assertEqual(response.data[0]['id'], most_recent_thread_id)

        # Check unread count for thread1 (user1 should have read their own message, but not user2's)
        thread1_data = next(item for item in response.data if item['id'] == thread1.id)
        self.assertEqual(thread1_data['unread_count'], 1 if msg_t1_u2.sender != self.user1 else 0)
        self.assertIsNotNone(thread1_data['last_message'])
        self.assertEqual(thread1_data['last_message']['content'][:100], "Thread 1 msg 2")

        # Check unread count for thread2 (user1 has not read the first message by user3)
        thread2_data = next(item for item in response.data if item['id'] == thread2.id)
        self.assertEqual(thread2_data['unread_count'], 1)


    # --- Test retrieve thread ---
    def test_retrieve_thread_participant(self):
        thread = self._create_thread_util()
        detail_url = reverse('communications:messagethread-detail', kwargs={'pk': thread.pk})
        response = self.client.get(detail_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['id'], thread.id)

    def test_retrieve_thread_non_participant(self):
        thread = self._create_thread_util(participants_qs=[self.user2, self.user3])
        detail_url = reverse('communications:messagethread-detail', kwargs={'pk': thread.pk})
        response = self.client.get(detail_url)
        self.assertIn(response.status_code, [status.HTTP_403_FORBIDDEN, status.HTTP_404_NOT_FOUND])

    # --- Test list_messages_in_thread ---
    def test_list_messages_in_thread_marks_as_read(self):
        thread = self._create_thread_util(participants_qs=[self.user1, self.user2])
        msg1 = Message.objects.create(thread=thread, sender=self.user2, content="Unread message 1 for user1")
        msg2 = Message.objects.create(thread=thread, sender=self.user2, content="Unread message 2 for user1")

        messages_url = reverse('communications:messagethread-list-messages-in-thread', kwargs={'pk': thread.pk})

        self.assertFalse(msg1.read_by.filter(pk=self.user1.pk).exists())
        self.assertFalse(msg2.read_by.filter(pk=self.user1.pk).exists())

        response = self.client.get(messages_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 2)

        msg1.refresh_from_db()
        msg2.refresh_from_db()
        self.assertTrue(msg1.read_by.filter(pk=self.user1.pk).exists())
        self.assertTrue(msg2.read_by.filter(pk=self.user1.pk).exists())

    # --- Test reply_to_thread ---
    def test_reply_to_thread_success(self):
        thread = self._create_thread_util(first_message_content="Initial message by user1", sender=self.user1)
        reply_url = reverse('communications:messagethread-reply-to-thread', kwargs={'pk': thread.pk})
        payload = {'content': "This is a reply"}

        response = self.client.post(reply_url, payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.data)
        self.assertEqual(response.data['content'], "This is a reply")
        self.assertEqual(response.data['sender']['id'], self.user1.id)

        thread.refresh_from_db() # Refresh to get updated_at
        self.assertEqual(thread.messages.count(), 2) # Initial + reply
        last_message = thread.messages.latest('timestamp')
        self.assertEqual(last_message.content, "This is a reply")
        self.assertEqual(thread.updated_at, last_message.timestamp)

    def test_reply_to_thread_non_participant(self):
        thread = self._create_thread_util(participants_qs=[self.user2, self.user3])
        reply_url = reverse('communications:messagethread-reply-to-thread', kwargs={'pk': thread.pk})
        payload = {'content': "Trying to reply"}
        response = self.client.post(reply_url, payload, format='json')
        self.assertIn(response.status_code, [status.HTTP_403_FORBIDDEN, status.HTTP_404_NOT_FOUND])

    # --- Test partial_update (subject) ---
    def test_update_thread_subject_participant(self):
        thread = self._create_thread_util(subject="Old Subject")
        old_updated_at = thread.updated_at
        detail_url = reverse('communications:messagethread-detail', kwargs={'pk': thread.pk})
        payload = {'subject': "New Subject"}

        # Make sure some time passes for updated_at to be different
        import time; time.sleep(0.01)

        response = self.client.patch(detail_url, payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
        self.assertEqual(response.data['subject'], "New Subject")
        thread.refresh_from_db()
        self.assertEqual(thread.subject, "New Subject")
        self.assertTrue(thread.updated_at > old_updated_at)

    # --- Test leave_thread ---
    def test_leave_thread_success(self):
        thread = self._create_thread_util(participants_qs=[self.user1, self.user2, self.user3])
        leave_url = reverse('communications:messagethread-leave-thread', kwargs={'pk': thread.pk})

        response = self.client.post(leave_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
        thread.refresh_from_db()
        self.assertNotIn(self.user1, thread.participants.all())
        self.assertEqual(thread.participants.count(), 2)

    def test_leave_thread_last_participant_deletes_thread(self):
        thread = self._create_thread_util(participants_qs=[self.user1])
        leave_url = reverse('communications:messagethread-leave-thread', kwargs={'pk': thread.pk})

        response = self.client.post(leave_url)
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(MessageThread.objects.filter(pk=thread.pk).exists())

    # --- Test mark_message_as_read ---
    def test_mark_message_as_read(self):
        thread = self._create_thread_util(participants_qs=[self.user1, self.user2])
        message = Message.objects.create(thread=thread, sender=self.user2, content="A message for user1")
        self.assertFalse(message.read_by.filter(pk=self.user1.pk).exists())

        mark_read_url = reverse('communications:messagethread-mark-message-read-action', kwargs={'pk': thread.pk}) # Use new url_name
        payload = {'message_id': message.pk}
        response = self.client.post(mark_read_url, payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT, response.data) # Expect 204

        message.refresh_from_db()
        self.assertTrue(message.read_by.filter(pk=self.user1.pk).exists())

    # --- Test disabled actions ---
    def test_put_on_thread_not_allowed(self):
        thread = self._create_thread_util()
        detail_url = reverse('communications:messagethread-detail', kwargs={'pk': thread.pk})
        response = self.client.put(detail_url, {'subject': 'Attempt PUT'}, format='json')
        self.assertEqual(response.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)

    def test_delete_on_thread_not_allowed(self):
        thread = self._create_thread_util()
        detail_url = reverse('communications:messagethread-detail', kwargs={'pk': thread.pk})
        response = self.client.delete(detail_url)
        self.assertEqual(response.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)


class MessageNotificationTests(APITestCase):
    def setUp(self):
        self.sender = User.objects.create_user(username='testsender', email='sender@example.com', password='password123', first_name="Test", last_name="Sender")
        self.recipient1 = User.objects.create_user(username='recipient1', email='recipient1@example.com', password='password123', first_name="Rec", last_name="One")
        self.recipient2 = User.objects.create_user(username='recipient2', email='recipient2@example.com', password='password123', first_name="Rec", last_name="Two")
        self.recipient_no_email = User.objects.create_user(username='noemailuser', email='', password='password123')

        self.thread = MessageThread.objects.create(subject="Test Notification Thread")
        self.thread.participants.set([self.sender, self.recipient1, self.recipient2, self.recipient_no_email])

    def test_send_new_message_email_notification_direct_call(self):
        """Test the email sending function directly."""
        message_content = "This is a direct test of the email notification function. It's a bit long to check snippeting."
        message = Message(
            thread=self.thread,
            sender=self.sender,
            content=message_content
        ) # Not saved, just for data

        send_new_message_email_notification(
            recipient_user=self.recipient1,
            sender_user=self.sender,
            thread=self.thread,
            message=message
        )

        self.assertEqual(len(mail.outbox), 1)
        email = mail.outbox[0]
        self.assertEqual(email.to, [self.recipient1.email])
        self.assertEqual(email.subject, "You have a new message in ERP Escolar")
        self.assertIn(f"Hi {self.recipient1.get_full_name()}", email.body)
        self.assertIn(f"from {self.sender.get_full_name()}", email.body)
        self.assertIn(f"regarding '{self.thread.subject}'", email.body)
        # Correctly determine expected snippet based on message content length
        expected_snippet = message_content[:100] + ('...' if len(message_content) > 100 else '')
        self.assertIn(f"Snippet: \"{expected_snippet}\"", email.body)
        self.assertIn(settings.SITE_URL.rstrip('/') + '/login/', email.body)

    def test_send_new_message_email_notification_no_recipient_email(self):
        """Test that no email is sent if recipient has no email."""
        message = Message(thread=self.thread, sender=self.sender, content="Test content")

        send_new_message_email_notification(
            recipient_user=self.recipient_no_email,
            sender_user=self.sender,
            thread=self.thread,
            message=message
        )
        self.assertEqual(len(mail.outbox), 0)

    def test_new_message_created_signal_sends_emails(self):
        """Test the signal handler for new message creation."""
        # This message creation will trigger the post_save signal
        new_message = Message.objects.create(
            thread=self.thread,
            sender=self.sender,
            content="Hello everyone, this is a test message via signal!"
        )

        # Expect emails to recipient1 and recipient2
        # Sender and recipient_no_email should not receive one.
        self.assertEqual(len(mail.outbox), 2)

        emails_sent_to = sorted([email.to[0] for email in mail.outbox])
        expected_recipients = sorted([self.recipient1.email, self.recipient2.email])
        self.assertEqual(emails_sent_to, expected_recipients)

        # Check content of one email (e.g., to recipient1)
        email_to_recipient1 = next(e for e in mail.outbox if self.recipient1.email in e.to)
        self.assertIn(f"Hi {self.recipient1.get_full_name()}", email_to_recipient1.body)
        self.assertIn(f"from {self.sender.get_full_name()}", email_to_recipient1.body)
        self.assertIn(new_message.content[:100], email_to_recipient1.body)

    def test_signal_does_not_send_to_message_sender(self):
        """Ensure the sender of the message doesn't get an email for their own message."""
        # Create a new thread where only sender and recipient1 are participants initially
        # to simplify checking who receives what.
        thread_minimal = MessageThread.objects.create(subject="Minimal Thread")
        thread_minimal.participants.set([self.sender, self.recipient1])

        Message.objects.create(
            thread=thread_minimal,
            sender=self.sender, # self.sender sends the message
            content="A message from sender to recipient1"
        )

        self.assertEqual(len(mail.outbox), 1) # Only one email should be sent
        self.assertEqual(mail.outbox[0].to, [self.recipient1.email]) # To recipient1

        # Clear outbox
        mail.outbox = []

        # Now recipient1 sends a message
        Message.objects.create(
            thread=thread_minimal,
            sender=self.recipient1, # self.recipient1 sends the message
            content="A reply from recipient1 to sender"
        )
        self.assertEqual(len(mail.outbox), 1) # Only one email
        self.assertEqual(mail.outbox[0].to, [self.sender.email]) # To self.sender
