from django.db import models
from django.conf import settings
from django.utils.translation import gettext_lazy as _

class GradeLevel(models.Model):
    """
    Modelo para representar os níveis/séries escolares (ex: 1º Ano, 2ª Série, etc.).
    """
    name = models.CharField(
        _('name'),
        max_length=100,
        unique=True,
        help_text=_('Nome da série/nível escolar, ex: "1º Ano Ensino Fundamental".')
    )
    order_in_sequence = models.PositiveSmallIntegerField(
        _('order in sequence'),
        unique=True,
        help_text=_('Ordem em que a série aparece na progressão escolar, ex: 1 para a primeira série, 2 para a segunda, etc.')
    )

    class Meta:
        verbose_name = _('Grade Level')
        verbose_name_plural = _('Grade Levels')
        ordering = ['order_in_sequence']

    def __str__(self):
        return self.name

class Student(models.Model):
    """
    Modelo para representar um aluno.
    Este modelo estende o UserProfile com informações específicas do aluno.
    """
    STATUS_PRE_REGISTERED = 'PRE_REGISTERED'
    STATUS_PENDING_VALIDATION = 'PENDING_VALIDATION'
    STATUS_ACTIVE = 'ACTIVE'
    STATUS_INACTIVE = 'INACTIVE'
    STATUS_TRANSFERRED = 'TRANSFERRED'
    STATUS_GRADUATED = 'GRADUATED'
    STATUS_REJECTED = 'REJECTED' # Novo status adicionado

    REGISTRATION_STATUS_CHOICES = [
        (STATUS_PRE_REGISTERED, _('Pré-Cadastrado')),
        (STATUS_PENDING_VALIDATION, _('Pendente de Validação')),
        (STATUS_ACTIVE, _('Ativo')),
        (STATUS_INACTIVE, _('Inativo')),
        (STATUS_TRANSFERRED, _('Transferido')),
        (STATUS_GRADUATED, _('Graduado')),
        (STATUS_REJECTED, _('Rejeitado')), # Novo status adicionado
    ]

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        primary_key=True, # Define user como chave primária
        related_name='student_profile', # Permite acesso reverso User.student_profile
        verbose_name=_('user account')
    )
    # Série/nível que o aluno pretende cursar ou está pré-cadastrado
    grade_level_pretended = models.ForeignKey(
        GradeLevel,
        on_delete=models.SET_NULL, # Se a série for deletada, não apagar o aluno, apenas desassociar
        null=True,
        blank=True,
        related_name='aspiring_students',
        verbose_name=_('grade level pretended')
    )
    # Data da matrícula efetiva (após validação)
    enrollment_date = models.DateField(
        _('enrollment date'),
        null=True,
        blank=True,
        help_text=_('Data em que a matrícula do aluno foi efetivada.')
    )
    registration_status = models.CharField(
        _('registration status'),
        max_length=20, # Mantido como 20, 'PENDING_VALIDATION' é o mais longo com 18.
        choices=REGISTRATION_STATUS_CHOICES,
        default=STATUS_PRE_REGISTERED,
        help_text=_('Status atual do cadastro/matrícula do aluno.')
    )
    school_entry_date = models.DateField(
        _('school entry date'),
        null=True,
        blank=True,
        help_text=_('Data de ingresso do aluno na instituição (pode ser diferente da data de matrícula no ano letivo atual).')
    )
    allergies = models.TextField(
        _('allergies'),
        null=True,
        blank=True,
        help_text=_('Informações sobre alergias do aluno.')
    )
    observations = models.TextField(
        _('observations'),
        null=True,
        blank=True,
        help_text=_('Outras observações relevantes sobre o aluno.')
    )
    # Novo campo para motivo de rejeição, conforme sugerido na tarefa
    rejection_reason = models.TextField(
        _('rejection reason'),
        null=True,
        blank=True,
        help_text=_('Motivo pelo qual a matrícula ou pré-cadastro foi rejeitado.')
    )


    class Meta:
        verbose_name = _('Student')
        verbose_name_plural = _('Students')
        ordering = ['user__first_name', 'user__last_name'] # Ordenar por nome do usuário associado

    def __str__(self):
        # Tenta obter o nome completo, senão usa o username.
        # É importante que o user tenha sido carregado (select_related('user') em querysets pode ajudar)
        if hasattr(self.user, 'get_full_name') and self.user.get_full_name():
            return self.user.get_full_name()
        return self.user.username


