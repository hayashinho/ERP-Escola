from django.urls import path, include # Adicionado include
from rest_framework.routers import DefaultRouter
from .views import (
    PreRegistrationAPIView,
    PendingRegistrationViewSet,
    StudentManagementViewSet,
    StudentDocumentManagementViewSet
)

app_name = 'students'  # Define o namespace do app

# Cria uma instância do DefaultRouter
router = DefaultRouter()

# Registra o PendingRegistrationViewSet com o router.
# O prefixo 'admin/pending-registrations' será usado nas URLs
# (ex: /api/students/admin/pending-registrations/)
router.register(
    r'admin/pending-registrations',
    PendingRegistrationViewSet,
    basename='pending_registration'
)
router.register(
    r'admin/student-management',
    StudentManagementViewSet,
    basename='student_management'
)
router.register(
    r'admin/student-document-management',
    StudentDocumentManagementViewSet,
    basename='student_document_management'
)

from .views import StudentListCSVExportView # Import the new view

# As urlpatterns do app começam com as URLs geradas pelo router.
urlpatterns = [
    # Inclui as URLs geradas pelo router (para o ViewSet)
    path('', include(router.urls)),

    # Adiciona a URL para PreRegistrationAPIView manualmente, pois não é um ViewSet.
    path('pre-register/', PreRegistrationAPIView.as_view(), name='pre_register_student'),

    # URL for CSV Export
    path('reports/student-list/csv/', StudentListCSVExportView.as_view(), name='student_list_csv_export'),

    # Outras URLs específicas do app students podem ser adicionadas aqui no futuro.
]

# A estrutura final de urlpatterns será algo como:
# [
#   path('admin/pending-registrations/', PendingRegistrationViewSet...list),
#   path('admin/pending-registrations/<pk>/', PendingRegistrationViewSet...detail),
#   path('admin/pending-registrations/<pk>/approve-registration/', PendingRegistrationViewSet...approve),
#   path('admin/pending-registrations/<pk>/reject-registration/', PendingRegistrationViewSet...reject),
#   path('pre-register/', PreRegistrationAPIView...),
# ]
