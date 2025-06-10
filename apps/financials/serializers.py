from rest_framework import serializers
from .models import Fee, FeeEditLog, Payment
from django.utils.translation import gettext_lazy as _
from django.utils import timezone # Para validação de data no PaymentWriteSerializer

class FeeSerializer(serializers.ModelSerializer):
    """
    Read-only serializer for Fee details.
    Includes calculated fields like student name, school year string representation,
    status display, overdue status, and total value.
    """
    student = serializers.PrimaryKeyRelatedField(read_only=True, help_text=_("ID of the student associated with this fee."))
    student_name = serializers.SerializerMethodField(method_name='get_student_name_typed', help_text=_("Full name of the student."))
    school_year = serializers.PrimaryKeyRelatedField(read_only=True, help_text=_("ID of the school year this fee pertains to."))
    school_year_str = serializers.CharField(source='school_year.__str__', read_only=True, help_text=_("String representation of the school year (e.g., '2023-2024')."))
    description = serializers.CharField(read_only=True, help_text=_("Description of the fee (e.g., Monthly Fee, Material Fee)."))
    due_date = serializers.DateField(read_only=True, help_text=_("Date when the fee is due."))
    amount = serializers.DecimalField(max_digits=10, decimal_places=2, read_only=True, help_text=_("Base amount of the fee."))
    status = serializers.CharField(read_only=True, help_text=_("Current status of the fee (e.g., PENDING, PAID)."))
    status_display = serializers.CharField(source='get_status_display', read_only=True, help_text=_("Display name for the fee status."))
    payment_gateway_id = serializers.CharField(read_only=True, allow_null=True, help_text=_("Optional ID from an external payment gateway."))
    barcode = serializers.CharField(read_only=True, allow_null=True, help_text=_("Barcode for payment slip, if applicable."))
    notes = serializers.CharField(read_only=True, allow_null=True, help_text=_("Administrative notes regarding this fee."))
    discount_amount = serializers.DecimalField(max_digits=10, decimal_places=2, read_only=True, help_text=_("Amount of discount applied to this fee."))
    penalty_amount = serializers.DecimalField(max_digits=10, decimal_places=2, read_only=True, help_text=_("Penalty amount for late payment, if any."))
    amount_paid = serializers.DecimalField(max_digits=10, decimal_places=2, read_only=True, help_text=_("Total amount paid towards this fee so far."))
    payment_date = serializers.DateField(read_only=True, allow_null=True, help_text=_("Date when the fee was fully or partially paid."))
    is_overdue = serializers.BooleanField(read_only=True, help_text=_("True if the fee is past its due date and not fully paid."))
    total_value = serializers.DecimalField(max_digits=10, decimal_places=2, read_only=True, help_text=_("Calculated total value of the fee (amount - discount + penalty)."))
    created_at = serializers.DateTimeField(read_only=True, help_text=_("Timestamp of fee creation."))
    updated_at = serializers.DateTimeField(read_only=True, help_text=_("Timestamp of last fee update."))


    class Meta:
        model = Fee
        fields = (
            'id',
            'student',
            'student_name',
            'school_year',
            'school_year_str',
            'description',
            'due_date',
            'amount',
            'status',
            'status_display',
            'payment_gateway_id',
            'barcode',
            'notes',
            'discount_amount',
            'penalty_amount',
            'amount_paid',
            'payment_date',
            'is_overdue',
            'total_value',
            'created_at',
            'updated_at', # All fields included for comprehensive read-only view
        )
        read_only_fields = fields # Ensure all are read-only

    def get_student_name_typed(self, obj: Fee) -> str | None:
        if obj.student and obj.student.user:
            return obj.student.user.get_full_name() or obj.student.user.username
        return None

