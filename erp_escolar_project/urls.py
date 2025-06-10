"""
URL configuration for erp_escolar_project project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path, include # Adicionado include
from rest_framework_simplejwt.views import (
    TokenObtainPairView, # Re-adicionada TokenObtainPairView original
    TokenRefreshView,
    TokenBlacklistView,
)
from drf_spectacular.views import SpectacularAPIView, SpectacularRedocView, SpectacularSwaggerView # Moved import to top
# Importar a view customizada para obtenção de token (COMENTADO TEMPORARIAMENTE)
# from apps.accounts.views import CustomTokenObtainPairView

urlpatterns = [
    path('admin/', admin.site.urls),

    # Rotas da API para o app accounts (usuários, etc.)
    path('api/accounts/', include('apps.accounts.urls')),
    # Rotas da API para o app students
    path('api/students/', include('apps.students.urls')),
    # Rotas da API para o app academics
    path('api/academics/', include('apps.academics.urls')),
    # Rotas da API para o app financials
    path('api/financials/', include('apps.financials.urls')),
    # Rotas da API para o app communications
    path('api/communications/', include('apps.communications.urls')),
    # Rotas da API para o app auditing
    path('api/auditing/', include('apps.auditing.urls')),

    # Rotas da API para autenticação JWT
    # Usar a view original TokenObtainPairView para evitar erro de ratelimit
    path('api/token/', TokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('api/token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path('api/token/blacklist/', TokenBlacklistView.as_view(), name='token_blacklist'),

    # drf-spectacular URLs
    path('api/schema/', SpectacularAPIView.as_view(), name='schema'),
    path('api/schema/swagger-ui/', SpectacularSwaggerView.as_view(url_name='schema'), name='swagger-ui'),
    path('api/schema/redoc/', SpectacularRedocView.as_view(url_name='schema'), name='redoc'),
]
