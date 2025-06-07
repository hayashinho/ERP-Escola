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


class UserEmailSerializer(serializers.ModelSerializer):
    """
    Serializer for User model for email management.
    """
    class Meta:
        model = User
        fields = ('id', 'username', 'first_name', 'last_name', 'email', 'user_type')
        read_only_fields = ('id', 'username', 'first_name', 'last_name', 'user_type')

    def update(self, instance, validated_data):
        instance.email = validated_data.get('email', instance.email)
        instance.save(update_fields=['email'])
        return instance


class UserManagementSerializer(serializers.ModelSerializer):
    """
    Serializer for User model for management by Direção/Admin.
    Handles creation, update (specific fields), and detailed display.
    """
    # For display purposes, include user_type_display
    user_type_display = serializers.CharField(source='get_user_type_display', read_only=True)

    class Meta:
        model = User
        fields = (
            'id', 'username', 'email', 'first_name', 'last_name',
            'user_type', 'user_type_display',
            'is_active', 'is_staff', 'is_superuser',
            'date_joined', 'last_login',
            'password' # Included for creation, write-only
        )
        read_only_fields = ('id', 'date_joined', 'last_login', 'user_type_display') # username removed from here
        extra_kwargs = {
            'password': {'write_only': True, 'style': {'input_type': 'password'}, 'required': False},
            # Fields like username, email, user_type are required by model (blank=False)
            # and will be enforced by DRF on POST. No need for 'required: True' here,
            # which would make them always required even for PATCH.
        }

    def create(self, validated_data):
        # Ensure password is provided for creation
        password = validated_data.pop('password', None)
        if password is None:
            raise serializers.ValidationError({"password": "Password is required for new users."})

        user = User(**validated_data)
        user.set_password(password) # Hash password
        user.save()
        return user

    def update(self, instance, validated_data):
        # Username should not be updatable. If provided, ignore it or raise error.
        # For now, we simply don't assign it. The field is not in read_only_fields for create to work.
        validated_data.pop('username', None)

        # Password updates are not handled by this serializer for existing users
        if 'password' in validated_data:
            # Do not allow password changes through this general update endpoint
            # Consider logging this attempt or simply ignoring it.
            # For this implementation, we'll pop it to prevent accidental changes.
            validated_data.pop('password', None)
            # If you wanted to allow it, you would do:
            # password = validated_data.pop('password')
            # instance.set_password(password)
            # But the requirement is to not handle it here.

        # Update other allowed fields
        instance.email = validated_data.get('email', instance.email)
        instance.first_name = validated_data.get('first_name', instance.first_name)
        instance.last_name = validated_data.get('last_name', instance.last_name)
        instance.user_type = validated_data.get('user_type', instance.user_type)
        instance.is_active = validated_data.get('is_active', instance.is_active)
        instance.is_staff = validated_data.get('is_staff', instance.is_staff)
        instance.is_superuser = validated_data.get('is_superuser', instance.is_superuser)

        instance.save()
        return instance
