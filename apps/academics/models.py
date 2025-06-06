from django.db import models
from django.conf import settings
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _
from django.utils import timezone # Para default em grading_date e outros

from apps.students.models import GradeLevel, Student # Importar GradeLevel e Student do app students
from apps.accounts.models import User # Import User model for limit_choices_to

class SchoolYear(models.Model):
    """
    Modelo para representar o Ano Letivo.
    Ex: 2023, 2024, etc.
    """
    year = models.IntegerField(
        _('year'),
        unique=True,
        help_text=_('Ano letivo, ex: 2024.')
    )
    start_date = models.DateField(
        _('start date'),
        help_text=_('Data de início do ano letivo.')
    )
    end_date = models.DateField(
        _('end date'),
        help_text=_('Data de término do ano letivo.')
    )
    is_active = models.BooleanField(
        _('is active?'),
        default=False,
        help_text=_('Indica se este é o ano letivo corrente/ativo no sistema.')
    )

    class Meta:
        verbose_name = _('School Year')
        verbose_name_plural = _('School Years')
        ordering = ['-year']

    def __str__(self):
        return str(self.year)

    def clean(self):
        super().clean()
        if self.start_date and self.end_date and self.end_date <= self.start_date:
            raise ValidationError(_('A data de término deve ser posterior à data de início.'))

        if self.is_active:
            active_years = SchoolYear.objects.filter(is_active=True).exclude(pk=self.pk)
            if active_years.exists():
                raise ValidationError(_('Já existe um ano letivo ativo. Desative o ano letivo atual antes de ativar um novo.'))

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)


class Subject(models.Model):
    """
    Modelo para representar Disciplinas ou Matérias.
    Ex: Matemática, Português, História, etc.
    """
    name = models.CharField(
        _('name'),
        max_length=100,
        unique=True,
        help_text=_('Nome da disciplina, ex: "Matemática".')
    )
    description = models.TextField(
        _('description'),
        blank=True,
        null=True,
        help_text=_('Descrição ou ementa da disciplina.')
    )

    class Meta:
        verbose_name = _('Subject')
        verbose_name_plural = _('Subjects')
        ordering = ['name']

    def __str__(self):
        return self.name


class SchoolClass(models.Model):
    """
    Modelo para representar uma Turma específica em um Ano Letivo e Nível Escolar.
    Ex: Turma A do 1º Ano de 2024.
    """
    name = models.CharField(
        _('name'),
        max_length=100,
        help_text=_('Nome ou identificador da turma, ex: "Turma A", "101", "Manhã".')
    )
    school_year = models.ForeignKey(
        SchoolYear,
        on_delete=models.PROTECT,
        related_name='classes',
        verbose_name=_('school year')
    )
    grade_level = models.ForeignKey(
        GradeLevel,
        on_delete=models.PROTECT,
        related_name='classes',
        verbose_name=_('grade level')
    )
    main_teacher = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='main_taught_classes',
        verbose_name=_('main teacher'),
        limit_choices_to={'user_type': 'TEACHER'},
        help_text=_('Professor principal ou regente da turma, se aplicável.')
    )

    class Meta:
        verbose_name = _('School Class')
        verbose_name_plural = _('School Classes')
        unique_together = ('name', 'school_year', 'grade_level')
        ordering = ['school_year', 'grade_level', 'name']

    def __str__(self):
        return f'{self.name} - {self.grade_level.name} ({self.school_year})'


