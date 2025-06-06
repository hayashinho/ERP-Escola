from rest_framework import serializers
from apps.academics.models import (
    SchoolYear, Subject, SchoolClass, Enrollment,
    GradingPeriod, Grade, Attendance, SchoolEvent, DidacticMaterial,
    TeacherAssignment, Announcement # Import Announcement model
)
from apps.students.models import GradeLevel, Student # Import Student
from apps.students.serializers import GradeLevelSerializer, StudentSimpleSerializer
from apps.accounts.serializers import UserSerializer
from django.utils.translation import gettext_lazy as _
from django.core.exceptions import ValidationError as DjangoValidationError
from django.utils import timezone # Import timezone


# 1. SchoolYearSerializer
class SchoolYearSerializer(serializers.ModelSerializer):
    class Meta:
        model = SchoolYear
        fields = '__all__'

# 2. SubjectSerializer
class SubjectSerializer(serializers.ModelSerializer):
    class Meta:
        model = Subject
        fields = '__all__'

# 3. SchoolClassListSerializer (Para listas)
class SchoolClassListSerializer(serializers.ModelSerializer):
    grade_level_name = serializers.CharField(source='grade_level.name', read_only=True)
    school_year_str = serializers.CharField(source='school_year.__str__', read_only=True)
    main_teacher_name = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = SchoolClass
        fields = ('id', 'name', 'grade_level_name', 'school_year_str', 'main_teacher_name')

    def get_main_teacher_name(self, obj):
        if obj.main_teacher:
            return obj.main_teacher.get_full_name() or obj.main_teacher.username
        return None

# 4. GradeLevelSerializer (já importado de apps.students.serializers)

# 5. UserSerializer (já importado de apps.accounts.serializers)

# 6. SchoolClassDetailSerializer
class SchoolClassDetailSerializer(serializers.ModelSerializer):
    school_year = SchoolYearSerializer(read_only=True)
    grade_level = GradeLevelSerializer(read_only=True)
    main_teacher = UserSerializer(read_only=True)

    class Meta:
        model = SchoolClass
        fields = ('id', 'name', 'school_year', 'grade_level', 'main_teacher')

# 7. EnrollmentSerializer
# Using StudentSimpleSerializer for student representation on read
# Using SchoolClassListSerializer for school_class representation on read
class EnrollmentSerializer(serializers.ModelSerializer):
    student_details = StudentSimpleSerializer(source='student', read_only=True)
    school_class_details = SchoolClassListSerializer(source='school_class', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)

    # student and school_class are PrimaryKeyRelatedField for write operations
    student = serializers.PrimaryKeyRelatedField(
        queryset=Student.objects.all(), write_only=True
    )
    school_class = serializers.PrimaryKeyRelatedField(
        queryset=SchoolClass.objects.all(), write_only=True
    )

    class Meta:
        model = Enrollment
        fields = (
            'id',
            'student', # Write-only
            'student_details', # Read-only
            'school_class', # Write-only
            'school_class_details', # Read-only
            'enrollment_date',
            'status',
            'status_display'
        )
        read_only_fields = ('enrollment_date', 'status_display')
        # 'status' is defaulted by model, but updatable.

    def validate_student(self, student_instance):
        """
        Validate that the student's registration_status is ACTIVE.
        """
        if student_instance.registration_status != Student.RegistrationStatus.ACTIVE:
            raise serializers.ValidationError(
                _("Student's registration status must be ACTIVE to create an enrollment. Current status: %(status)s.") %
                {'status': student_instance.get_registration_status_display()}
            )
        return student_instance

    def validate_school_class(self, school_class_instance):
        """
        Validate that the SchoolClass belongs to an active SchoolYear.
        """
        if not school_class_instance.school_year.is_active:
            raise serializers.ValidationError(
                _("Enrollments can only be made into classes of an active school year. School year %(year)s is not active.") %
                {'year': school_class_instance.school_year.year}
            )
        return school_class_instance

    def validate(self, data):
        """
        Validate against duplicate active enrollments for the same student in the same school year.
        The unique_together on model handles ('student', 'school_class').
        This adds a check for student in ANY active class within the same school year.
        """
        student = data.get('student')
        school_class = data.get('school_class')

        # This validation is only relevant during creation (POST)
        # For PATCH, student and school_class are not part of `data` if made read-only for update
        if self.instance is None and student and school_class: # self.instance is None for POST
            # Check if student is already actively enrolled in another class in the same school year
            # (and same grade level, if that's a policy - for now, just school year)
            existing_active_enrollments = Enrollment.objects.filter(
                student=student,
                school_class__school_year=school_class.school_year,
                status=Enrollment.STATUS_ACTIVE
            ).exclude(school_class=school_class) # Exclude if somehow it's the same class (unique_together should catch)

            if existing_active_enrollments.exists():
                # Example: Check if the student is in a class of the same grade level
                # current_grade = school_class.grade_level
                # if existing_active_enrollments.filter(school_class__grade_level=current_grade).exists():
                raise serializers.ValidationError(
                    _("This student is already actively enrolled in another class for the school year %(year)s.") %
                    {'year': school_class.school_year.year}
                )

        # For updates (PATCH), ensure student and school_class are not being changed
        if self.instance is not None: # self.instance exists for PUT/PATCH
            if 'student' in data and data['student'] != self.instance.student:
                raise serializers.ValidationError({"student": _("Cannot change the student after enrollment creation.")})
            if 'school_class' in data and data['school_class'] != self.instance.school_class:
                raise serializers.ValidationError({"school_class": _("Cannot change the school class after enrollment creation.")})

        return data