class StudentParentAssociation(models.Model):
    """
    Modelo para associar um aluno a um ou mais pais/responsáveis.
    """
    REL_FATHER = 'FATHER'
    REL_MOTHER = 'MOTHER'
    REL_LEGAL_GUARDIAN = 'LEGAL_GUARDIAN'
    REL_FINANCIAL_GUARDIAN = 'FINANCIAL_GUARDIAN'
    REL_OTHER = 'OTHER'

    RELATIONSHIP_CHOICES = [
        (REL_FATHER, _('Pai')),
        (REL_MOTHER, _('Mãe')),
        (REL_LEGAL_GUARDIAN, _('Responsável Legal')),
        (REL_FINANCIAL_GUARDIAN, _('Responsável Financeiro')),
        (REL_OTHER, _('Outro')),
    ]

    student = models.ForeignKey(
        Student,
        on_delete=models.CASCADE,
        related_name='parent_associations',
        verbose_name=_('student')
    )
    parent_user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='child_associations',
        verbose_name=_('parent/guardian user'),
        limit_choices_to={'user_type': 'PARENT'}, # Restringe a seleção no Django Admin/Forms
        help_text=_('Usuário do tipo "Pai/Responsável".')
    )
    relationship_type = models.CharField(
        _('relationship type'),
        max_length=30,
        choices=RELATIONSHIP_CHOICES,
        help_text=_('Tipo de relação entre o responsável e o aluno.')
    )

    class Meta:
        verbose_name = _('Student-Parent Association')
        verbose_name_plural = _('Student-Parent Associations')
        unique_together = ('student', 'parent_user', 'relationship_type')
        ordering = ['student', 'parent_user']

    def __str__(self):
        return f'{self.parent_user} - {self.get_relationship_type_display()} de {self.student}'


class StudentDocument(models.Model):
    """
    Modelo para armazenar documentos dos alunos.
    """
    DOC_RG_ALUNO = 'RG_ALUNO'
    DOC_CPF_ALUNO = 'CPF_ALUNO'
    DOC_COMP_RESIDENCIA = 'COMP_RESIDENCIA_RESP'
    DOC_CARTEIRA_VACINACAO = 'CARTEIRA_VACINACAO'
    DOC_HIST_ESCOLAR = 'HIST_ESCOLAR'
    DOC_LAUDO_MEDICO = 'LAUDO_MEDICO'
    DOC_FOTO_3X4 = 'FOTO_3X4'
    DOC_RG_RESPONSAVEL = 'RG_RESPONSAVEL'
    DOC_CPF_RESPONSAVEL = 'CPF_RESPONSAVEL'
    DOC_DECLARACAO_QUITACAO = 'DECLARACAO_QUITACAO_ESCOLA_ANT'
    DOC_OUTRO = 'OUTRO'

    DOCUMENT_TYPE_CHOICES = [
        (DOC_RG_ALUNO, _('RG do Aluno')),
        (DOC_CPF_ALUNO, _('CPF do Aluno')),
        (DOC_COMP_RESIDENCIA, _('Comprovante de Residência do Responsável')),
        (DOC_CARTEIRA_VACINACAO, _('Carteira de Vacinação')),
        (DOC_HIST_ESCOLAR, _('Histórico Escolar da Escola Anterior')),
        (DOC_LAUDO_MEDICO, _('Laudo Médico (para necessidades especiais)')),
        (DOC_FOTO_3X4, _('Foto 3x4 Recente')),
        (DOC_RG_RESPONSAVEL, _('RG do Responsável')),
        (DOC_CPF_RESPONSAVEL, _('CPF do Responsável')),
        (DOC_DECLARACAO_QUITACAO, _('Declaração de Quitação da Escola Anterior')),
        (DOC_OUTRO, _('Outro Documento')),
    ]

    STATUS_PENDING = 'PENDING'
    STATUS_APPROVED = 'APPROVED'
    STATUS_REJECTED = 'REJECTED' # Status já existia aqui, o que é bom.

    VALIDATION_STATUS_CHOICES = [
        (STATUS_PENDING, _('Pendente de Validação')),
        (STATUS_APPROVED, _('Aprovado')),
        (STATUS_REJECTED, _('Rejeitado')),
    ]

    student = models.ForeignKey(
        Student,
        on_delete=models.CASCADE,
        related_name='documents',
        verbose_name=_('student')
    )
    document_type = models.CharField(
        _('document type'),
        max_length=50,
        choices=DOCUMENT_TYPE_CHOICES,
        help_text=_('Tipo do documento.')
    )
    document_name = models.CharField(
        _('document name'),
        max_length=255,
        blank=True,
        help_text=_('Nome descritivo do documento, ex: RG Frente, Comprovante Março/2024. Preenchido se "Outro Documento" ou para especificar.')
    )
    file = models.FileField(
        _('file'),
        upload_to='student_documents/%Y/%m/%d/',
        help_text=_('Arquivo do documento.')
    )
    upload_date = models.DateField(
        _('upload date'),
        auto_now_add=True,
        help_text=_('Data em que o arquivo foi enviado.')
    )
    validation_status = models.CharField(
        _('validation status'),
        max_length=10,
        choices=VALIDATION_STATUS_CHOICES,
        default=STATUS_PENDING,
        help_text=_('Status da validação do documento pela secretaria.')
    )
    is_optional = models.BooleanField(
        _('is optional?'),
        default=False,
        help_text=_('Marque se este tipo de documento é opcional para a matrícula.')
    )
    notes = models.TextField(
        _('notes'),
        blank=True,
        null=True,
        help_text=_('Observações da secretaria sobre o documento (ex: motivo da rejeição).')
    )

    class Meta:
        verbose_name = _('Student Document')
        verbose_name_plural = _('Student Documents')
        ordering = ['student', '-upload_date']

    def __str__(self):
        return f'{self.get_document_type_display()} - {self.student}'
