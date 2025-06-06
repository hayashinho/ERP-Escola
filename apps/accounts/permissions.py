from rest_framework import permissions
from .models import User # Importar o modelo User para acessar USER_TYPE_TEACHER

class IsTeacher(permissions.BasePermission):
    """
    Permissão customizada para permitir acesso apenas a usuários do tipo Professor.
    """

    message = "Apenas usuários do tipo Professor podem realizar esta ação."

    def has_permission(self, request, view):
        # Verifica se o usuário está autenticado e se o user_type é TEACHER
        return bool(
            request.user and
            request.user.is_authenticated and
            request.user.user_type == User.USER_TYPE_TEACHER
        )

class IsParent(permissions.BasePermission):
    """
    Permissão customizada para permitir acesso apenas a usuários do tipo Pai/Responsável.
    """
    message = "Apenas usuários do tipo Pai/Responsável podem realizar esta ação."

    def has_permission(self, request, view):
        return bool(
            request.user and
            request.user.is_authenticated and
            request.user.user_type == User.USER_TYPE_PARENT
        )

class IsStudent(permissions.BasePermission):
    """
    Permissão customizada para permitir acesso apenas a usuários do tipo Aluno.
    """
    message = "Apenas usuários do tipo Aluno podem realizar esta ação."

    def has_permission(self, request, view):
        return bool(
            request.user and
            request.user.is_authenticated and
            request.user.user_type == User.USER_TYPE_STUDENT
        )

# Poderíamos adicionar outras permissões como IsStaffOrAdmin, etc.
# class IsStaffOrAdmin(permissions.BasePermission):
#     def has_permission(self, request, view):
#         return bool(request.user and request.user.is_authenticated and (request.user.is_staff or request.user.user_type == User.USER_TYPE_ADMIN))
