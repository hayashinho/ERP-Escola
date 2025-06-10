from rest_framework import permissions

class IsParticipantInThread(permissions.BasePermission):
    message = "You do not have permission to access this message thread."

    def has_object_permission(self, request, view, obj):
        # obj is the MessageThread instance
        if request.user and request.user.is_authenticated:
            return obj.participants.filter(pk=request.user.pk).exists()
        return False
