from rest_framework import serializers
from .models import User, UserProfile

class UserProfileSerializer(serializers.ModelSerializer):
    """
    Serializer para o modelo UserProfile.
    Inclui todos os campos do modelo.
    """
    class Meta:
        model = UserProfile
        fields = '__all__'
        # Poderia também ser uma lista explícita:
        # fields = ('user', 'cpf', 'date_of_birth', 'address', 'phone_number')

class UserSerializer(serializers.ModelSerializer):
    """
    Serializer para o modelo User customizado.
    Inclui campos selecionados do User e o UserProfile aninhado (somente leitura).
    """
    # Aninhar o UserProfileSerializer.
    # 'profile' é o related_name que definimos no OneToOneField do UserProfile.
    # read_only=True simplifica, pois não precisaremos lidar com escrita aninhada agora.
    profile = UserProfileSerializer(read_only=True)

    class Meta:
        model = User
        fields = (
            'id',
            'username',
            'email',
            'first_name',
            'last_name',
            'user_type',
            'profile', # Chave para o serializer aninhado
        )
        # Se você quisesse que o perfil fosse gravável, a configuração seria mais complexa,
        # exigindo a sobrescrita dos métodos create() e/ou update().
        # Exemplo de como poderia ser se fosse gravável (mas não implementaremos agora):
        # profile = UserProfileSerializer()
        #
        # read_only_fields = ('user_type',) # Exemplo, se user_type não pudesse ser setado via API diretamente

# Nota sobre escrita aninhada (para referência futura, não implementado agora):
# Para permitir a escrita no `profile` aninhado, você precisaria sobrescrever
# o método `create` e/ou `update` no `UserSerializer`.
#
# def create(self, validated_data):
#     profile_data = validated_data.pop('profile', None)
#     user = User.objects.create(**validated_data) # CUIDADO: create_user para senha
#     if profile_data:
#         UserProfile.objects.create(user=user, **profile_data)
#     return user
#
# def update(self, instance, validated_data):
#     profile_data = validated_data.pop('profile', None)
#     # Atualizar campos do User
#     instance = super().update(instance, validated_data)
#
#     if profile_data:
#         profile = instance.profile
#         # Atualizar campos do UserProfile
#         for attr, value in profile_data.items():
#             setattr(profile, attr, value)
#         profile.save()
#     return instance


class UserRegistrationSerializer(serializers.ModelSerializer):
    """
    Serializer para registro de novos usuários (pais, alunos, etc., dependendo do user_type).
    """
    password_confirm = serializers.CharField(write_only=True, required=True, label="Confirm password")

    class Meta:
        model = User
        fields = (
            'username',    # Pode ser o email, CPF ou um nome de usuário único
            'email',       # Obrigatório se username não for o email
            'password',
            'password_confirm',
            'first_name',
            'last_name',
            'user_type',   # PARENT, STUDENT, TEACHER, STAFF, ADMIN
        )
        extra_kwargs = {
            'password': {'write_only': True, 'style': {'input_type': 'password'}},
            'first_name': {'required': True},
            'last_name': {'required': True},
            'email': {'required': True}, # Tornar email obrigatório
        }

    def validate_username(self, value):
        """
        Valida se o username já existe.
        """
        if User.objects.filter(username=value).exists():
            raise serializers.ValidationError("A user with that username already exists.")
        return value

    def validate_email(self, value):
        """
        Valida se o email já existe.
        Normalmente, o modelo User já tem unique=True para email se configurado,
        mas uma validação explícita aqui é boa para mensagens de erro mais claras.
        Se o email não for unique no modelo User, esta validação é mais importante.
        """
        # O AbstractUser por padrão não força email único. Se o seu User customizado sim, esta validação é redundante.
        # No nosso User customizado, não especificamos unique=True para email, então esta validação é útil.
        if User.objects.filter(email__iexact=value).exists(): # __iexact para case-insensitive
            raise serializers.ValidationError("A user with this email address already exists.")
        return value

    def validate(self, data):
        """
        Verifica se password e password_confirm são iguais.
        """
        if data.get('password') != data.get('password_confirm'):
            raise serializers.ValidationError({"password_confirm": "Passwords do not match."})

        # Validação do user_type para garantir que seja um valor válido dos choices
        user_type_value = data.get('user_type')
        valid_user_types = [choice[0] for choice in User.USER_TYPE_CHOICES]
        if user_type_value not in valid_user_types:
            raise serializers.ValidationError({"user_type": f"Invalid user type. Choose from: {', '.join(valid_user_types)}."})

        return data

    def create(self, validated_data):
        """
        Cria e retorna um novo usuário.
        """
        validated_data.pop('password_confirm', None)  # Remover antes de passar para create_user

        user = User.objects.create_user(**validated_data)
        return user