# 20. AnnouncementSerializer
class AnnouncementSerializer(serializers.ModelSerializer):
    author_details = UserSerializer(source='author', read_only=True)

    # For writing, expect PKs
    target_grade_levels = serializers.PrimaryKeyRelatedField(
        queryset=GradeLevel.objects.all(),
        many=True,
        required=False,
        allow_empty=True
    )
    target_school_classes = serializers.PrimaryKeyRelatedField(
        queryset=SchoolClass.objects.all(),
        many=True,
        required=False,
        allow_empty=True
    )

    # For reading, show more details (optional, can be simplified if needed)
    target_grade_levels_details = GradeLevelSerializer(source='target_grade_levels', many=True, read_only=True)
    target_school_classes_details = SchoolClassListSerializer(source='target_school_classes', many=True, read_only=True)


    class Meta:
        model = Announcement
        fields = (
            'id', 'title', 'content', 'publication_date', 'author', 'author_details',
            'target_user_types', 'target_grade_levels', 'target_grade_levels_details',
            'target_school_classes', 'target_school_classes_details',
            'is_school_wide', 'expiry_date'
        )
        read_only_fields = ('author', 'publication_date', 'author_details',
                            'target_grade_levels_details', 'target_school_classes_details')

    def validate_target_user_types(self, value):
        if value is None: # Allow null
            return value
        if not isinstance(value, list):
            raise serializers.ValidationError(_("target_user_types must be a list."))

        valid_user_types = [choice[0] for choice in User.USER_TYPE_CHOICES]
        for item in value:
            if item not in valid_user_types:
                raise serializers.ValidationError(
                    _("Invalid user type '%(user_type)s'. Valid choices are: %(valid_choices)s") %
                    {'user_type': item, 'valid_choices': ", ".join(valid_user_types)}
                )
        return value

    def validate(self, data):
        is_school_wide = data.get('is_school_wide', False)
        target_user_types = data.get('target_user_types')
        target_grade_levels = data.get('target_grade_levels')
        target_school_classes = data.get('target_school_classes')

        if not is_school_wide and not target_user_types and not target_grade_levels and not target_school_classes:
            raise serializers.ValidationError(
                _("If the announcement is not school-wide, at least one targeting option (user types, grade levels, or school classes) must be specified.")
            )

        if data.get('expiry_date') and data['expiry_date'] < timezone.now():
             raise serializers.ValidationError(_("Expiry date cannot be in the past."))

        return data

    def create(self, validated_data):
        # Status defaults to ACTIVE via model's field definition.
        # No need to explicitly set it here unless overriding.
        enrollment = Enrollment.objects.create(**validated_data)
        return enrollment

    def update(self, instance, validated_data):
        # Only allow 'status' to be updated via this serializer for PATCH.
        # Student and SchoolClass changes are blocked by the validate method.
        instance.status = validated_data.get('status', instance.status)
        instance.save(update_fields=['status'])
        return instance