class Enrollment(models.Model):
    """
    Modelo para representar a Matrícula de um Aluno em uma Turma específica.
    """
    STATUS_ACTIVE = 'ACTIVE'
    STATUS_COMPLETED = 'COMPLETED'
    STATUS_TRANSFERRED_OUT = 'TRANSFERRED_OUT'
    STATUS_DROPPED_OUT = 'DROPPED_OUT'

    STATUS_CHOICES = [
        (STATUS_ACTIVE, _('Ativa')),
        (STATUS_COMPLETED, _('Concluída')),
        (STATUS_TRANSFERRED_OUT, _('Transferido (Saída)')),
        (STATUS_DROPPED_OUT, _('Abandono/Evasão')),
    ]

    student = models.ForeignKey(
        Student,
        on_delete=models.CASCADE,
        related_name='enrollments',
        verbose_name=_('student')
    )
    school_class = models.ForeignKey(
        SchoolClass,
        on_delete=models.CASCADE,
        related_name='enrolled_students',
        verbose_name=_('school class')
    )
    enrollment_date = models.DateField(
        _('enrollment date'),
        auto_now_add=True,
        help_text=_('Data em que a matrícula foi efetivada nesta turma.')
    )
    status = models.CharField(
        _('status'),
        max_length=20,
        choices=STATUS_CHOICES,
        default=STATUS_ACTIVE,
        help_text=_('Status atual da matrícula do aluno na turma.')
    )

    class Meta:
        verbose_name = _('Enrollment')
        verbose_name_plural = _('Enrollments')
        unique_together = ('student', 'school_class')
        ordering = ['school_class', 'student__user__first_name', 'student__user__last_name']

    def __str__(self):
        return f'{self.student} em {self.school_class}'


class GradingPeriod(models.Model):
    """
    Modelo para Períodos de Avaliação (Bimestres, Trimestres, Semestres).
    """
    name = models.CharField(
        _('name'),
        max_length=100,
        help_text=_('Nome do período, ex: "1º Bimestre", "Trimestre Final".')
    )
    school_year = models.ForeignKey(
        SchoolYear,
        on_delete=models.CASCADE,
        related_name='grading_periods',
        verbose_name=_('school year')
    )
    start_date = models.DateField(
        _('start date'),
        help_text=_('Data de início do período de avaliação.')
    )
    end_date = models.DateField(
        _('end date'),
        help_text=_('Data de término do período de avaliação.')
    )

    class Meta:
        verbose_name = _('Grading Period')
        verbose_name_plural = _('Grading Periods')
        unique_together = ('name', 'school_year')
        ordering = ['school_year', 'start_date']

    def __str__(self):
        return f'{self.name} ({self.school_year})'

    def clean(self):
        super().clean()
        if self.start_date and self.end_date and self.end_date <= self.start_date:
            raise ValidationError(_('A data de término do período deve ser posterior à data de início.'))

        if self.school_year:
            if self.start_date < self.school_year.start_date:
                raise ValidationError(_('A data de início do período não pode ser anterior à data de início do ano letivo.'))
            if self.end_date > self.school_year.end_date:
                raise ValidationError(_('A data de término do período não pode ser posterior à data de término do ano letivo.'))

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)


class Grade(models.Model):
    """
    Modelo para armazenar uma Nota específica de um Aluno em uma Disciplina,
    dentro de um Período de Avaliação e referente a uma Avaliação específica.
    """
    enrollment = models.ForeignKey(
        Enrollment,
        on_delete=models.CASCADE,
        related_name='grades',
        verbose_name=_('enrollment')
    )
    subject = models.ForeignKey(
        Subject,
        on_delete=models.CASCADE,
        related_name='grades',
        verbose_name=_('subject')
    )
    grading_period = models.ForeignKey(
        GradingPeriod,
        on_delete=models.CASCADE,
        related_name='grades',
        verbose_name=_('grading period')
    )
    assessment_name = models.CharField(
        _('assessment name'),
        max_length=100,
        help_text=_('Nome ou descrição da avaliação, ex: "Prova Bimestral 1", "Trabalho em Grupo - Revolução Francesa", "Participação em Aula".')
    )
    grade_value = models.DecimalField(
        _('grade value'),
        max_digits=5,
        decimal_places=2,
        help_text=_('Valor da nota obtida pelo aluno.')
    )
    weight = models.DecimalField(
        _('weight'),
        max_digits=3,
        decimal_places=2,
        null=True,
        blank=True,
        help_text=_('Peso desta nota para cálculo de média ponderada (ex: 0.4 para 40%). Deixar em branco se não aplicável ou se a média for simples.')
    )
    grading_date = models.DateField(
        _('grading date'),
        default=timezone.now,
        help_text=_('Data de lançamento ou da realização da avaliação.')
    )

    class Meta:
        verbose_name = _('Grade')
        verbose_name_plural = _('Grades')
        ordering = ['enrollment', 'subject', 'grading_period', 'grading_date']

    def __str__(self):
        return f'Nota {self.grade_value} para {self.enrollment.student} em {self.subject.name} ({self.grading_period.name})'