class FeeEditLogSerializer(serializers.ModelSerializer):
    """
    Serializer for FeeEditLog entries.
    Provides a read-only log of changes made to Fee records.
    """
    edited_by = serializers.PrimaryKeyRelatedField(read_only=True, help_text=_("User who made the change."))
    edited_by_name = serializers.SerializerMethodField(method_name='get_edited_by_name_typed', help_text=_("Name of the user who made the change."))
    fee = serializers.PrimaryKeyRelatedField(read_only=True, help_text=_("The fee that was edited."))
    fee_description = serializers.CharField(source='fee.description', read_only=True, help_text=_("Description of the fee that was edited."))
    timestamp = serializers.DateTimeField(read_only=True, help_text=_("When the change was made."))
    field_changed = serializers.CharField(read_only=True, help_text=_("The specific field of the fee that was changed."))
    previous_value = serializers.CharField(read_only=True, help_text=_("Value of the field before the change."))
    new_value = serializers.CharField(read_only=True, help_text=_("Value of the field after the change."))
    reason = serializers.CharField(read_only=True, help_text=_("Reason provided for making the change."))


    class Meta:
        model = FeeEditLog
        fields = (
            'id',
            'fee',
            'fee_description',
            'edited_by',
            'edited_by_name',
            'timestamp',
            'field_changed',
            'previous_value',
            'new_value', # All relevant fields included
            'reason',
        )
        read_only_fields = fields # All fields are read-only


    def get_edited_by_name_typed(self, obj: FeeEditLog) -> str | None:
        if obj.edited_by:
            return obj.edited_by.get_full_name() or obj.edited_by.username
        return None

class PaymentSerializer(serializers.ModelSerializer): # Read-focused
    """
    Read-only serializer for Payment details.
    Includes display names for choices and related object information.
    """
    fee = serializers.PrimaryKeyRelatedField(read_only=True, help_text=_("ID of the fee this payment is associated with."))
    fee_description = serializers.CharField(source='fee.description', read_only=True, help_text=_("Description of the associated fee."))
    student_name = serializers.SerializerMethodField(method_name='get_student_name_typed', help_text=_("Name of the student this payment is for (via the fee)."))
    payment_date = serializers.DateField(read_only=True, help_text=_("Date the payment was made."))
    amount_paid = serializers.DecimalField(max_digits=10, decimal_places=2, read_only=True, help_text=_("Amount paid in this transaction."))
    payment_method = serializers.CharField(read_only=True, help_text=_("Method used for payment (e.g., CC, BANK_TRANSFER)."))
    payment_method_display = serializers.CharField(source='get_payment_method_display', read_only=True, help_text=_("Display name for the payment method."))
    transaction_id = serializers.CharField(read_only=True, allow_null=True, help_text=_("Optional transaction ID from a payment gateway or bank."))
    notes = serializers.CharField(read_only=True, allow_null=True, help_text=_("Administrative notes about this payment."))
    confirmed_by = serializers.PrimaryKeyRelatedField(read_only=True, allow_null=True, help_text=_("User who confirmed this payment, if applicable."))
    confirmed_by_name = serializers.SerializerMethodField(method_name='get_confirmed_by_name_typed', help_text=_("Name of the user who confirmed the payment."))
    created_at = serializers.DateTimeField(read_only=True, help_text=_("Timestamp of when this payment record was created."))

    class Meta:
        model = Payment
        fields = (
            'id',
            'fee',
            'fee_description',
            'student_name',
            'payment_date',
            'amount_paid',
            'payment_method',
            'payment_method_display',
            'transaction_id',
            'notes',
            'confirmed_by',
            'confirmed_by_name', # User who confirmed
            'created_at',
        )
        read_only_fields = fields # All fields are read-only

    def get_student_name_typed(self, obj: Payment) -> str | None:
        if obj.fee and obj.fee.student and obj.fee.student.user:
            return obj.fee.student.user.get_full_name() or obj.fee.student.user.username
        return None

    def get_confirmed_by_name_typed(self, obj: Payment) -> str | None:
        if obj.confirmed_by:
            return obj.confirmed_by.get_full_name() or obj.confirmed_by.username
        return None

