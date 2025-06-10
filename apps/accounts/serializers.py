from rest_framework import serializers
from .models import User, UserProfile
from django.utils.translation import gettext_lazy as _ # Import gettext_lazy

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
    Serializer for managing User emails.
    Allows viewing user details and updating the email field.
    Other fields are read-only.
    """
    email = serializers.EmailField(help_text=_("User's email address. This field is updatable."))
    user_type = serializers.CharField(help_text=_("Type of user account (e.g., STUDENT, TEACHER). Read-only.")) # Force CharField for display of choices

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
    Handles creation, update (specific fields), and detailed display of User accounts.
    Designed for use by administrative users (e.g., Direção).
    """
    user_type_display = serializers.CharField(source='get_user_type_display', read_only=True, help_text=_("Verbose display name for the user type."))
    # Explicitly define fields to add help_text or override properties
    username = serializers.CharField(
        help_text=_("Username. Required for new users. Cannot be changed after creation via this endpoint.")
    )
    email = serializers.EmailField(
        required=True, # Model's email field is not blank/null
        help_text=_("User's email address. Must be unique.")
    )
    user_type = serializers.ChoiceField(
        choices=User.USER_TYPE_CHOICES,
        required=True, # Model's user_type has a default, but explicit is better for API clarity on create
        help_text=_("Type of user account. Determines permissions and role.")
    )
    first_name = serializers.CharField(required=False, allow_blank=True, help_text=_("User's first name (optional)."))
    last_name = serializers.CharField(required=False, allow_blank=True, help_text=_("User's last name (optional)."))
    password = serializers.CharField(
        write_only=True,
        style={'input_type': 'password'},
        required=True, # Required for new users
        help_text=_("User's password. Required for new users. Not readable. Not updatable for existing users via this endpoint.")
    )

    class Meta:
        model = User
        fields = (
            'id', 'username', 'email', 'first_name', 'last_name',
            'user_type', 'user_type_display',
            'is_active', 'is_staff', 'is_superuser',
            'date_joined', 'last_login',
            'password'
        )
        read_only_fields = ('id', 'date_joined', 'last_login', 'user_type_display')
        extra_kwargs = {
            # username: help_text added above. It's not in read_only_fields to allow for create.
            # email: help_text and required status handled above.
            # user_type: help_text and required status handled above.
            # password: help_text, write_only, required handled above.
            'is_active': {'help_text': _("Designates whether this user should be treated as active. Unselect this instead of deleting accounts.")},
            'is_staff': {'help_text': _("Designates whether the user can log into this admin site (e.g., access Django Admin).")},
            'is_superuser': {'help_text': _("Designates that this user has all permissions without explicitly assigning them. Use with caution.")},
        }

    def create(self, validated_data):
        # Password hashing is done by User.objects.create_user
        # email, username, password will be in validated_data due to required=True or handled by create_user
        user = User.objects.create_user(**validated_data)
        return user

    def update(self, instance, validated_data):
        # For updates, username should not be changed.
        # Password is not updatable here (it's write_only and not explicitly handled for update).
        # We allow partial updates, so only provided fields are updated.

        # Prevent username update attempts
        if 'username' in validated_data:
            validated_data.pop('username')
            # Optionally, log this attempt or raise an error if strictness is preferred.
            # For now, we silently ignore it to prevent accidental changes.

        # Prevent password update attempts (password is write_only and not in instance fields for super().update)
        if 'password' in validated_data:
            validated_data.pop('password')

        return super().update(instance, validated_data)
        # The parent's update method will handle saving the instance with validated_data.
        # Fields like email, first_name, last_name, user_type, is_active, is_staff, is_superuser
        # will be updated if provided in validated_data.
        return instance