class Attendance(models.Model):
    """
    Modelo para registrar a frequência (presenças e faltas) de um aluno
    em uma disciplina específica em uma determinada data.
    """
    STATUS_PRESENT = 'PRESENT'
    STATUS_ABSENT = 'ABSENT'
    STATUS_JUSTIFIED_ABSENCE = 'JUSTIFIED_ABSENCE'

    STATUS_CHOICES = [
        (STATUS_PRESENT, _('Presente')),
        (STATUS_ABSENT, _('Ausente')),
        (STATUS_JUSTIFIED_ABSENCE, _('Ausência Justificada')),
    ]

    enrollment = models.ForeignKey(
        Enrollment,
        on_delete=models.CASCADE,
        related_name='attendances',
        verbose_name=_('enrollment')
    )
    subject = models.ForeignKey(
        Subject,
        on_delete=models.CASCADE,
        related_name='attendances',
        verbose_name=_('subject')
    )
    date = models.DateField(
        _('date'),
        default=timezone.now,
        help_text=_('Data da aula para a qual a frequência está sendo registrada.')
    )
    status = models.CharField(
        _('status'),
        max_length=20,
        choices=STATUS_CHOICES,
        help_text=_('Status de presença do aluno na aula.')
    )
    notes = models.TextField(
        _('notes'),
        blank=True,
        null=True,
        help_text=_('Observações, como a justificativa para uma ausência.')
    )

    class Meta:
        verbose_name = _('Attendance Record')
        verbose_name_plural = _('Attendance Records')
        unique_together = ('enrollment', 'subject', 'date')
        ordering = ['-date', 'enrollment', 'subject']

    def __str__(self):
        return f'{self.enrollment.student} - {self.subject.name} em {self.date}: {self.get_status_display()}'


class SchoolEvent(models.Model):
    """
    Modelo para Eventos da Agenda Escolar.
    Ex: Provas, Reuniões, Feriados, Atividades Escolares.
    """
    TYPE_EXAM = 'EXAM'
    TYPE_MEETING = 'MEETING'
    TYPE_HOLIDAY = 'HOLIDAY'
    TYPE_SCHOOL_ACTIVITY = 'SCHOOL_ACTIVITY'
    TYPE_OTHER = 'OTHER'

    EVENT_TYPE_CHOICES = [
        (TYPE_EXAM, _('Prova/Avaliação')),
        (TYPE_MEETING, _('Reunião')),
        (TYPE_HOLIDAY, _('Feriado/Recesso')),
        (TYPE_SCHOOL_ACTIVITY, _('Atividade Escolar')),
        (TYPE_OTHER, _('Outro Evento')),
    ]

    title = models.CharField(
        _('title'),
        max_length=200,
        help_text=_('Título do evento.')
    )
    description = models.TextField(
        _('description'),
        blank=True,
        null=True,
        help_text=_('Descrição detalhada do evento.')
    )
    start_time = models.DateTimeField(
        _('start time'),
        help_text=_('Data e hora de início do evento.')
    )
    end_time = models.DateTimeField(
        _('end time'),
        help_text=_('Data e hora de término do evento.')
    )
    event_type = models.CharField(
        _('event type'),
        max_length=30,
        choices=EVENT_TYPE_CHOICES,
        help_text=_('Tipo do evento.')
    )
    target_school_classes = models.ManyToManyField(
        SchoolClass,
        blank=True,
        related_name='events',
        verbose_name=_('target school classes'),
        help_text=_('Selecione as turmas específicas para este evento. Deixe em branco se for para uma série ou para toda a escola.')
    )
    target_grade_levels = models.ManyToManyField(
        GradeLevel,
        blank=True,
        related_name='events',
        verbose_name=_('target grade levels'),
        help_text=_('Selecione as séries específicas. Usado se não for para turmas específicas ou toda a escola.')
    )
    is_school_wide = models.BooleanField(
        _('is school-wide?'),
        default=False,
        help_text=_('Marque se o evento é para toda a escola (ignora turmas/séries específicas).')
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='created_events',
        verbose_name=_('created by'),
        limit_choices_to={'user_type__in': ['TEACHER', 'STAFF', 'ADMIN']},
        help_text=_('Usuário que criou o evento (Professor, Secretaria, Admin).')
    )

    class Meta:
        verbose_name = _('School Event')
        verbose_name_plural = _('School Events')
        ordering = ['start_time']

    def __str__(self):
        return self.title

    def clean(self):
        super().clean()
        if self.start_time and self.end_time and self.end_time <= self.start_time:
            raise ValidationError(_('A data/hora de término deve ser posterior à data/hora de início.'))

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)


