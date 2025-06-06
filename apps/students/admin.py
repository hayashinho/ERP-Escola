from django.contrib import admin
from .models import GradeLevel, Student, StudentParentAssociation, StudentDocument

@admin.register(GradeLevel)
class GradeLevelAdmin(admin.ModelAdmin):
    list_display = ('name', 'order_in_sequence')
    search_fields = ('name',)

class StudentParentAssociationInline(admin.TabularInline):
    model = StudentParentAssociation
    extra = 1 # Quantidade de formulários extras para adicionar associações
    autocomplete_fields = ['parent_user'] # Assumindo que User admin tem search_fields configurado
    verbose_name = "Responsável Associado"
    verbose_name_plural = "Responsáveis Associados"

class StudentDocumentInline(admin.TabularInline):
    model = StudentDocument
    extra = 1 # Quantidade de formulários extras para adicionar documentos
    fields = ('document_type', 'document_name', 'file', 'validation_status', 'is_optional', 'notes')
    readonly_fields = ('upload_date',) # upload_date é auto_now_add
    verbose_name = "Documento do Aluno"
    verbose_name_plural = "Documentos do Aluno"

@admin.register(Student)
class StudentAdmin(admin.ModelAdmin):
    list_display = ('__str__', 'grade_level_pretended', 'registration_status', 'enrollment_date', 'school_entry_date')
    list_filter = ('registration_status', 'grade_level_pretended')
    search_fields = ('user__username', 'user__first_name', 'user__last_name')
    # user é a chave primária, então não pode estar em raw_id_fields ou autocomplete_fields diretamente no StudentAdmin
    # mas pode ser útil em inlines ou outros contextos.
    # Se o User (de accounts.User) tiver um bom search_fields, o Django Admin lida bem com o OneToOne.
    date_hierarchy = 'enrollment_date' # Para navegação por datas
    inlines = [StudentParentAssociationInline, StudentDocumentInline]
    fieldsets = (
        (None, {
            'fields': ('user', 'registration_status')
        }),
        ('Informações Acadêmicas', {
            'fields': ('grade_level_pretended', 'enrollment_date', 'school_entry_date')
        }),
        ('Informações Adicionais', {
            'fields': ('allergies', 'observations'),
            'classes': ('collapse',), # Para campos menos usados
        }),
    )
    # Para o campo 'user' (OneToOne para accounts.User), o Django Admin já fornece uma interface de seleção.
    # Se houvesse muitos usuários, autocomplete_fields = ['user'] seria útil aqui,
    # mas 'user' é a PK, então não é necessário/permitido em autocomplete_fields.

@admin.register(StudentParentAssociation)
class StudentParentAssociationAdmin(admin.ModelAdmin):
    list_display = ('student', 'parent_user', 'get_relationship_type_display_custom')
    list_filter = ('relationship_type',)
    search_fields = ('student__user__username', 'parent_user__username', 'student__user__first_name', 'parent_user__first_name')
    autocomplete_fields = ['student', 'parent_user'] # Essencial para boa performance

    def get_relationship_type_display_custom(self, obj):
        return obj.get_relationship_type_display()
    get_relationship_type_display_custom.short_description = 'Tipo de Relação'

@admin.register(StudentDocument)
class StudentDocumentAdmin(admin.ModelAdmin):
    list_display = ('student', 'document_type', 'document_name', 'upload_date', 'validation_status', 'is_optional')
    list_filter = ('document_type', 'validation_status', 'is_optional', 'upload_date')
    search_fields = ('student__user__username', 'student__user__first_name', 'document_name')
    autocomplete_fields = ['student']
    date_hierarchy = 'upload_date'
    actions = ['approve_documents', 'reject_documents']

    def approve_documents(self, request, queryset):
        queryset.update(validation_status=StudentDocument.STATUS_APPROVED)
    approve_documents.short_description = "Aprovar documentos selecionados"

    def reject_documents(self, request, queryset):
        queryset.update(validation_status=StudentDocument.STATUS_REJECTED)
    reject_documents.short_description = "Rejeitar documentos selecionados"

# Nota: Para que autocomplete_fields funcione bem, o admin do modelo referenciado
# (ex: UserAdmin para parent_user, StudentAdmin para student) deve ter search_fields definido.
# O UserAdmin padrão do Django já tem search_fields. Para Student, já definimos.