# 8. GradingPeriodSerializer
class GradingPeriodSerializer(serializers.ModelSerializer):
    school_year_str = serializers.CharField(source='school_year.__str__', read_only=True)
    class Meta:
        model = GradingPeriod
        fields = ('id', 'name', 'school_year', 'school_year_str', 'start_date', 'end_date')


# 9. GradeSerializer (Read-focused)
class GradeSerializer(serializers.ModelSerializer):
    subject_name = serializers.CharField(source='subject.name', read_only=True)
    grading_period_name = serializers.CharField(source='grading_period.name', read_only=True)
    student_name = serializers.CharField(source='enrollment.student.user.get_full_name', read_only=True)

    class Meta:
        model = Grade
        fields = (
            'id',
            'enrollment',
            'student_name',
            'subject',
            'subject_name',
            'grading_period',
            'grading_period_name',
            'assessment_name',
            'grade_value',
            'weight',
            'grading_date'
        )
        read_only_fields = ('grading_date',)


# 10. AttendanceSerializer (Read-focused)
class AttendanceSerializer(serializers.ModelSerializer):
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    student_name = serializers.CharField(source='enrollment.student.user.get_full_name', read_only=True)
    subject_name = serializers.CharField(source='subject.name', read_only=True)

    class Meta:
        model = Attendance
        fields = (
            'id',
            'enrollment',
            'student_name',
            'subject',
            'subject_name',
            'date',
            'status',
            'status_display',
            'notes'
        )

# 11. SchoolEventSerializer (Read-focused)
class SchoolEventSerializer(serializers.ModelSerializer):
    target_school_classes_display = serializers.StringRelatedField(many=True, source='target_school_classes', read_only=True)
    target_grade_levels_display = serializers.StringRelatedField(many=True, source='target_grade_levels', read_only=True)
    created_by_name = serializers.SerializerMethodField(read_only=True)
    event_type_display = serializers.CharField(source='get_event_type_display', read_only=True)

    class Meta:
        model = SchoolEvent
        fields = (
            'id', 'title', 'description', 'start_time', 'end_time',
            'event_type', 'event_type_display',
            'target_school_classes',
            'target_school_classes_display',
            'target_grade_levels',
            'target_grade_levels_display',
            'is_school_wide',
            'created_by',
            'created_by_name'
        )

    def get_created_by_name(self, obj):
        if obj.created_by:
            return obj.created_by.get_full_name() or obj.created_by.username
        return None

# 12. DidacticMaterialSerializer (Read-focused)
class DidacticMaterialSerializer(serializers.ModelSerializer):
    file_url = serializers.SerializerMethodField(read_only=True)
    subject_name = serializers.CharField(source='subject.name', read_only=True)
    school_class_name = serializers.CharField(source='school_class.__str__', read_only=True, allow_null=True)
    uploader_info = UserSerializer(source='uploader', read_only=True)

    class Meta:
        model = DidacticMaterial
        fields = (
            'id', 'title', 'description', 'file', 'file_url',
            'subject', 'subject_name',
            'school_class', 'school_class_name',
            'uploader',
            'uploader_info',
            'upload_date'
        )
        read_only_fields = ('upload_date', 'file_url')

    def get_file_url(self, obj):
        request = self.context.get('request')
        if obj.file and hasattr(obj.file, 'url') and request:
            return request.build_absolute_uri(obj.file.url)
        return None