class DidacticMaterial(models.Model):
    """
    Modelo para Materiais Didáticos disponibilizados por professores.
    """
    title = models.CharField(
        _('title'),
        max_length=200,
        help_text=_('Título do material didático.')
    )
    description = models.TextField(
        _('description'),
        blank=True,
        null=True,
        help_text=_('Breve descrição do material.')
    )
    file = models.FileField(
        _('file'),
        upload_to='didactic_materials/%Y/%m/',
        help_text=_('Arquivo do material didático (PDF, DOCX, PPTX, etc.).')
    )
    subject = models.ForeignKey(
        Subject,
        on_delete=models.CASCADE,
        related_name='didactic_materials',
        verbose_name=_('subject')
    )
    school_class = models.ForeignKey(
        SchoolClass,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='didactic_materials',
        verbose_name=_('school class'),
        help_text=_('Associe a uma turma específica, ou deixe em branco se for geral para a disciplina/série.')
    )
    uploader = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='uploaded_materials',
        verbose_name=_('uploader'),
        limit_choices_to={'user_type__in': ['TEACHER', 'STAFF', 'ADMIN']},
        help_text=_('Usuário que fez o upload do material (Professor, Secretaria, Admin).')
    )
    upload_date = models.DateTimeField(
        _('upload date'),
        auto_now_add=True,
        help_text=_('Data e hora em que o material foi enviado.')
    )

    class Meta:
        verbose_name = _('Didactic Material')
        verbose_name_plural = _('Didactic Materials')
        ordering = ['subject', '-upload_date']

    def __str__(self):
        return self.title

# Novo modelo a ser adicionado abaixo

class TeacherAssignment(models.Model):
    """
    Modelo para atribuir um Professor a uma Disciplina específica em uma Turma e Ano Letivo.
    """
    teacher = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='assignments',
        verbose_name=_('teacher'),
        limit_choices_to={'user_type': 'TEACHER'},
        help_text=_('Professor atribuído.')
    )
    school_class = models.ForeignKey(
        SchoolClass,
        on_delete=models.CASCADE,
        related_name='teacher_assignments',
        verbose_name=_('school class')
    )
    subject = models.ForeignKey(
        Subject,
        on_delete=models.CASCADE,
        related_name='teacher_assignments',
        verbose_name=_('subject')
    )
    school_year = models.ForeignKey(
        SchoolYear,
        on_delete=models.CASCADE, # Ou models.PROTECT se preferir não excluir atribuições se o ano for removido
        related_name='teacher_assignments',
        verbose_name=_('school year'),
        help_text=_('Ano letivo para o qual esta atribuição é válida.')
    )

    class Meta:
        verbose_name = _('Teacher Assignment')
        verbose_name_plural = _('Teacher Assignments')
        unique_together = ('teacher', 'school_class', 'subject', 'school_year')
        ordering = ['school_year', 'school_class__grade_level__order_in_sequence', 'school_class__name', 'subject__name']

    def __str__(self):
        return f'{self.teacher} - {self.subject} em {self.school_class} ({self.school_year})'


