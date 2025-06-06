from django.contrib import admin
from .models import (
    SchoolYear, Subject, SchoolClass, Enrollment,
    GradingPeriod, Grade, Attendance, SchoolEvent, DidacticMaterial,
    TeacherAssignment # Adicionado TeacherAssignment
)

@admin.register(SchoolYear)
class SchoolYearAdmin(admin.ModelAdmin):
    list_display = ('year', 'start_date', 'end_date', 'is_active')
    list_filter = ('is_active',)
    search_fields = ('year',)

@admin.register(Subject)
class SubjectAdmin(admin.ModelAdmin):
    list_display = ('name', 'description')
    search_fields = ('name',)

# Inlines para SchoolClassAdmin
class EnrollmentInline(admin.TabularInline):
    model = Enrollment
    extra = 0
    autocomplete_fields = ['student']
    show_change_link = True
    verbose_name = "Matrícula nesta Turma"
    verbose_name_plural = "Alunos Matriculados nesta Turma"
    # Definir quais campos do Enrollment mostrar no inline, se necessário
    # fields = ('student', 'status', 'enrollment_date')
    # readonly_fields = ('enrollment_date',)


@admin.register(SchoolClass)
class SchoolClassAdmin(admin.ModelAdmin):
    list_display = ('name', 'school_year', 'grade_level', 'main_teacher_display')
    list_filter = ('school_year', 'grade_level', 'main_teacher')
    search_fields = ('name', 'main_teacher__username', 'grade_level__name', 'school_year__year')
    autocomplete_fields = ['school_year', 'grade_level', 'main_teacher']
    inlines = [EnrollmentInline]
    fieldsets = (
        (None, {
            'fields': ('name', 'school_year', 'grade_level')
        }),
        ('Detalhes Adicionais', {
            'fields': ('main_teacher',),
        }),
    )
    list_select_related = ('school_year', 'grade_level', 'main_teacher')

    def main_teacher_display(self, obj):
        if obj.main_teacher:
            return obj.main_teacher.get_full_name() or obj.main_teacher.username
        return "-"
    main_teacher_display.short_description = 'Professor Principal'


# Inlines para EnrollmentAdmin
class GradeInline(admin.TabularInline):
    model = Grade
    extra = 0
    autocomplete_fields = ['subject', 'grading_period']
    verbose_name = "Nota"
    verbose_name_plural = "Notas Lançadas para esta Matrícula"
    # fields = ('subject', 'grading_period', 'assessment_name', 'grade_value', 'weight', 'grading_date')
    # readonly_fields = ('grading_date',)

class AttendanceInline(admin.TabularInline):
    model = Attendance
    extra = 0
    autocomplete_fields = ['subject']
    verbose_name = "Registro de Frequência"
    verbose_name_plural = "Registros de Frequência para esta Matrícula"
    # fields = ('subject', 'date', 'status', 'notes')
    # readonly_fields = ('date',)


@admin.register(Enrollment)
class EnrollmentAdmin(admin.ModelAdmin):
    list_display = ('student_display', 'school_class_display', 'enrollment_date', 'status')
    list_filter = ('status', 'school_class__school_year', 'school_class__grade_level')
    search_fields = (
        'student__user__username',
        'student__user__first_name',
        'student__user__last_name',
        'school_class__name'
    )
    autocomplete_fields = ['student', 'school_class']
    date_hierarchy = 'enrollment_date'
    inlines = [GradeInline, AttendanceInline]
    list_select_related = ('student__user', 'school_class__grade_level', 'school_class__school_year')

    def student_display(self, obj):
        return str(obj.student) # Usa o __str__ do modelo Student
    student_display.short_description = 'Aluno'
    student_display.admin_order_field = 'student__user__first_name'


    def school_class_display(self, obj):
        return str(obj.school_class) # Usa o __str__ do modelo SchoolClass
    school_class_display.short_description = 'Turma'
    school_class_display.admin_order_field = 'school_class__name'


@admin.register(GradingPeriod)
class GradingPeriodAdmin(admin.ModelAdmin):
    list_display = ('name', 'school_year', 'start_date', 'end_date')
    list_filter = ('school_year__year',)
    search_fields = ('name', 'school_year__year')
    autocomplete_fields = ['school_year']