class FeeWriteSerializer(serializers.ModelSerializer):
    """
    Serializer for creating and updating Fee records.
    Includes a field for edit reason when updating.
    """
    # Need to import Student and SchoolYear models to use in queryset
    from apps.students.models import Student
    from apps.academics.models import SchoolYear

    student = serializers.PrimaryKeyRelatedField(queryset=Student.objects.all(), help_text=_("ID of the student this fee applies to."))
    school_year = serializers.PrimaryKeyRelatedField(queryset=SchoolYear.objects.all(), help_text=_("ID of the school year for this fee."))
    description = serializers.CharField(max_length=255, help_text=_("Description of the fee."))
    due_date = serializers.DateField(help_text=_("Date when the fee is due."))
    amount = serializers.DecimalField(max_digits=10, decimal_places=2, help_text=_("Base amount of the fee."))
    status = serializers.ChoiceField(choices=Fee.STATUS_CHOICES, help_text=_("Current status of the fee.")) # Corrected to STATUS_CHOICES
    notes = serializers.CharField(required=False, allow_blank=True, style={'base_template': 'textarea.html'}, help_text=_("Optional administrative notes."))
    payment_gateway_id = serializers.CharField(max_length=100, required=False, allow_blank=True, help_text=_("Optional ID from an external payment gateway."))
    barcode = serializers.CharField(max_length=255, required=False, allow_blank=True, help_text=_("Optional barcode for payment slip."))
    discount_amount = serializers.DecimalField(max_digits=10, decimal_places=2, default=0, help_text=_("Amount of discount. Defaults to 0."))
    penalty_amount = serializers.DecimalField(max_digits=10, decimal_places=2, default=0, help_text=_("Penalty for late payment. Defaults to 0."))
    amount_paid = serializers.DecimalField(max_digits=10, decimal_places=2, default=0, help_text=_("Amount already paid. Defaults to 0."))
    payment_date = serializers.DateField(required=False, allow_null=True, help_text=_("Date of last payment, if any."))
    edit_reason = serializers.CharField(write_only=True, required=False, allow_blank=True, label=_("Motivo da Edição"), help_text=_("Reason for editing the fee, required for updates if changes are significant."))


    class Meta:
        model = Fee
        fields = (
            'student',
            'school_year',
            'description',
            'due_date',
            'amount',
            'status',
            'notes',
            'payment_gateway_id',
            'barcode',
            'discount_amount',
            'penalty_amount',
            'amount_paid',
            'payment_date',
            'edit_reason',
        )

    def validate_amount_paid(self, value):
        if value is not None and value < 0:
            raise serializers.ValidationError(_("Amount paid cannot be negative."))
        return value

    def validate_amount(self, value):
        if value < 0:
            raise serializers.ValidationError(_("Fee amount cannot be negative."))
        return value

    def validate(self, data):
        school_year = data.get('school_year')
        due_date = data.get('due_date')

        if school_year and due_date:
            if not (school_year.start_date <= due_date <= school_year.end_date):
                raise serializers.ValidationError({
                    'due_date': _("Due date must be within the selected school year (%(start_date)s - %(end_date)s).") %
                                {'start_date': school_year.start_date, 'end_date': school_year.end_date}
                })

        amount_paid = data.get('amount_paid')
        payment_date = data.get('payment_date')
        status = data.get('status')

        # Obter 'amount' da instância se estiver atualizando e não estiver nos dados, ou dos dados se estiver criando/atualizando
        amount = data.get('amount', getattr(self.instance, 'amount', None))


        if amount_paid is not None: # Se amount_paid está sendo fornecido/alterado
            if not payment_date: # payment_date é obrigatório se amount_paid for fornecido
                payment_date_from_instance = getattr(self.instance, 'payment_date', None)
                if not payment_date_from_instance : # Se não há data de pagamento nem na instância nem nos dados
                     raise serializers.ValidationError({'payment_date': _("Payment date is required if amount paid is provided.")})

            if amount is not None:
                if amount_paid > 0 and amount_paid < amount and status not in [Fee.STATUS_PARTIALLY_PAID, Fee.STATUS_PENDING, Fee.STATUS_OVERDUE]:
                    raise serializers.ValidationError({'status': _("Status should be 'Partially Paid', 'Pending', or 'Overdue' if amount paid is less than total amount.")})
                elif amount_paid >= amount and status != Fee.STATUS_PAID:
                    # Permitir que o status seja PENDING ou OVERDUE mesmo se o valor já foi pago,
                    # pois a secretaria pode estar apenas registrando o valor pago antes de mudar o status.
                    # A lógica de mudança de status baseada no valor pago será na view/signal.
                    pass
        elif status == Fee.STATUS_PAID or status == Fee.STATUS_PARTIALLY_PAID :
            if amount_paid is None or (amount_paid == 0 and (amount or 0) != 0 ): # amount pode ser None se não estiver nos dados e self.instance for None
                 raise serializers.ValidationError({'amount_paid': _("Amount paid must be provided if status is 'Paid' or 'Partially Paid' (unless fee amount is zero).")})
        return data

