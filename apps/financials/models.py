from django.db import models
from django.conf import settings # Adicionado para settings.AUTH_USER_MODEL
from django.utils import timezone # Adicionado para default de datas
from django.utils.translation import gettext_lazy as _
from apps.students.models import Student # Reverted import
from apps.academics.models import SchoolYear # Reverted import

class Fee(models.Model):
    """
    Modelo para representar Taxas, Boletos ou Cobranças financeiras
    associadas a um aluno para um determinado ano letivo.
    """
    STATUS_PENDING = 'PENDING'
    STATUS_PAID = 'PAID'
    STATUS_OVERDUE = 'OVERDUE'
    STATUS_CANCELED = 'CANCELED'
    STATUS_PARTIALLY_PAID = 'PARTIALLY_PAID'

    STATUS_CHOICES = [
        (STATUS_PENDING, _('Pendente')),
        (STATUS_PAID, _('Pago')),
        (STATUS_OVERDUE, _('Vencido')),
        (STATUS_CANCELED, _('Cancelado')),
        (STATUS_PARTIALLY_PAID, _('Parcialmente Pago')),
    ]

    student = models.ForeignKey(
        Student,
        on_delete=models.PROTECT,
        related_name='fees',
        verbose_name=_('student'),
        help_text=_('Aluno ao qual esta taxa se refere.')
    )
    school_year = models.ForeignKey(
        SchoolYear,
        on_delete=models.PROTECT,
        related_name='fees',
        verbose_name=_('school year'),
        help_text=_('Ano letivo da taxa.')
    )
    description = models.CharField(
        _('description'),
        max_length=255,
        help_text=_('Descrição da taxa (ex: Mensalidade Março/2024, Taxa de Material Didático).')
    )
    due_date = models.DateField(
        _('due date'),
        help_text=_('Data de vencimento.')
    )
    amount = models.DecimalField(
        _('amount'),
        max_digits=10,
        decimal_places=2,
        help_text=_('Valor original da taxa.')
    )
    status = models.CharField(
        _('status'),
        max_length=20,
        choices=STATUS_CHOICES,
        default=STATUS_PENDING,
        help_text=_('Status atual da taxa.')
    )
    payment_gateway_id = models.CharField(
        _('payment gateway ID'),
        max_length=255,
        blank=True,
        null=True,
        help_text=_('ID externo do boleto/cobrança no gateway de pagamento.')
    )
    barcode = models.CharField(
        _('barcode'),
        max_length=255,
        blank=True,
        null=True,
        help_text=_('Código de barras do boleto, se aplicável.')
    )
    notes = models.TextField(
        _('notes'),
        blank=True,
        null=True,
        help_text=_('Observações internas sobre a taxa (ex: negociações, isenções parciais).')
    )

    discount_amount = models.DecimalField(
        _('discount amount'),
        max_digits=10,
        decimal_places=2,
        default=0.00,
        help_text=_('Valor do desconto aplicado.')
    )
    penalty_amount = models.DecimalField(
        _('penalty amount'),
        max_digits=10,
        decimal_places=2,
        default=0.00,
        help_text=_('Valor da multa por atraso.')
    )
    amount_paid = models.DecimalField(
        _('amount paid'),
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        default=None,
        help_text=_('Valor efetivamente pago.')
    )
    payment_date = models.DateField(
        _('payment date'),
        null=True,
        blank=True,
        help_text=_('Data em que o pagamento foi efetuado/confirmado.')
    )

    created_at = models.DateTimeField(_('created at'), auto_now_add=True)
    updated_at = models.DateTimeField(_('updated at'), auto_now=True)

    class Meta:
        verbose_name = _('Fee')
        verbose_name_plural = _('Fees')
        ordering = ['due_date', 'student']

    def __str__(self):
        return f'{self.description} - {self.student} (Venc: {self.due_date})'

    @property
    def is_overdue(self):
        if self.status == self.STATUS_PENDING and self.due_date < timezone.now().date():
            return True
        return False

    @property
    def total_value(self):
        return self.amount - self.discount_amount + self.penalty_amount


