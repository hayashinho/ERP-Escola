from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import UserViewSet

# Cria uma instância do DefaultRouter
# O DefaultRouter automaticamente cria as rotas padrão para um ViewSet (list, create, retrieve, update, partial_update, destroy)
router = DefaultRouter()

# Registra o UserViewSet com o router.
# O prefixo 'users' será usado nas URLs (ex: /api/accounts/users/)
# 'basename' é usado para nomear as URLs geradas. Se o queryset for definido no ViewSet,
# o basename geralmente pode ser omitido e o DRF o inferirá do nome do modelo.
# No entanto, é uma boa prática especificá-lo para clareza e evitar conflitos.
router.register(r'users', UserViewSet, basename='user')

# As urlpatterns do app são definidas pelas URLs geradas pelo router.
# Também podemos adicionar outras URLs específicas do app aqui, se necessário,
# usando path() como de costume.
urlpatterns = [
    path('', include(router.urls)),
    # Exemplo de URL adicional não gerenciada pelo router:
    # path('custom-action/', views.some_custom_view, name='custom-action'),
]

# Opcionalmente, podemos definir app_name para namespacing de URLs,
# mas com DRF e routers, o basename no registro do ViewSet geralmente é suficiente.
# app_name = 'accounts'
