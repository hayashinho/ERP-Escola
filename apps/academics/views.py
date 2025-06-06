from django.db.models import Q
from django.shortcuts import get_object_or_404
from django.core.exceptions import PermissionDenied
from rest_framework import viewsets, status, serializers as drf_serializers
from rest_framework.permissions import IsAuthenticated, IsAdminUser
from rest_framework.response import Response
from rest_framework.decorators import action
from rest_framework.parsers import MultiPartParser, FormParser # Importar parsers para upload

from apps.accounts.models import User
from apps.accounts.permissions import IsTeacher
from apps.students.models import Student, StudentParentAssociation
from apps.academics.models import (
    Grade, Attendance, SchoolEvent, Enrollment, DidacticMaterial, TeacherAssignment,
    GradingPeriod, Subject, SchoolClass, SchoolYear
)
from apps.academics.serializers import (
    GradeSerializer, AttendanceSerializer, SchoolEventSerializer, DidacticMaterialSerializer,
    TeacherAssignmentSerializer, StudentGradeSheetSerializer, GradeWriteSerializer,
    AttendanceWriteSerializer, SchoolEventWriteSerializer, DidacticMaterialWriteSerializer # Importar DidacticMaterialWriteSerializer
)

class BaseMyStudentDataViewSet(viewsets.ReadOnlyModelViewSet):
    permission_classes = [IsAuthenticated]
    related_field_lookup_student = None
    related_field_lookup_student_id_in = None

    def _filter_queryset_by_user_role(self, initial_queryset):
        user = self.request.user
        if not self.related_field_lookup_student or not self.related_field_lookup_student_id_in:
            return initial_queryset.none()
        if user.user_type == User.USER_TYPE_STUDENT:
            try:
                student = Student.objects.get(user=user)
                return initial_queryset.filter(**{self.related_field_lookup_student: student})
            except Student.DoesNotExist:
                return initial_queryset.none()
        elif user.user_type == User.USER_TYPE_PARENT:
            try:
                student_ids = StudentParentAssociation.objects.filter(parent_user=user).values_list('student_id', flat=True)
                if not student_ids:
                    return initial_queryset.none()
                return initial_queryset.filter(**{self.related_field_lookup_student_id_in: list(student_ids)})
            except Exception:
                return initial_queryset.none()
        else:
            if user.is_staff or user.is_superuser:
                return initial_queryset
            return initial_queryset.none()


class MyGradesViewSet(BaseMyStudentDataViewSet):
    serializer_class = GradeSerializer
    related_field_lookup_student = 'enrollment__student'
    related_field_lookup_student_id_in = 'enrollment__student_id__in'
    def get_queryset(self):
        initial_queryset = Grade.objects.select_related(
            'enrollment__student__user', 'subject', 'grading_period', 'grading_period__school_year'
        ).all()
        return self._filter_queryset_by_user_role(initial_queryset)


class MyAttendanceViewSet(BaseMyStudentDataViewSet):
    serializer_class = AttendanceSerializer
    related_field_lookup_student = 'enrollment__student'
    related_field_lookup_student_id_in = 'enrollment__student_id__in'
    def get_queryset(self):
        initial_queryset = Attendance.objects.select_related(
            'enrollment__student__user', 'subject', 'enrollment__school_class'
        ).all()
        return self._filter_queryset_by_user_role(initial_queryset)


class MySchoolEventsViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = SchoolEventSerializer
    permission_classes = [IsAuthenticated]
    def get_queryset(self):
        user = self.request.user
        base_queryset = SchoolEvent.objects.select_related('created_by').prefetch_related(
            'target_school_classes', 'target_grade_levels'
        ).order_by('start_time')
        if user.is_staff or user.is_superuser:
            return base_queryset
        student_active_enrollments = Enrollment.objects.filter(status=Enrollment.STATUS_ACTIVE).select_related('school_class__grade_level', 'student__user')
        if user.user_type == User.USER_TYPE_STUDENT:
            try:
                current_enrollment = student_active_enrollments.filter(student__user=user).order_by('-enrollment_date').first()
                if not current_enrollment: return base_queryset.none()
                student_school_class = current_enrollment.school_class
                student_grade_level = student_school_class.grade_level
                filter_conditions = Q(is_school_wide=True) | Q(target_grade_levels=student_grade_level) | Q(target_school_classes=student_school_class)
                return base_queryset.filter(filter_conditions).distinct()
            except Student.DoesNotExist: return base_queryset.none()
        elif user.user_type == User.USER_TYPE_PARENT:
            associated_students_ids = StudentParentAssociation.objects.filter(parent_user=user).values_list('student_id', flat=True)
            if not associated_students_ids: return base_queryset.none()
            children_enrollments = student_active_enrollments.filter(student_id__in=list(associated_students_ids))
            children_school_classes, children_grade_levels = set(), set()
            for enrollment in children_enrollments:
                children_school_classes.add(enrollment.school_class)
                children_grade_levels.add(enrollment.school_class.grade_level)
            if not children_school_classes and not children_grade_levels: return base_queryset.filter(is_school_wide=True).distinct()
            filter_conditions = Q(is_school_wide=True)
            if children_grade_levels: filter_conditions |= Q(target_grade_levels__in=list(children_grade_levels))
            if children_school_classes: filter_conditions |= Q(target_school_classes__in=list(children_school_classes))
            return base_queryset.filter(filter_conditions).distinct()
        return base_queryset.none()


class MyDidacticMaterialsViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = DidacticMaterialSerializer
    permission_classes = [IsAuthenticated]
    def get_queryset(self):
        user = self.request.user
        base_queryset = DidacticMaterial.objects.select_related('subject', 'school_class', 'uploader', 'uploader__profile').order_by('-upload_date')
        if user.is_staff or user.is_superuser: return base_queryset
        student_active_enrollments = Enrollment.objects.filter(status=Enrollment.STATUS_ACTIVE).select_related('school_class', 'student__user')
        if user.user_type == User.USER_TYPE_STUDENT:
            try:
                current_enrollment = student_active_enrollments.filter(student__user=user).order_by('-enrollment_date').first()
                if not current_enrollment: return base_queryset.none()
                student_school_class = current_enrollment.school_class
                filter_conditions = Q(school_class=student_school_class) | Q(school_class=None)
                return base_queryset.filter(filter_conditions).distinct()
            except Student.DoesNotExist: return base_queryset.none()
        elif user.user_type == User.USER_TYPE_PARENT:
            associated_students_ids = StudentParentAssociation.objects.filter(parent_user=user).values_list('student_id', flat=True)
            if not associated_students_ids: return base_queryset.none()
            children_enrollments = student_active_enrollments.filter(student_id__in=list(associated_students_ids))
            children_school_classes_pks = [enroll.school_class_id for enroll in children_enrollments if enroll.school_class_id]
            if not children_school_classes_pks: return base_queryset.filter(school_class=None).distinct()
            filter_conditions = Q(school_class_id__in=children_school_classes_pks) | Q(school_class=None)
            return base_queryset.filter(filter_conditions).distinct()
        elif user.user_type == User.USER_TYPE_TEACHER:
            # Professores veem materiais que eles enviaram OU materiais das turmas/disciplinas que lecionam (se school_class for None)
            teacher_assignments = TeacherAssignment.objects.filter(teacher=user)
            assigned_school_classes = teacher_assignments.values_list('school_class_id', flat=True)
            assigned_subjects = teacher_assignments.values_list('subject_id', flat=True)

            filter_conditions = Q(uploader=user) | \
                                (Q(school_class_id__in=list(assigned_school_classes)) & Q(subject_id__in=list(assigned_subjects))) | \
                                (Q(school_class=None) & Q(subject_id__in=list(assigned_subjects)))
            return base_queryset.filter(filter_conditions).distinct()
        return base_queryset.none()


class MyTeacherAssignmentsViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = TeacherAssignmentSerializer
    permission_classes = [IsAuthenticated, IsTeacher]
    def get_queryset(self):
        user = self.request.user
        return TeacherAssignment.objects.filter(teacher=user).select_related(
            'school_class__grade_level', 'school_class__school_year', 'subject', 'school_year'
        ).order_by('school_year__year', 'school_class__name', 'subject__name')

    @action(detail=True, methods=['get'], url_path='students-for-grading')
    def students_for_grading(self, request, pk=None):
        teacher_assignment = self.get_object()
        grading_period_id = request.query_params.get('grading_period_id')
        if not grading_period_id:
            return Response({"error": "O parâmetro 'grading_period_id' é obrigatório."}, status=status.HTTP_400_BAD_REQUEST)
        try:
            grading_period = GradingPeriod.objects.get(pk=grading_period_id)
        except (ValueError, GradingPeriod.DoesNotExist):
            return Response({"error": "GradingPeriod inválido ou não encontrado."}, status=status.HTTP_400_BAD_REQUEST)
        if teacher_assignment.school_year != grading_period.school_year:
            return Response({"error": "O período de avaliação não pertence ao ano letivo desta atribuição."}, status=status.HTTP_400_BAD_REQUEST)
        enrollments = Enrollment.objects.filter(
            school_class=teacher_assignment.school_class, status=Enrollment.STATUS_ACTIVE
        ).select_related('student__user').order_by('student__user__last_name', 'student__user__first_name')
        data_list = []
        for enrollment in enrollments:
            existing_grades = Grade.objects.filter(
                enrollment=enrollment, subject=teacher_assignment.subject, grading_period=grading_period
            ).order_by('assessment_name')
            data_list.append({'student': enrollment.student, 'grades': existing_grades})
        serializer = StudentGradeSheetSerializer(data_list, many=True, context={'request': request})
        return Response(serializer.data)


class TeacherGradeViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated, IsTeacher]
    def get_serializer_class(self):
        if self.action in ['list', 'retrieve']:
            return GradeSerializer
        return GradeWriteSerializer
    def get_queryset(self):
        user = self.request.user
        # Garante que o professor só acesse notas de suas TeacherAssignments
        teacher_assignments = TeacherAssignment.objects.filter(teacher=user)
        school_class_ids = teacher_assignments.values_list('school_class_id', flat=True)
        subject_ids = teacher_assignments.values_list('subject_id', flat=True)
        school_year_ids = teacher_assignments.values_list('school_year_id', flat=True)

        return Grade.objects.filter(
            enrollment__school_class_id__in=school_class_ids,
            subject_id__in=subject_ids,
            grading_period__school_year_id__in=school_year_ids,
            # Adicionalmente, garantir que a combinação específica de turma/disciplina/ano da nota
            # corresponde a uma atribuição do professor. Isso é mais complexo e _check_assignment_permission lida com isso.
            # Para listagem, podemos filtrar pelos componentes da atribuição.
        ).select_related(
            'enrollment__student__user', 'subject', 'grading_period', 'grading_period__school_year'
        ).distinct()


    def _check_assignment_permission(self, teacher, enrollment, subject, school_year_from_related_obj, object_name="grade"):
        if not enrollment or not subject or not school_year_from_related_obj:
            raise PermissionDenied(f"Enrollment, Subject, e SchoolYear (do GradingPeriod ou da data) são obrigatórios para a {object_name}.")
        school_class = enrollment.school_class
        has_assignment = TeacherAssignment.objects.filter(
            teacher=teacher, school_class=school_class, subject=subject, school_year=school_year_from_related_obj
        ).exists()
        if not has_assignment:
            raise PermissionDenied(f"Você não tem permissão para gerenciar {object_name}s para esta turma/disciplina/ano letivo.")
        if enrollment.status != Enrollment.STATUS_ACTIVE:
            raise PermissionDenied(f"Não é possível lançar {object_name}s para matrículas que não estão ativas.")

    def perform_create(self, serializer):
        enrollment = serializer.validated_data.get('enrollment')
        subject = serializer.validated_data.get('subject')
        grading_period = serializer.validated_data.get('grading_period')
        self._check_assignment_permission(self.request.user, enrollment, subject, grading_period.school_year if grading_period else None)
        serializer.save()

    def perform_update(self, serializer):
        grade_instance = serializer.instance
        self._check_assignment_permission(
            self.request.user, grade_instance.enrollment, grade_instance.subject, grade_instance.grading_period.school_year
        )
        serializer.save()

    def perform_destroy(self, instance):
        self._check_assignment_permission(
            self.request.user, instance.enrollment, instance.subject, instance.grading_period.school_year
        )
        instance.delete()


class TeacherAttendanceViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated, IsTeacher]
    def get_serializer_class(self):
        if self.action in ['list', 'retrieve']:
            return AttendanceSerializer
        return AttendanceWriteSerializer
    def get_queryset(self):
        user = self.request.user
        teacher_assignments = TeacherAssignment.objects.filter(teacher=user)
        school_class_ids = teacher_assignments.values_list('school_class_id', flat=True)
        subject_ids = teacher_assignments.values_list('subject_id', flat=True)
        # Adicional: filtrar por ano letivo se a data for usada para isso
        return Attendance.objects.filter(
            enrollment__school_class_id__in=school_class_ids,
            subject_id__in=subject_ids
        ).select_related(
            'enrollment__student__user', 'subject', 'enrollment__school_class__school_year'
        ).distinct()

    def _check_attendance_assignment_permission(self, teacher, enrollment, subject, attendance_date):
        if not enrollment or not subject or not attendance_date:
            raise PermissionDenied("Enrollment, Subject, e Date são obrigatórios para o registro de frequência.")
        school_class = enrollment.school_class
        relevant_school_year = SchoolYear.objects.filter(start_date__lte=attendance_date, end_date__gte=attendance_date).first()
        if not relevant_school_year:
            raise PermissionDenied("A data da frequência não corresponde a um ano letivo válido.")
        has_assignment = TeacherAssignment.objects.filter(
            teacher=teacher, school_class=school_class, subject=subject, school_year=relevant_school_year
        ).exists()
        if not has_assignment:
            raise PermissionDenied("Você não tem permissão para gerenciar frequência para esta turma/disciplina neste ano letivo/data.")
        if enrollment.status != Enrollment.STATUS_ACTIVE:
            raise PermissionDenied("Não é possível lançar frequência para matrículas que não estão ativas.")

    def perform_create(self, serializer):
        enrollment = serializer.validated_data.get('enrollment')
        subject = serializer.validated_data.get('subject')
        attendance_date = serializer.validated_data.get('date')
        self._check_attendance_assignment_permission(self.request.user, enrollment, subject, attendance_date)
        if Attendance.objects.filter(enrollment=enrollment, subject=subject, date=attendance_date).exists():
            raise drf_serializers.ValidationError("Um registro de frequência para este aluno, disciplina e data já existe.")
        serializer.save()

    def perform_update(self, serializer):
        attendance_instance = serializer.instance
        self._check_attendance_assignment_permission(
            self.request.user, attendance_instance.enrollment, attendance_instance.subject, attendance_instance.date
        )
        new_enrollment = serializer.validated_data.get('enrollment', attendance_instance.enrollment)
        new_subject = serializer.validated_data.get('subject', attendance_instance.subject)
        new_date = serializer.validated_data.get('date', attendance_instance.date)
        if (new_enrollment != attendance_instance.enrollment or
            new_subject != attendance_instance.subject or
            new_date != attendance_instance.date):
            self._check_attendance_assignment_permission(self.request.user, new_enrollment, new_subject, new_date)
        serializer.save()

    def perform_destroy(self, instance):
        self._check_attendance_assignment_permission(
            self.request.user, instance.enrollment, instance.subject, instance.date
        )
        instance.delete()


class TeacherSchoolEventViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated, IsTeacher]
    def get_serializer_class(self):
        if self.action in ['list', 'retrieve']:
            return SchoolEventSerializer
        return SchoolEventWriteSerializer
    def get_queryset(self):
        return SchoolEvent.objects.filter(created_by=self.request.user).order_by('-start_time')

    def _can_teacher_target(self, teacher, school_classes, grade_levels):
        if not school_classes and not grade_levels: return True
        teacher_assignments = TeacherAssignment.objects.filter(teacher=teacher)
        assigned_school_classes_ids = set(teacher_assignments.values_list('school_class_id', flat=True))
        assigned_grade_levels_ids = set(SchoolClass.objects.filter(id__in=assigned_school_classes_ids).values_list('grade_level_id', flat=True))
        for sc in school_classes:
            if sc.id not in assigned_school_classes_ids: return False
        for gl in grade_levels:
            if gl.id not in assigned_grade_levels_ids: return False
        return True

    def perform_create(self, serializer):
        is_school_wide = serializer.validated_data.get('is_school_wide', False)
        target_school_classes = serializer.validated_data.get('target_school_classes', [])
        target_grade_levels = serializer.validated_data.get('target_grade_levels', [])
        if not is_school_wide:
            if not self._can_teacher_target(self.request.user, target_school_classes, target_grade_levels):
                raise PermissionDenied("Você só pode criar eventos para turmas ou séries às quais você está atribuído.")
        serializer.save(created_by=self.request.user)

    def perform_update(self, serializer):
        is_school_wide = serializer.validated_data.get('is_school_wide', serializer.instance.is_school_wide)
        target_school_classes = serializer.validated_data.get('target_school_classes', list(serializer.instance.target_school_classes.all()))
        target_grade_levels = serializer.validated_data.get('target_grade_levels', list(serializer.instance.target_grade_levels.all()))
        if not is_school_wide:
            if not self._can_teacher_target(self.request.user, target_school_classes, target_grade_levels):
                raise PermissionDenied("Você só pode atualizar eventos para turmas ou séries às quais você está atribuído.")
        serializer.save()


class TeacherDidacticMaterialViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated, IsTeacher]
    parser_classes = (MultiPartParser, FormParser) # Para upload de arquivos

    def get_serializer_class(self):
        if self.action in ['list', 'retrieve']:
            return DidacticMaterialSerializer
        return DidacticMaterialWriteSerializer

    def get_queryset(self):
        return DidacticMaterial.objects.filter(uploader=self.request.user).order_by('-upload_date')

    def _check_material_assignment_permission(self, teacher, subject, school_class=None):
        """
        Verifica se o professor tem atribuição para a disciplina e, opcionalmente, para a turma.
        """
        query_params = {'teacher': teacher, 'subject': subject}
        if school_class:
            query_params['school_class'] = school_class

        # O professor precisa ter uma atribuição que corresponda ao ano letivo da turma (se especificada)
        # ou a qualquer ano letivo se for um material geral da disciplina.
        # Esta lógica pode precisar ser mais refinada dependendo de como os anos letivos são gerenciados.
        # Por ora, uma atribuição para a disciplina/turma em qualquer ano letivo é considerada.
        if school_class:
            query_params['school_year'] = school_class.school_year
            if not TeacherAssignment.objects.filter(**query_params).exists():
                raise PermissionDenied("Você não tem permissão para enviar material para esta turma/disciplina específica.")
        elif not TeacherAssignment.objects.filter(teacher=teacher, subject=subject).exists():
             # Se school_class não é fornecida, o professor deve pelo menos lecionar a disciplina.
            raise PermissionDenied("Você não tem permissão para enviar material para esta disciplina (geral).")


    def perform_create(self, serializer):
        subject = serializer.validated_data.get('subject')
        school_class = serializer.validated_data.get('school_class') # Pode ser None
        self._check_material_assignment_permission(self.request.user, subject, school_class)
        serializer.save(uploader=self.request.user)

    def perform_update(self, serializer):
        # get_queryset já garante que o professor só edita seus próprios materiais.
        # Validação adicional se subject ou school_class forem alterados.
        subject = serializer.validated_data.get('subject', serializer.instance.subject)
        school_class = serializer.validated_data.get('school_class', serializer.instance.school_class)
        self._check_material_assignment_permission(self.request.user, subject, school_class)
        serializer.save()

    # perform_destroy já está protegido pelo get_queryset.
