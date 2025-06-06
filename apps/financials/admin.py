from django.contrib import admin
from .models import Fee, FeeEditLog, Payment

class FeeEditLogInline(admin.TabularInline):
    model = FeeEditLog
    extra = 0 # Não mostrar formulários vazios por padrão
    fields = ('timestamp', 'field_changed', 'previous_value', 'new_value', 'reason', 'edited_by')
    readonly_fields = ('timestamp',) # Definido por auto_now_add
    autocomplete_fields = ['edited_by']
    verbose_name = "Log de Edição"
    verbose_name_plural = "Logs de Edições"

class PaymentInline(admin.TabularInline):
    model = Payment
    extra = 0
    fields = ('payment_date', 'amount_paid', 'payment_method', 'transaction_id', 'notes', 'confirmed_by', 'created_at')
    readonly_fields = ('created_at',)
    autocomplete_fields = ['confirmed_by']
    show_change_link = True
    verbose_name = "Pagamento Recebido"
    verbose_name_plural = "Pagamentos Recebidos"

@admin.register(Fee)
class FeeAdmin(admin.ModelAdmin):
    list_display = (
        'description',
        'student_display',
        'school_year_display',
        'due_date',
        'amount',
        'status',
        'amount_paid',
        'payment_date',
        'is_overdue_display'
    )
    list_filter = ('status', 'school_year__year', 'due_date')
    search_fields = (
        'description',
        'student__user__username',
        'student__user__first_name',
        'student__user__last_name',
        'payment_gateway_id',
        'barcode'
    )
    date_hierarchy = 'due_date'
    autocomplete_fields = ['student', 'school_year']
    inlines = [PaymentInline, FeeEditLogInline]
    list_select_related = ('student__user', 'school_year')
    fieldsets = (
        (None, {
            'fields': ('student', 'school_year', 'description', 'due_date', 'amount', 'status')
        }),
        ('Detalhes do Pagamento', {
            'classes': ('collapse',),
            'fields': ('amount_paid', 'payment_date', 'discount_amount', 'penalty_amount')
        }),
        ('Informações do Gateway/Boleto', {
            'classes': ('collapse',),
            'fields': ('payment_gateway_id', 'barcode')
        }),
        ('Observações', {
            'classes': ('collapse',),
            'fields': ('notes',)
        }),
    )

    def student_display(self, obj):
        return str(obj.student)
    student_display.short_description = 'Aluno'
    student_display.admin_order_field = 'student__user__first_name'

    def school_year_display(self, obj):
        return str(obj.school_year)
    school_year_display.short_description = 'Ano Letivo'
    school_year_display.admin_order_field = 'school_year__year'

    def is_overdue_display(self, obj):
        return "Sim" if obj.is_overdue else "Não"
    is_overdue_display.short_description = 'Vencido?'
    is_overdue_display.boolean = True


@admin.register(FeeEditLog)
class FeeEditLogAdmin(admin.ModelAdmin):
    list_display = ('fee_info', 'field_changed', 'previous_value', 'new_value', 'reason_snippet', 'timestamp', 'edited_by_display')
    list_filter = ('field_changed', 'timestamp', 'edited_by__username')
    search_fields = ('fee__description', 'fee__student__user__username', 'edited_by__username', 'reason', 'previous_value', 'new_value')
    date_hierarchy = 'timestamp'
    autocomplete_fields = ['fee', 'edited_by']
    list_select_related = ('fee__student__user', 'edited_by')

    def fee_info(self, obj):
        return f"{obj.fee.description} ({obj.fee.student})"
    fee_info.short_description = 'Taxa (Aluno)'

    def edited_by_display(self, obj):
        if obj.edited_by:
            return obj.edited_by.username
        return "-"
    edited_by_display.short_description = 'Editado Por'
    edited_by_display.admin_order_field = 'edited_by__username'

    def reason_snippet(self, obj):
        return (obj.reason[:50] + '...') if len(obj.reason) > 50 else obj.reason
    reason_snippet.short_description = 'Motivo (Trecho)'


@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = ('fee_info', 'payment_date', 'amount_paid', 'payment_method', 'transaction_id', 'confirmed_by_display', 'created_at')
    list_filter = ('payment_method', 'payment_date', 'confirmed_by__username')
    search_fields = (
        'fee__description',
        'fee__student__user__username',
        'transaction_id',
        'notes'
    )
    date_hierarchy = 'payment_date'
    autocomplete_fields = ['fee', 'confirmed_by']
    list_select_related = ('fee__student__user', 'confirmed_by')
    readonly_fields = ('created_at',)


    def fee_info(self, obj):
        return f"{obj.fee.description} ({obj.fee.student})"
    fee_info.short_description = 'Taxa (Aluno)'

    def confirmed_by_display(self, obj):
        if obj.confirmed_by:
            return obj.confirmed_by.username
        return "-"
    confirmed_by_display.short_description = 'Confirmado Por'
    confirmed_by_display.admin_order_field = 'confirmed_by__username'

# Garantir que os modelos referenciados em autocomplete_fields (Student, User, SchoolYear)
# tenham search_fields definidos em seus respectivos ModelAdmins.
# User (padrão do Django ou customizado) e SchoolYear já têm. Student foi configurado em seu app.