class PaymentWriteSerializer(serializers.ModelSerializer):
    """
    Serializer para criação de Pagamentos (Payment) pela secretaria/administração.
    """
    class Meta:
        model = Payment
        fields = (
            'fee',
            'payment_date',
            'amount_paid',
            'payment_method',
            'transaction_id',
            'notes',
            # 'confirmed_by' será definido na view
        )

    def validate_payment_date(self, value):
        if value > timezone.now().date():
            raise serializers.ValidationError(_("Payment date cannot be in the future."))
        return value

    def validate_amount_paid(self, value):
        if value <= 0:
            raise serializers.ValidationError(_("Amount paid must be a positive value."))
        return value

    def validate(self, data):
        fee = data.get('fee')
        amount_paid_new = data.get('amount_paid') # Pagamento atual sendo registrado

        if fee and amount_paid_new:
            # Verificar se o pagamento não excede o valor restante da taxa
            current_total_paid_on_fee = fee.payments.exclude(pk=getattr(self.instance, 'pk', None)).aggregate(total=models.Sum('amount_paid'))['total'] or 0

            # Se for uma atualização, precisamos subtrair o valor anterior deste pagamento
            # if self.instance and self.instance.pk:
            #     current_total_paid_on_fee -= self.instance.amount_paid

            # Não permitir que o total de pagamentos (incluindo este novo) exceda muito o valor da taxa.
            # Uma pequena margem pode ser permitida para casos de arredondamento ou pequenas multas não registradas.
            # A lógica exata de "exceder" pode variar.
            # Aqui, vamos impedir que este pagamento isoladamente seja maior que o valor total da taxa.
            # A lógica mais complexa de totais e status da taxa fica na view.
            if amount_paid_new > fee.total_value and fee.status != Fee.STATUS_PENDING and fee.status != Fee.STATUS_OVERDUE and fee.status != Fee.STATUS_PARTIALLY_PAID : # Permitir pagar mais se estiver pendente/vencido/parcial
                 pass # A lógica na view vai tratar o status da Fee

            if fee.status == Fee.STATUS_PAID and (current_total_paid_on_fee + amount_paid_new) > fee.total_value:
                 # Se a taxa já está PAGA, não permitir mais pagamentos que aumentem o valor pago além do necessário
                 # A menos que seja um estorno (valor negativo, que não é o caso aqui devido à validação de amount_paid)
                 pass # A lógica de estorno seria mais complexa. Por ora, a view pode impedir novos pagamentos em Fee paga.


            # Validar se a data do pagamento está dentro do ano letivo da taxa
            if fee.school_year and not (fee.school_year.start_date <= data.get('payment_date') <= fee.school_year.end_date):
                raise serializers.ValidationError({
                    'payment_date': _("Payment date must be within the fee's school year (%(start_date)s - %(end_date)s).") %
                                    {'start_date': fee.school_year.start_date, 'end_date': fee.school_year.end_date}
                })
        return data
