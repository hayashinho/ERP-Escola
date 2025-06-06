from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from .models import User, UserProfile

# Para customizar a exibição do User no admin
class CustomUserAdmin(BaseUserAdmin):
    # Adicionar 'user_type' aos campos exibidos na lista de usuários
    list_display = ('username', 'email', 'first_name', 'last_name', 'is_staff', 'user_type')
    # Adicionar 'user_type' aos fieldsets para edição
    # Copiar os fieldsets padrão do UserAdmin e adicionar user_type
    # É importante manter a estrutura original dos fieldsets
    fieldsets = (
        (None, {'fields': ('username', 'password')}),
        ('Personal info', {'fields': ('first_name', 'last_name', 'email')}),
        ('Permissions', {
            'fields': ('is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions'),
        }),
        ('Important dates', {'fields': ('last_login', 'date_joined')}),
        # Adicionar um novo set de campos para user_type ou adicioná-lo a um existente
        ('Role', {'fields': ('user_type',)}),
    )
    # Se você tiver muitos campos, pode ser útil adicionar user_type a list_filter também
    list_filter = BaseUserAdmin.list_filter + ('user_type',)
    # Adicionar campos para a funcionalidade de adicionar usuário
    add_fieldsets = BaseUserAdmin.add_fieldsets + (
        (None, {
            'classes': ('wide',),
            'fields': ('user_type',),
        }),
    )

# Registrar o modelo User com a classe CustomUserAdmin
admin.site.register(User, CustomUserAdmin)

# Registrar o modelo UserProfile
# Uma abordagem mais avançada seria usar um Inline para editar UserProfile junto com User.
# Por exemplo:
# class UserProfileInline(admin.StackedInline):
#     model = UserProfile
#     can_delete = False
#     verbose_name_plural = 'Profile'
#
# class CustomUserAdminWithProfile(CustomUserAdmin):
#     inlines = (UserProfileInline,)
#
# admin.site.unregister(User) # Desregistrar o User anterior se já registrado
# admin.site.register(User, CustomUserAdminWithProfile) # Registrar com o inline

# Por enquanto, vamos registrar UserProfile separadamente para simplicidade.
@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'cpf', 'phone_number', 'date_of_birth')
    search_fields = ('user__username', 'user__first_name', 'user__last_name', 'cpf')
    # Para performance, é bom selecionar o usuário relacionado
    list_select_related = ('user',)