@admin.register(Grade)
class GradeAdmin(admin.ModelAdmin):
    list_display = ('enrollment_info', 'subject', 'grading_period', 'assessment_name', 'grade_value', 'weight', 'grading_date')
    list_filter = ('grading_period__school_year__year', 'subject', 'grading_period', 'grading_date')
    search_fields = (
        'enrollment__student__user__username',
        'enrollment__student__user__first_name',
        'subject__name',
        'assessment_name'
    )
    autocomplete_fields = ['enrollment', 'subject', 'grading_period']
    date_hierarchy = 'grading_date'
    list_select_related = ('enrollment__student__user', 'subject', 'grading_period__school_year')

    def enrollment_info(self, obj):
        return f"{obj.enrollment.student} ({obj.enrollment.school_class.name})"
    enrollment_info.short_description = "Aluno (Turma)"


@admin.register(Attendance)
class AttendanceAdmin(admin.ModelAdmin):
    list_display = ('enrollment_info', 'subject', 'date', 'status')
    list_filter = ('status', 'date', 'subject__name')
    search_fields = (
        'enrollment__student__user__username',
        'enrollment__student__user__first_name',
        'subject__name'
    )
    autocomplete_fields = ['enrollment', 'subject']
    date_hierarchy = 'date'
    list_select_related = ('enrollment__student__user', 'subject')

    def enrollment_info(self, obj):
        return f"{obj.enrollment.student} ({obj.enrollment.school_class.name})"
    enrollment_info.short_description = "Aluno (Turma)"


@admin.register(SchoolEvent)
class SchoolEventAdmin(admin.ModelAdmin):
    list_display = ('title', 'event_type', 'start_time', 'end_time', 'is_school_wide', 'created_by_display')
    list_filter = ('event_type', 'is_school_wide', 'start_time')
    search_fields = ('title', 'description', 'created_by__username')
    date_hierarchy = 'start_time'
    filter_horizontal = ('target_school_classes', 'target_grade_levels')
    autocomplete_fields = ['created_by']
    fieldsets = (
        (None, {'fields': ('title', 'description', 'event_type')}),
        ('Datas e Horários', {'fields': ('start_time', 'end_time')}),
        ('Público Alvo', {'fields': ('target_school_classes', 'target_grade_levels', 'is_school_wide')}),
        ('Metadados', {'fields': ('created_by',)}),
    )
    list_select_related = ('created_by',)

    def created_by_display(self, obj):
        if obj.created_by:
            return obj.created_by.get_full_name() or obj.created_by.username
        return "-"
    created_by_display.short_description = 'Criado por'


@admin.register(DidacticMaterial)
class DidacticMaterialAdmin(admin.ModelAdmin):
    list_display = ('title', 'subject', 'school_class_display', 'uploader_display', 'upload_date')
    list_filter = ('subject', 'school_class', 'upload_date', 'uploader')
    search_fields = ('title', 'description', 'subject__name', 'uploader__username')
    autocomplete_fields = ['subject', 'school_class', 'uploader']
    date_hierarchy = 'upload_date'
    list_select_related = ('subject', 'school_class', 'uploader')

    def school_class_display(self, obj):
        return str(obj.school_class) if obj.school_class else "-"
    school_class_display.short_description = 'Turma'

    def uploader_display(self, obj):
        if obj.uploader:
            return obj.uploader.get_full_name() or obj.uploader.username
        return "-"
    uploader_display.short_description = 'Enviado por'


@admin.register(TeacherAssignment)
class TeacherAssignmentAdmin(admin.ModelAdmin):
    list_display = ('teacher_display', 'subject', 'school_class_display', 'school_year')
    list_filter = ('school_year__year', 'subject__name', 'school_class__grade_level__name')
    search_fields = (
        'teacher__username',
        'teacher__first_name',
        'teacher__last_name',
        'subject__name',
        'school_class__name',
        'school_year__year'
    )
    autocomplete_fields = ['teacher', 'school_class', 'subject', 'school_year']
    list_select_related = ('teacher', 'school_class', 'subject', 'school_year', 'school_class__grade_level')

    def teacher_display(self, obj):
        if obj.teacher:
            return obj.teacher.get_full_name() or obj.teacher.username
        return "-"
    teacher_display.short_description = 'Professor'
    teacher_display.admin_order_field = 'teacher__first_name' # Exemplo de ordenação

    def school_class_display(self, obj):
        return str(obj.school_class)
    school_class_display.short_description = 'Turma'
    school_class_display.admin_order_field = 'school_class__name'


# É importante que os modelos referenciados em autocomplete_fields (Student, User, SchoolClass, etc.)
# tenham search_fields definidos em seus respectivos ModelAdmins para que o widget de autocomplete funcione.
# User (padrão do Django ou o customizado) já tem. Para os outros, foram configurados aqui ou em seus apps.
