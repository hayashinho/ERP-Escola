from rest_framework import viewsets, status, generics
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.shortcuts import get_object_or_404
from django.db.models import Q, OuterRef, Subquery, Count, Prefetch
# from django.contrib.auth import get_user_model # Using direct import
from apps.accounts.models import User
from .models import MessageThread, Message
from .serializers import (
    MessageThreadListSerializer,
    MessageThreadDetailSerializer,
    MessageThreadCreateSerializer,
    MessageSerializer
)
from .permissions import IsParticipantInThread
from django.utils import timezone # For updating thread timestamp manually if needed
from django.utils.translation import gettext_lazy as _


class MessageThreadViewSet(viewsets.ModelViewSet):
    """
    Manages message threads and their messages.

    Provides functionality for:
    - Listing threads for the current authenticated user.
    - Creating new threads with an initial message.
    - Retrieving details of a specific thread.
    - Listing messages within a thread (marks messages as read for the user).
    - Replying to an existing thread.
    - Updating the subject of a thread.
    - Allowing users to leave a thread.
    - Marking individual messages as read.
    """
    queryset = MessageThread.objects.none() # Default queryset, get_queryset will override
    permission_classes = [IsAuthenticated, IsParticipantInThread]

    def get_serializer_class(self):
        if self.action == 'list':
            return MessageThreadListSerializer
        if self.action == 'retrieve':
            return MessageThreadDetailSerializer
        if self.action == 'create_thread_with_message':
            return MessageThreadCreateSerializer
        if self.action in ['reply_to_thread', 'list_messages_in_thread', 'mark_message_as_read']: # Added mark_message_as_read
            return MessageSerializer
        return MessageThreadDetailSerializer # Default for other actions like partial_update

    def get_queryset(self):
        """
        Returns MessageThreads where the current authenticated user is a participant.
        Results are ordered by the most recently updated thread first.
        Includes prefetching of participant details and the latest messages for efficiency.
        """
        # Users should only see threads they are participants in
        # Prefetch related objects for optimization
        return MessageThread.objects.filter(participants=self.request.user).prefetch_related(
            Prefetch('participants', queryset=User.objects.only('id', 'username', 'first_name', 'last_name')),
            Prefetch('messages', queryset=Message.objects.order_by('-timestamp').select_related('sender'))
        ).distinct().order_by('-updated_at')

    @action(detail=False, methods=['post'], url_path='create-thread')
    def create_thread_with_message(self, request):
        """
        Creates a new message thread and posts the initial message.

        Payload requires:
        - `recipients`: A list of user IDs for other participants.
        - `content`: The text content of the first message.
        - `subject` (optional): Subject for the thread.

        The authenticated user making the request is automatically added as a participant and sender.
        Returns the details of the newly created thread.
        """
        serializer = self.get_serializer(data=request.data, context={'request': request})
        serializer.is_valid(raise_exception=True)
        validated_data = serializer.validated_data

        recipient_users = validated_data.get('recipients')
        content = validated_data.get('content')
        subject = validated_data.get('subject', None)
        sender = request.user

        all_participants = list(set([sender] + recipient_users))

        # Note: Logic to find and reuse existing threads with the same participants could be added here.
        # For simplicity, we always create a new thread.

        thread = MessageThread.objects.create(subject=subject)
        thread.participants.set(all_participants)

        Message.objects.create(
            thread=thread,
            sender=sender,
            content=content
        )
        # Message.save() handles adding sender to read_by and updating thread.updated_at

        thread_serializer = MessageThreadDetailSerializer(thread, context={'request': request})
        return Response(thread_serializer.data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=['post'], url_path='reply')
    def reply_to_thread(self, request, pk=None):
        """
        Posts a reply (a new message) to the specified message thread (by thread ID in URL).
        The authenticated user must be a participant of the thread.

        Payload requires:
        - `content`: The text content of the reply message.

        Returns the details of the created message.
        """
        thread = self.get_object()
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        message = serializer.save(sender=request.user, thread=thread)

        return Response(MessageSerializer(message, context={'request': request}).data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=['get'], url_path='messages')
    def list_messages_in_thread(self, request, pk=None):
        """
        Retrieves the list of messages for a specific thread (by thread ID in URL).
        The authenticated user must be a participant.
        Accessing messages via this endpoint will mark them as read by the current user.
        Messages are ordered by timestamp (oldest first).
        Supports pagination.
        """
        thread = self.get_object()

        messages_qs = thread.messages.all().order_by('timestamp').select_related(
            'sender' # For MessageUserSerializer in MessageSerializer
        ).prefetch_related('read_by')

        # Mark messages as read by the current user for this thread
        messages_to_mark_as_read = []
        for msg in messages_qs: # Iterate over queryset to use prefetched read_by
            if not msg.read_by.filter(pk=request.user.pk).exists():
                 messages_to_mark_as_read.append(msg)

        if messages_to_mark_as_read:
            # Using bulk_create for the through model for efficiency
            MessageRead = Message.read_by.through
            batch = [
                MessageRead(message_id=msg.id, user_id=request.user.id)
                for msg in messages_to_mark_as_read
            ]
            MessageRead.objects.bulk_create(batch, ignore_conflicts=True)

        # Apply pagination
        # Assuming pagination is configured globally or in settings for ModelViewSet
        # If using a specific pagination class for this endpoint:
        # from rest_framework.pagination import PageNumberPagination
        # paginator = PageNumberPagination()
        # paginator.page_size = 20 # Example page size
        page = self.paginate_queryset(messages_qs)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)

        serializer = self.get_serializer(messages_qs, many=True)
        return Response(serializer.data)

    def update(self, request, *args, **kwargs):
        return Response(status=status.HTTP_405_METHOD_NOT_ALLOWED)

    def partial_update(self, request, *args, **kwargs):
        """
        Partially updates a message thread.
        Currently, only allows updating the 'subject' of the thread.
        The user must be a participant.
        """
        instance = self.get_object()
        new_subject = request.data.get('subject')

        if new_subject is not None:
            if not isinstance(new_subject, str):
                 return Response({'subject': [_('Subject must be a string.')]}, status=status.HTTP_400_BAD_REQUEST)

            instance.subject = new_subject
            instance.updated_at = timezone.now()
            instance.save(update_fields=['subject', 'updated_at'])
            return Response(MessageThreadDetailSerializer(instance, context={'request': request}).data)

        return Response({'error': _('Subject field not provided or is invalid.')}, status=status.HTTP_400_BAD_REQUEST)

    def destroy(self, request, *args, **kwargs):
        return Response(status=status.HTTP_405_METHOD_NOT_ALLOWED)

    @action(detail=True, methods=['post'], url_path='leave-thread')
    def leave_thread(self, request, pk=None):
        """
        Allows an authenticated user to remove themselves from a thread's participant list.
        If the user is the last participant, the entire thread is deleted.
        """
        thread = self.get_object()
        user = request.user

        if not thread.participants.filter(pk=user.pk).exists():
             return Response({'error': _('You are not a participant in this thread.')}, status=status.HTTP_400_BAD_REQUEST)

        if thread.participants.count() == 1:
            thread.delete() # Last participant leaving deletes the thread
            return Response(status=status.HTTP_204_NO_CONTENT)
        else:
            thread.participants.remove(user)
            # Optionally add a system message
            # Message.objects.create(thread=thread, content=f"{user.get_username()} has left the conversation.")
            return Response({'status': _('You have left the thread.')}, status=status.HTTP_200_OK)

    @action(
        detail=True,
        methods=['post'],
        url_path='mark-message-read',
        url_name='mark-message-read-action' # Explicitly set url_name
    )
    def mark_message_as_read(self, request, pk=None):
        """
        Marks a specific message within a thread as read by the current user.
        Expects 'message_id' in the request data payload.
        The user must be a participant in the thread.
        """
        thread = self.get_object() # pk is for the thread
        message_id = request.data.get('message_id')

        if not message_id:
            return Response({"error": "message_id is required in the payload."}, status=status.HTTP_400_BAD_REQUEST)

        try:
            message_id = int(message_id) # Ensure it's an integer
        except (ValueError, TypeError):
            return Response({"error": "Invalid message_id format."}, status=status.HTTP_400_BAD_REQUEST)

        message = get_object_or_404(Message, pk=message_id, thread=thread) # Ensure message belongs to thread

        message.read_by.add(request.user)
        return Response(status=status.HTTP_204_NO_CONTENT) # Return 204 on successful action
