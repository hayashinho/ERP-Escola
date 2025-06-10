from django.contrib.auth.models import AbstractUser
from django.db import models
from django.utils.translation import gettext_lazy as _

class User(AbstractUser):
    """
    Modelo de usuário customizado que herda de AbstractUser.
    Adiciona um campo user_type para diferenciar entre os tipos de usuários.
    """
    USER_TYPE_PARENT = 'PARENT'
    USER_TYPE_STUDENT = 'STUDENT'
    USER_TYPE_TEACHER = 'TEACHER'
    USER_TYPE_STAFF = 'STAFF'
    USER_TYPE_ADMIN = 'ADMIN'

    USER_TYPE_CHOICES = [
        (USER_TYPE_PARENT, _('Parent')),
        (USER_TYPE_STUDENT, _('Student')),
        (USER_TYPE_TEACHER, _('Teacher')),
        (USER_TYPE_STAFF, _('Staff')),
        (USER_TYPE_ADMIN, _('Admin')),
    ]

    # Remove first_name e last_name se não forem usados diretamente, pois AbstractUser já os possui.
    # Se você quiser torná-los obrigatórios ou alterar algo, pode redefini-los.
    # Por enquanto, vamos manter os campos de AbstractUser.
    # username, email, password, first_name, last_name, is_staff, is_active, date_joined já existem.

    user_type = models.CharField(
        _('user type'),
        max_length=10,
        choices=USER_TYPE_CHOICES,
        default=USER_TYPE_STUDENT,
        help_text=_('Designates the role of the user in the system.'),
    )

    # Link to School Units for access permissions
    # Make sure to import SchoolUnit: from apps.core.models import SchoolUnit
    school_units_access = models.ManyToManyField(
       'core.SchoolUnit', # Use string 'app_label.ModelName'
       blank=True,
       related_name='users_with_access',
       verbose_name=_('school units access'),
       help_text=_("School units this user has permissions to access data from.")
    )

    # Adicionar related_name para evitar conflitos com o User padrão do Django, se necessário.
    # groups = models.ManyToManyField(
    #     'auth.Group',
    #     verbose_name=_('groups'),
    #     blank=True,
    #     help_text=_(
    #         'The groups this user belongs to. A user will get all permissions '
    #         'granted to each of their groups.'
    #     ),
    #     related_name="accounts_user_set", # Nome único para related_name
    #     related_query_name="user",
    # )
    # user_permissions = models.ManyToManyField(
    #     'auth.Permission',
    #     verbose_name=_('user permissions'),
    #     blank=True,
    #     help_text=_('Specific permissions for this user.'),
    #     related_name="accounts_user_set", # Nome único para related_name
    #     related_query_name="user",
    # )

    def __str__(self):
        return self.username


class UserProfile(models.Model):
    """
    Modelo de perfil do usuário para armazenar informações adicionais.
    """
    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        primary_key=True, # Define user como chave primária para otimizar buscas
        related_name='profile',
        verbose_name=_('user')
    )
    cpf = models.CharField(
        _('CPF'),
        max_length=14, # Formato XXX.XXX.XXX-XX
        unique=True,
        null=True,
        blank=True,
        help_text=_('Formato: XXX.XXX.XXX-XX')
    )
    date_of_birth = models.DateField(
        _('date of birth'),
        null=True,
        blank=True
    )
    address = models.TextField(
        _('address'),
        null=True,
        blank=True
    )
    phone_number = models.CharField(
        _('phone number'),
        max_length=20, # Considerar formatos internacionais (+XX XXXX-XXXX)
        null=True,
        blank=True
    )
    # Adicionar outros campos conforme necessário, como foto de perfil, etc.
    # profile_picture = models.ImageField(upload_to='profile_pics/', null=True, blank=True)

    # Link to SchoolUnit
    # Make sure to import SchoolUnit: from apps.core.models import SchoolUnit
    active_school_unit = models.ForeignKey(
       'core.SchoolUnit', # Use string 'app_label.ModelName' to avoid circular import if SchoolUnit is in another app
       on_delete=models.SET_NULL,
       null=True,
       blank=True,
       related_name='user_profiles_active_here',
       verbose_name=_('active school unit'),
       help_text=_("The school unit this user is currently primarily associated with or operating within.")
    )

    def __str__(self):
        return f"{self.user.username}'s Profile"

    class Meta:
        verbose_name = _('User Profile')
        verbose_name_plural = _('User Profiles')
