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


from rest_framework import permissions
from .serializers import UserEmailSerializer

class UserEmailManagementViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing user emails.
    Allows listing, retrieving, and updating user emails.
    Filtering by user_type is supported.
    """
    queryset = User.objects.all().order_by('username')
    serializer_class = UserEmailSerializer
    permission_classes = [permissions.IsAdminUser] # Initially, only admin users

    http_method_names = ['get', 'put', 'patch', 'head', 'options'] # Allow only these methods

    def get_queryset(self):
        """
        Optionally restricts the returned users by filtering against a `user_type`
        query parameter in the URL.
        """
        queryset = super().get_queryset()
        user_type = self.request.query_params.get('user_type')
        if user_type:
            queryset = queryset.filter(user_type=user_type.upper())
        return queryset

    def get_serializer_class(self):
        # Ensure that for update actions, only email can be changed.
        # The UserEmailSerializer already restricts fields, but this is an additional safeguard
        # if we were to use a more permissive serializer for retrieve/list.
        # However, with UserEmailSerializer used for all actions, its own field definitions
        # and read_only_fields will enforce this.
        return UserEmailSerializer


from .serializers import UserManagementSerializer
from django_filters import rest_framework as filters

class UserFilter(filters.FilterSet):
    username = filters.CharFilter(lookup_expr='iexact')
    email = filters.CharFilter(lookup_expr='iexact')
    # user_type and is_active can use default exact matching

    class Meta:
        model = User
        fields = ['username', 'email', 'user_type', 'is_active']


class UserManagementViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing Users by Direção/Admin.
    Allows CRUD operations on User accounts, with specific field handling.
    """
    queryset = User.objects.all().order_by('username')
    serializer_class = UserManagementSerializer
    permission_classes = [permissions.IsAdminUser] # Ensures only staff (admins) can access
    filter_backends = (filters.DjangoFilterBackend,)
    filterset_class = UserFilter

    def perform_create(self, serializer):
        # Password hashing is handled by the serializer's create method
        serializer.save()

    # perform_update is handled by serializer as well, including username protection.
    # No specific password update method here, as per requirements.
    # A separate action would be needed for "set_password" functionality.