class FeeEditLog(models.Model):
    """
    Log de alterações manuais em uma taxa/cobrança.
    """
    fee = models.ForeignKey(
        Fee,
        on_delete=models.CASCADE,
        related_name='edit_logs',
        verbose_name=_('fee')
    )
    edited_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='fee_edits',
        verbose_name=_('edited by'),
        limit_choices_to={'is_staff': True},
        help_text=_('Usuário (staff) que realizou a alteração.')
    )
    timestamp = models.DateTimeField(
        _('timestamp'),
        auto_now_add=True
    )
    field_changed = models.CharField(
        _('field changed'),
        max_length=50,
        default='amount', # Exemplo, poderia ser status, due_date, etc.
        help_text=_('Campo que foi alterado (ex: amount, due_date, status).')
    )
    previous_value = models.CharField(
        _('previous value'),
        max_length=255,
        help_text=_('Valor anterior do campo.')
    )
    new_value = models.CharField(
        _('new value'),
        max_length=255,
        help_text=_('Novo valor do campo.')
    )
    reason = models.TextField(
        _('reason'),
        help_text=_('Motivo da alteração manual.')
    )

    class Meta:
        verbose_name = _('Fee Edit Log')
        verbose_name_plural = _('Fee Edit Logs')
        ordering = ['-timestamp']

    def __str__(self):
        return f'Log para {self.fee.description} ({self.fee.student}) em {self.timestamp.strftime("%Y-%m-%d %H:%M")}'


class Payment(models.Model):
    """
    Modelo para registrar um Pagamento efetuado para uma Taxa.
    Uma taxa pode ter múltiplos pagamentos parciais.
    """
    METHOD_BOLETO = 'BOLETO'
    METHOD_CREDIT_CARD = 'CREDIT_CARD'
    METHOD_PIX = 'PIX'
    METHOD_CASH = 'CASH'
    METHOD_BANK_TRANSFER = 'BANK_TRANSFER'
    METHOD_OTHER = 'OTHER'

    PAYMENT_METHOD_CHOICES = [
        (METHOD_BOLETO, _('Boleto Bancário')),
        (METHOD_CREDIT_CARD, _('Cartão de Crédito')),
        (METHOD_PIX, _('PIX')),
        (METHOD_CASH, _('Dinheiro')),
        (METHOD_BANK_TRANSFER, _('Transferência Bancária')),
        (METHOD_OTHER, _('Outro')),
    ]

    fee = models.ForeignKey(
        Fee,
        on_delete=models.PROTECT, # Proteger a taxa se houver pagamentos associados
        related_name='payments',
        verbose_name=_('fee'),
        help_text=_('Taxa à qual este pagamento se refere.')
    )
    payment_date = models.DateField(
        _('payment date'),
        default=timezone.now,
        help_text=_('Data em que o pagamento foi efetuado/registrado.')
    )
    amount_paid = models.DecimalField(
        _('amount paid'),
        max_digits=10,
        decimal_places=2,
        help_text=_('Valor efetivamente pago nesta transação.')
    )
    payment_method = models.CharField(
        _('payment method'),
        max_length=20,
        choices=PAYMENT_METHOD_CHOICES,
        help_text=_('Método utilizado para o pagamento.')
    )
    transaction_id = models.CharField(
        _('transaction ID'),
        max_length=255,
        blank=True,
        null=True,
        help_text=_('ID da transação no gateway de pagamento ou referência interna/documento.')
    )
    notes = models.TextField(
        _('notes'),
        blank=True,
        null=True,
        help_text=_('Observações sobre o pagamento (ex: pago na secretaria, referente a acordo).')
    )
    confirmed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='confirmed_payments',
        verbose_name=_('confirmed by'),
        limit_choices_to={'is_staff': True},
        help_text=_('Usuário (staff) que confirmou o recebimento do pagamento (se aplicável).')
    )
    created_at = models.DateTimeField(_('created at'), auto_now_add=True)
    # updated_at não é estritamente necessário aqui, a menos que pagamentos sejam editáveis.

    class Meta:
        verbose_name = _('Payment')
        verbose_name_plural = _('Payments')
        ordering = ['-payment_date', '-created_at']

    def __str__(self):
        return f'Pagamento de {self.amount_paid} para {self.fee.description} ({self.fee.student}) em {self.payment_date.strftime("%Y-%m-%d")}'

    def save(self, *args, **kwargs):
        # Lógica para atualizar o status da Fee associada pode ser colocada aqui
        # ou preferencialmente em um signal handler (post_save para Payment).
        super().save(*args, **kwargs)
        # Exemplo de lógica (simplificada) para atualizar Fee após salvar Payment:
        # self.fee.amount_paid = sum(p.amount_paid for p in self.fee.payments.all() if p.amount_paid) # Recalcula o total pago
        # if self.fee.amount_paid >= self.fee.total_value:
        #     self.fee.status = Fee.STATUS_PAID
        # elif self.fee.amount_paid > 0:
        #     self.fee.status = Fee.STATUS_PARTIALLY_PAID
        # # else: manter status atual ou reavaliar se PENDING/OVERDUE
        # self.fee.payment_date = self.payment_date # Atualiza a data do último pagamento na Fee
        # self.fee.save()
