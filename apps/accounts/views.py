from django.utils.decorators import method_decorator
# from ratelimit.decorators import ratelimit # TEMPORARIAMENTE COMENTADO
from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework_simplejwt.views import TokenObtainPairView

from .models import User
from .serializers import UserSerializer

# --- Views de Autenticação com Rate Limiting ---

# @method_decorator( # TEMPORARIAMENTE COMENTADO
#     ratelimit(key='ip', rate='5/m', method=ratelimit.ALL, block=True),
#     name='dispatch'
# )
class CustomTokenObtainPairView(TokenObtainPairView): # Herança mantida, mas decorador comentado
    """
    View customizada para obtenção de token JWT (login) com rate limiting.
    Limita as tentativas de login para 5 por minuto por endereço IP.
    """
    # Nenhuma lógica adicional é necessária aqui, a menos que queiramos
    # customizar o serializer ou o comportamento da view original.
    # O rate limiting é aplicado pelo decorador ao método dispatch.
    pass


# --- Views de Modelos (CRUD) ---

class UserViewSet(viewsets.ModelViewSet):
    """
    ViewSet para visualização e edição de instâncias de User.
    """
    queryset = User.objects.all().order_by('-date_joined') # Ordenar por data de entrada, mais recentes primeiro
    serializer_class = UserSerializer
    permission_classes = [IsAuthenticated] # Apenas usuários autenticados podem acessar

    # Se quiséssemos permitir criação de usuário sem autenticação (ex: cadastro público):
    # def get_permissions(self):
    #     if self.action == 'create':
    #         return [AllowAny()] # Permite qualquer um criar (registrar)
    #     return super().get_permissions()

    # Poderíamos adicionar filtros, paginação, etc. aqui no futuro.
    # from django_filters.rest_framework import DjangoFilterBackend
    # from rest_framework import filters
    # filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    # filterset_fields = ['user_type', 'is_active']
    # search_fields = ['username', 'email', 'first_name', 'last_name']
    # ordering_fields = ['username', 'date_joined', 'user_type']
    # pagination_class = PageNumberPagination (ou outra classe de paginação)

# Outros ViewSets ou APIViews podem ser adicionados aqui no futuro,
# por exemplo, para UserProfile isoladamente, se necessário, ou para ações customizadas.