# 13. TeacherAssignmentSerializer
class TeacherAssignmentSerializer(serializers.ModelSerializer):
    teacher_info = UserSerializer(source='teacher', read_only=True)
    school_class_info = SchoolClassListSerializer(source='school_class', read_only=True)
    subject_info = SubjectSerializer(source='subject', read_only=True)
    school_year_info = SchoolYearSerializer(source='school_year', read_only=True)

    class Meta:
        model = TeacherAssignment
        fields = (
            'id',
            'teacher',
            'teacher_info',
            'school_class',
            'school_class_info',
            'subject',
            'subject_info',
            'school_year',
            'school_year_info',
        )

# 14. StudentGradeSheetSerializer
class StudentGradeSheetSerializer(serializers.Serializer):
    student = StudentSimpleSerializer(read_only=True)
    grades = GradeSerializer(many=True, read_only=True)
    new_grade_assessment_name = serializers.CharField(write_only=True, required=False, allow_blank=True, max_length=100)
    new_grade_value = serializers.DecimalField(write_only=True, required=False, max_digits=5, decimal_places=2, coerce_to_string=False)
    new_grade_weight = serializers.DecimalField(write_only=True, required=False, max_digits=3, decimal_places=2, coerce_to_string=False, allow_null=True)

    def validate(self, data):
        has_assessment_name = 'new_grade_assessment_name' in data and data['new_grade_assessment_name']
        has_grade_value = 'new_grade_value' in data and data['new_grade_value'] is not None
        if has_assessment_name != has_grade_value:
            raise serializers.ValidationError(
                _("To add a new grade, 'new_grade_assessment_name' and 'new_grade_value' must be provided together.")
            )
        return data

# 15. GradeWriteSerializer
class GradeWriteSerializer(serializers.ModelSerializer):
    class Meta:
        model = Grade
        fields = (
            'enrollment',
            'subject',
            'grading_period',
            'assessment_name',
            'grade_value',
            'weight',
        )
    def validate_enrollment(self, value):
        if value.status != Enrollment.STATUS_ACTIVE:
            raise serializers.ValidationError(
                _("Grades can only be assigned to active enrollments.")
            )
        return value
    def validate(self, data):
        return data

# 16. AttendanceWriteSerializer
class AttendanceWriteSerializer(serializers.ModelSerializer):
    class Meta:
        model = Attendance
        fields = (
            'enrollment',
            'subject',
            'date',
            'status',
            'notes',
        )
    def validate_enrollment(self, value):
        if value.status != Enrollment.STATUS_ACTIVE:
            raise serializers.ValidationError(
                _("Attendance can only be recorded for active enrollments.")
            )
        return value
    def validate_date(self, value):
        return value
    def validate(self, data):
        enrollment = data.get('enrollment')
        date = data.get('date')
        if enrollment and date:
            school_year = enrollment.school_class.school_year
            if not (school_year.start_date <= date <= school_year.end_date):
                raise serializers.ValidationError(
                    _("Attendance date must be within the school year of the enrollment's class (%(start_date)s - %(end_date)s).") %
                    {'start_date': school_year.start_date, 'end_date': school_year.end_date}
                )
        return data

# 17. SchoolEventWriteSerializer
class SchoolEventWriteSerializer(serializers.ModelSerializer):
    target_school_classes = serializers.PrimaryKeyRelatedField(
        queryset=SchoolClass.objects.all(),
        many=True,
        required=False,
        allow_empty=True
    )
    target_grade_levels = serializers.PrimaryKeyRelatedField(
        queryset=GradeLevel.objects.all(),
        many=True,
        required=False,
        allow_empty=True
    )
    class Meta:
        model = SchoolEvent
        fields = (
            'title',
            'description',
            'start_time',
            'end_time',
            'event_type',
            'target_school_classes',
            'target_grade_levels',
            'is_school_wide'
        )
    def validate(self, data):
        if 'start_time' in data and 'end_time' in data:
            if data['end_time'] <= data['start_time']:
                raise serializers.ValidationError(_("End time must occur after start time."))
        is_school_wide = data.get('is_school_wide', False)
        target_classes = data.get('target_school_classes')
        target_grades = data.get('target_grade_levels')
        if not is_school_wide and not target_classes and not target_grades:
            raise serializers.ValidationError(
                _("If the event is not school-wide, please specify target school classes or grade levels.")
            )
        return data

