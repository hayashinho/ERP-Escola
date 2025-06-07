from django.db.models import Q
from django.shortcuts import get_object_or_404
from django.core.exceptions import PermissionDenied
from rest_framework import viewsets, status, serializers as drf_serializers
from rest_framework.permissions import IsAuthenticated, IsAdminUser
from django.utils import timezone # Added timezone import
from rest_framework.response import Response
from rest_framework.decorators import action
from rest_framework.parsers import MultiPartParser, FormParser # Importar parsers para upload

from apps.accounts.models import User # Reverted import
from apps.accounts.permissions import IsTeacher # Reverted import
from apps.students.models import Student, StudentParentAssociation # Reverted import
from apps.academics.models import (
    Grade, Attendance, SchoolEvent, Enrollment, DidacticMaterial, TeacherAssignment,
    GradingPeriod, Subject, SchoolClass, SchoolYear, Announcement # Added Announcement
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


from .serializers import EnrollmentSerializer # Import EnrollmentSerializer

class EnrollmentViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing Student Enrollments in SchoolClasses.
    Allows creation, update (status), listing, and retrieval.
    """
    queryset = Enrollment.objects.all().select_related(
        'student__user',
        'school_class__grade_level',
        'school_class__school_year'
    ).order_by('-enrollment_date')
    serializer_class = EnrollmentSerializer
    permission_classes = [IsAdminUser] # Or a more specific 'Secretaria' permission
    http_method_names = ['get', 'post', 'patch', 'delete', 'head', 'options'] # Allow DELETE if policy permits

    # Add filtering capabilities
    filterset_fields = {
        'student': ['exact'],
        'student__user__username': ['exact', 'icontains'],
        'school_class': ['exact'],
        'school_class__school_year': ['exact'],
        'school_class__school_year__year': ['exact', 'gte', 'lte'],
        'school_class__grade_level': ['exact'],
        'school_class__grade_level__name': ['exact', 'icontains'],
        'status': ['exact'],
        'enrollment_date': ['exact', 'gte', 'lte'],
    }

    # perform_create: Handled by EnrollmentSerializer's create and validation logic.
    # perform_update: Handled by EnrollmentSerializer's update and validation logic.
    # perform_destroy: Default behavior is fine unless specific logic is needed.
    # Ensure that if an enrollment is deleted, related objects like grades/attendance
    # are handled according to policy (CASCADE is default on models shown, which might be too aggressive).
    # Consider soft-delete or archival strategies in a real-world scenario.


from django.db import transaction
from apps.students.models import GradeLevel # Reverted import: Ensure GradeLevel from students.models is imported
from .serializers import SchoolYearSerializer, BatchReenrollSerializer # Import necessary serializers

class SchoolYearViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing SchoolYears.
    Includes a custom action for batch re-enrollment of students.
    """
    queryset = SchoolYear.objects.all().order_by('-year')
    serializer_class = SchoolYearSerializer
    permission_classes = [IsAdminUser] # Secretaria or Admin

    @action(detail=True, methods=['post'], url_path='batch-reenroll')
    def batch_reenroll(self, request, pk=None):
        source_school_year = self.get_object()

        # Validate request data
        serializer = BatchReenrollSerializer(
            data=request.data,
            context={'source_school_year_id': source_school_year.pk}
        )
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        target_school_year_id = serializer.validated_data['target_school_year_id']
        try:
            target_school_year = SchoolYear.objects.get(pk=target_school_year_id)
        except SchoolYear.DoesNotExist:
            # Should be caught by serializer, but good practice
            return Response({'error': 'Target school year not found.'}, status=status.HTTP_404_NOT_FOUND)

        # Counters for summary
        processed_count = 0
        reenrolled_count = 0
        skipped_graduating = 0
        skipped_no_next_grade = 0
        skipped_no_class_found = 0
        skipped_already_enrolled = 0
        errors = []

        # Fetch relevant enrollments from the source year
        source_enrollments = Enrollment.objects.filter(
            school_class__school_year=source_school_year,
            status__in=[Enrollment.STATUS_ACTIVE, Enrollment.STATUS_COMPLETED]
        ).select_related('student', 'student__user', 'school_class__grade_level')

        with transaction.atomic():
            for src_enrollment in source_enrollments:
                processed_count += 1
                student = src_enrollment.student
                current_grade = src_enrollment.school_class.grade_level

                # Update old enrollment status first, if it was active
                original_src_enrollment_status = src_enrollment.status
                if original_src_enrollment_status == Enrollment.STATUS_ACTIVE:
                    src_enrollment.status = Enrollment.STATUS_COMPLETED
                    src_enrollment.save(update_fields=['status'])

                # 1. Determine Next Grade Level
                if current_grade.order_in_sequence is None: # Should not happen for well-defined grades
                    skipped_no_next_grade +=1
                    errors.append(f"Student {student.user.username}: Current grade '{current_grade.name}' has no order_in_sequence.")
                    continue

                try:
                    next_grade_level = GradeLevel.objects.get(order_in_sequence=current_grade.order_in_sequence + 1)
                except GradeLevel.DoesNotExist:
                    skipped_graduating += 1
                    # Optionally, update student status to GRADUATED if that's a policy
                    # student.registration_status = Student.STATUS_GRADUATED
                    # student.save(update_fields=['registration_status'])
                    errors.append(f"Student {student.user.username}: Graduating or no next grade level found after '{current_grade.name}'.")
                    continue

                # 2. Check if student is already enrolled in the target year (any active enrollment)
                if Enrollment.objects.filter(
                    student=student,
                    school_class__school_year=target_school_year,
                    status=Enrollment.STATUS_ACTIVE).exists():
                    skipped_already_enrolled +=1
                    errors.append(f"Student {student.user.username}: Already actively enrolled in target year {target_school_year.year}.")
                    continue

                # 3. Find or Create SchoolClass in Target Year for Next Grade
                # For V1, we'll try to find one. If multiple, pick first. If none, skip.
                target_school_class = SchoolClass.objects.filter(
                    school_year=target_school_year,
                    grade_level=next_grade_level
                ).order_by('name').first() # Simplistic: pick the first one

                if not target_school_class:
                    skipped_no_class_found += 1
                    # Log or handle class creation if policy allows, e.g.:
                    # target_school_class = SchoolClass.objects.create(
                    #     name=f"Default {next_grade_level.name}",
                    #     school_year=target_school_year,
                    #     grade_level=next_grade_level
                    # )
                    # logger.info(f"Created class {target_school_class.name} for {target_school_year.year}")
                    errors.append(f"Student {student.user.username}: No class found for grade '{next_grade_level.name}' in target year {target_school_year.year}.")
                    continue

                # 4. Create New Enrollment
                try:
                    Enrollment.objects.create(
                        student=student,
                        school_class=target_school_class,
                        status=Enrollment.STATUS_ACTIVE
                        # enrollment_date will be auto_now_add
                    )
                    reenrolled_count += 1
                except Exception as e: # Catch potential unique_together or other db errors
                    errors.append(f"Student {student.user.username}: Error creating new enrollment - {str(e)}.")
                    continue

                # Old enrollment status already updated at the beginning of the loop if it was active.

        summary = {
            'processed_enrollments': processed_count,
            'successfully_reenrolled': reenrolled_count,
            'skipped_graduating_or_no_next_grade': skipped_graduating + skipped_no_next_grade,
            'skipped_no_class_found_in_target_year': skipped_no_class_found,
            'skipped_already_enrolled_in_target_year': skipped_already_enrolled,
            'detailed_errors_or_info': errors if errors else "No specific errors."
        }
        return Response(summary, status=status.HTTP_200_OK)


from .serializers import AnnouncementSerializer # Import AnnouncementSerializer
from django_filters import rest_framework as filters # For filtering

# Custom filter for JSONField array containment (if needed)
# class CharArrayFilterInFilter(filters.BaseInFilter, filters.CharFilter):
#     pass

class AnnouncementFilter(filters.FilterSet):
    # publication_date_after = filters.DateTimeFilter(field_name="publication_date", lookup_expr='gte')
    # publication_date_before = filters.DateTimeFilter(field_name="publication_date", lookup_expr='lte')
    # Example for target_user_types if it were a simple CharField or text search:
    # target_user_types_contain = filters.CharFilter(field_name='target_user_types', lookup_expr='icontains')

    # For JSONField, direct __contains or __icontains might not work as expected for array elements.
    # A custom filter method might be needed if complex JSON queries are required.
    # For simple equality or if the DB supports it:
    # target_user_types = filters.CharFilter(field_name='target_user_types', lookup_expr='contains') # Adjust based on DB & needs

    class Meta:
        model = Announcement
        fields = {
            'author': ['exact'],
            'is_school_wide': ['exact'],
            'target_grade_levels': ['exact'], # Filters if announcement is targeted to specific grade(s)
            'target_school_classes': ['exact'], # Filters if announcement is targeted to specific class(es)
            'publication_date': ['date__gte', 'date__lte'], # Date part gte/lte
            'expiry_date': ['date__gte', 'date__lte', 'isnull'],
            # 'target_user_types': ['contains'] # if your DB supports JSONField contains for lists
        }

class AnnouncementViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing Announcements.
    """
    queryset = Announcement.objects.all().select_related('author').prefetch_related(
        'target_grade_levels', 'target_school_classes'
    ).order_by('-publication_date')
    serializer_class = AnnouncementSerializer
    permission_classes = [IsAdminUser] # Adjust as needed (e.g. Secretaria, Teacher for specific actions)
    filter_backends = (filters.DjangoFilterBackend,)
    filterset_class = AnnouncementFilter
    # For more complex JSONField filtering on target_user_types,
    # you might need to override get_queryset or use a custom filter class.

    def perform_create(self, serializer):
        serializer.save(author=self.request.user)

    # Optional: Add custom logic for updates or deletions if needed
    # def perform_update(self, serializer):
    #     super().perform_update(serializer)

    # def perform_destroy(self, instance):
    #     super().perform_destroy(instance)

    # Example: Custom action to publish/unpublish or similar
    # @action(detail=True, methods=['post'])
    # def set_published_status(self, request, pk=None):
    #     announcement = self.get_object()
    #     # ... logic to change a status field if you add one ...
    #     return Response({'status': 'status changed'})


from rest_framework.views import APIView
from django.db.models import Count
from apps.students.models import Student # Reverted import: Import Student model
from apps.academics.models import GradeLevel # GradeLevel from academics is used for M2M in Announcement, but student grade is from students.models

class DashboardSummaryView(APIView):
    """
    Provides a summary of key indicators for an administrative dashboard.
    """
    permission_classes = [IsAdminUser]

    def get(self, request, *args, **kwargs):
        # Total active students
        total_active_students = Student.objects.filter(registration_status=Student.STATUS_ACTIVE).count()

        # Active students by grade level (based on active enrollments)
        # This counts distinct students per grade level if a student has multiple active enrollments in different classes of the same grade.
        # If a student can only be in one grade level at a time via active enrollments, this is fine.
        active_students_by_grade_level_query = Enrollment.objects.filter(
            status=Enrollment.STATUS_ACTIVE
        ).values(
            'school_class__grade_level__name' # Use name from related GradeLevel (from students.models via SchoolClass)
        ).annotate(
            count=Count('student_id', distinct=True) # Count distinct students
        ).order_by('school_class__grade_level__order_in_sequence')

        active_students_by_grade_level_data = [
            {'grade_level_name': item['school_class__grade_level__name'], 'count': item['count']}
            for item in active_students_by_grade_level_query if item['school_class__grade_level__name'] is not None
        ]

        # Other student counts by registration status
        total_preregistered_students = Student.objects.filter(registration_status=Student.STATUS_PRE_REGISTERED).count()
        total_pending_validation_students = Student.objects.filter(registration_status=Student.STATUS_PENDING_VALIDATION).count()

        # Total active enrollments
        total_active_enrollments = Enrollment.objects.filter(status=Enrollment.STATUS_ACTIVE).count()

        # Active school years
        active_school_years_count = SchoolYear.objects.filter(is_active=True).count()

        data = {
            'total_active_students': total_active_students,
            'active_students_by_grade_level': active_students_by_grade_level_data,
            'total_preregistered_students': total_preregistered_students,
            'total_pending_validation_students': total_pending_validation_students,
            'total_active_enrollments': total_active_enrollments,
            'active_school_years': active_school_years_count,
        }
        return Response(data, status=status.HTTP_200_OK)


from rest_framework_csv.renderers import CSVRenderer
from rest_framework import generics
# from django.utils import timezone # Already imported if needed for filename
from .serializers import EnrollmentReportSerializer

class EnrollmentListCSVExportView(generics.ListAPIView):
    """
    API View to export a list of enrollments to a CSV file.
    Supports filtering by school_year_id, grade_level_id, school_class_id, status, and student_id.
    """
    renderer_classes = (CSVRenderer,)
    serializer_class = EnrollmentReportSerializer
    permission_classes = [IsAdminUser]

    def get_queryset(self):
        queryset = Enrollment.objects.select_related(
            'student__user',
            'school_class__grade_level',
            'school_class__school_year'
        ).all()

        # Filtering
        school_year_id = self.request.query_params.get('school_year_id')
        if school_year_id:
            queryset = queryset.filter(school_class__school_year_id=school_year_id)

        grade_level_id = self.request.query_params.get('grade_level_id')
        if grade_level_id:
            queryset = queryset.filter(school_class__grade_level_id=grade_level_id)

        school_class_id = self.request.query_params.get('school_class_id')
        if school_class_id:
            queryset = queryset.filter(school_class_id=school_class_id)

        status = self.request.query_params.get('status')
        if status:
            queryset = queryset.filter(status=status)

        student_id = self.request.query_params.get('student_id')
        if student_id:
            queryset = queryset.filter(student_id=student_id)

        return queryset.order_by('school_class__school_year__year', 'school_class__grade_level__order_in_sequence', 'school_class__name', 'student__user__last_name', 'student__user__first_name')

    def get_filename(self, request=None, format=None):
        timestamp = timezone.now().strftime('%Y%m%d_%H%M%S')
        return f'enrollment_list_report_{timestamp}.csv'

    def list(self, request, *args, **kwargs):
        response = super().list(request, *args, **kwargs)
        response['Content-Disposition'] = f'attachment; filename="{self.get_filename()}"'
        return response
