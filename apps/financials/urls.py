from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    MyFeesViewSet,
    MyPaymentsViewSet,
    FeeManagementViewSet,
    PaymentManagementViewSet # PaymentManagementViewSet importado
)

app_name = 'financials'  # Define o namespace do app

# Cria uma instância do DefaultRouter
router = DefaultRouter()

# Registra os ViewSets "My Data" para o app financials (acesso de alunos/pais)
router.register(r'my-fees', MyFeesViewSet, basename='my-fees')
router.register(r'my-payments', MyPaymentsViewSet, basename='my-payments')

# Registra os ViewSets de Gerenciamento (acesso da secretaria/admin)
router.register(r'management/fees', FeeManagementViewSet, basename='fee-management')
router.register(r'management/payments', PaymentManagementViewSet, basename='payment-management') # Novo ViewSet registrado


# As urlpatterns do app são definidas pelas URLs geradas pelo router.
urlpatterns = [
    path('', include(router.urls)),
    # Adicionar outras URLs específicas do app aqui, se não forem baseadas em ViewSets.
]