# 18. DidacticMaterialWriteSerializer (Novo)
class DidacticMaterialWriteSerializer(serializers.ModelSerializer):
    """
    Serializer para criação e atualização de Materiais Didáticos (DidacticMaterial).
    """
    # school_class é opcional
    school_class = serializers.PrimaryKeyRelatedField(
        queryset=SchoolClass.objects.all(),
        required=False,
        allow_null=True
    )
    # subject é obrigatório
    subject = serializers.PrimaryKeyRelatedField(
        queryset=Subject.objects.all()
    )

    class Meta:
        model = DidacticMaterial
        fields = (
            'title',
            'description',
            'file', # FileField será tratado pelo DRF para upload
            'subject',
            'school_class',
            # 'uploader' será definido na view
        )
        # Não há validações complexas de data ou estado aqui,
        # mas a validação de permissão (se o professor pode postar para esta disciplina/turma)
        # será feita na view.


# 19. BatchReenrollSerializer
class BatchReenrollSerializer(serializers.Serializer):
    target_school_year_id = serializers.IntegerField()
    # source_school_year_id will come from the URL (viewset's pk)

    def validate_target_school_year_id(self, value):
        if not SchoolYear.objects.filter(pk=value).exists():
            raise serializers.ValidationError(_("Target school year not found."))

        target_year = SchoolYear.objects.get(pk=value)
        # Add any specific validation for the target year, e.g., must be active or future
        # For example, if it must not be in the past relative to current date:
        # if target_year.end_date < timezone.now().date():
        #     raise serializers.ValidationError(_("Target school year cannot be in the past."))

        # Check if target year is active (optional, depends on policy)
        # if not target_year.is_active:
        #    raise serializers.ValidationError(_("Target school year must be active."))
        return value

    def validate(self, data):
        source_school_year_id = self.context.get('source_school_year_id')
        target_school_year_id = data.get('target_school_year_id')

        if source_school_year_id is None:
            # This should ideally be caught earlier or ensured by view context
            raise serializers.ValidationError(_("Source school year ID must be provided in context."))

        if source_school_year_id == target_school_year_id:
            raise serializers.ValidationError(
                _("Target school year cannot be the same as the source school year.")
            )

        # Further validation: e.g., target year must be chronologically after source year
        try:
            source_year = SchoolYear.objects.get(pk=source_school_year_id)
            target_year = SchoolYear.objects.get(pk=target_school_year_id)
            if target_year.start_date <= source_year.end_date:
                 raise serializers.ValidationError(
                    _("Target school year must start after the source school year ends.")
                )
        except SchoolYear.DoesNotExist:
            # This should be caught by individual field validation, but good for robustness
            raise serializers.ValidationError(_("Invalid source or target school year ID."))

        return data


# 21. EnrollmentReportSerializer
class EnrollmentReportSerializer(serializers.ModelSerializer):
    enrollment_id = serializers.IntegerField(source='id', read_only=True)
    student_name = serializers.CharField(source='student.user.get_full_name', read_only=True)
    student_username = serializers.CharField(source='student.user.username', read_only=True)
    school_class_name = serializers.CharField(source='school_class.name', read_only=True)
    grade_level_name = serializers.CharField(source='school_class.grade_level.name', read_only=True)
    school_year = serializers.IntegerField(source='school_class.school_year.year', read_only=True)
    enrollment_status = serializers.CharField(source='get_status_display', read_only=True)
    # enrollment_date is directly from the model

    class Meta:
        model = Enrollment
        fields = (
            'enrollment_id',
            'student_name',
            'student_username',
            'school_class_name',
            'grade_level_name',
            'school_year',
            'enrollment_status',
            'enrollment_date',
        )
