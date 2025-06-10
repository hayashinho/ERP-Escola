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
        ('Role & School Access', {'fields': ('user_type', 'school_units_access')}), # Added school_units_access
    )
    list_filter = BaseUserAdmin.list_filter + ('user_type',)
    add_fieldsets = BaseUserAdmin.add_fieldsets + (
        (None, {
            'classes': ('wide',),
            'fields': ('user_type',), # school_units_access might be too complex for add_fieldsets, handle post-creation
        }),
    )
    filter_horizontal = ('groups', 'user_permissions', 'school_units_access',) # Added school_units_access

# Registrar o modelo User com a classe CustomUserAdmin
admin.site.register(User, CustomUserAdmin)

@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'cpf', 'phone_number', 'date_of_birth', 'active_school_unit') # Added active_school_unit
    search_fields = ('user__username', 'user__first_name', 'user__last_name', 'cpf', 'active_school_unit__name') # Added active_school_unit
    list_filter = ('active_school_unit',) # Added active_school_unit
    raw_id_fields = ('user', 'active_school_unit',) # Added active_school_unit, user was already good candidate
    # Para performance, é bom selecionar o usuário relacionado
    list_select_related = ('user', 'active_school_unit') # Added active_school_unit