class Announcement(models.Model):
    """
    Modelo para Comunicados Escolares.
    """
    title = models.CharField(
        _('title'),
        max_length=255
    )
    content = models.TextField(
        _('content')
    )
    publication_date = models.DateTimeField(
        _('publication date'),
        auto_now_add=True
    )
    author = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='authored_announcements',
        verbose_name=_('author'),
        limit_choices_to={'user_type__in': [User.USER_TYPE_STAFF, User.USER_TYPE_ADMIN, User.USER_TYPE_TEACHER]}
    )
    # Targeting fields
    target_user_types = models.JSONField(
        _('target user types'),
        null=True,
        blank=True,
        help_text=_("Lista de tipos de usuários que devem ver este comunicado, ex: ['STUDENT', 'PARENT']. Deixe em branco para todos os tipos aplicáveis por outras regras de direcionamento.")
    )
    target_grade_levels = models.ManyToManyField(
        GradeLevel, # Assuming GradeLevel is imported from apps.students.models
        blank=True,
        related_name='announcements',
        verbose_name=_('target grade levels'),
        help_text=_('Selecione as séries específicas para este comunicado. Vazio significa todas as séries aplicáveis por outras regras.')
    )
    target_school_classes = models.ManyToManyField(
        SchoolClass,
        blank=True,
        related_name='announcements',
        verbose_name=_('target school classes'),
        help_text=_('Selecione as turmas específicas. Vazio significa todas as turmas aplicáveis por outras regras.')
    )
    is_school_wide = models.BooleanField(
        _('is school-wide?'),
        default=False,
        help_text=_('Marque se o comunicado é para toda a escola (ignora outros direcionamentos específicos se marcado).')
    )
    expiry_date = models.DateTimeField(
        _('expiry date'),
        null=True,
        blank=True,
        help_text=_('Data após a qual o comunicado não será mais exibido proeminentemente.')
    )

    class Meta:
        verbose_name = _('Announcement')
        verbose_name_plural = _('Announcements')
        ordering = ['-publication_date']

    def __str__(self):
        return self.title

    def clean(self):
        super().clean()
        # Example validation: if is_school_wide is True, other targeting fields might be redundant
        # or should ideally be empty. This depends on desired strictness.
        # For now, we allow them to be set, but UI/UX should guide user.
        if self.target_user_types:
            from apps.accounts.models import User # Local import to avoid circularity if User model imports from academics
            valid_user_types = [choice[0] for choice in User.USER_TYPE_CHOICES]
            for user_type in self.target_user_types:
                if user_type not in valid_user_types:
                    raise ValidationError(
                        _("Tipo de usuário inválido '%(user_type)s' em 'target_user_types'. Escolha de: %(valid_types)s") %
                        {'user_type': user_type, 'valid_types': ", ".join(valid_user_types)}
                    )

        if self.expiry_date and self.expiry_date < timezone.now(): # Use timezone.now() for datetime comparison
            raise ValidationError(_("A data de expiração não pode ser no passado."))

    def save(self, *args, **kwargs):
        # Ensure author is set if not already (e.g. if created via admin panel without perform_create)
        # This is more a safeguard; perform_create in ViewSet is primary for setting author.
        # if not self.author_id and hasattr(self, '_current_user') and self._current_user and self._current_user.is_authenticated:
        #     self.author = self._current_user
        self.full_clean()
        super().save(*args, **kwargs)
