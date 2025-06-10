from rest_framework import serializers
from apps.academics.models import (
    SchoolYear, Subject, SchoolClass, Enrollment,
    GradingPeriod, Grade, Attendance, SchoolEvent, DidacticMaterial,
    TeacherAssignment, Announcement # Import Announcement model
)
from apps.students.models import GradeLevel, Student # Reverted import
from apps.students.serializers import GradeLevelSerializer, StudentSimpleSerializer # Reverted import
from apps.accounts.serializers import UserSerializer # Reverted import
from apps.accounts.models import User # Import User model for choices
from django.utils.translation import gettext_lazy as _
from django.core.exceptions import ValidationError as DjangoValidationError
from django.utils import timezone # Import timezone


# 1. SchoolYearSerializer
class SchoolYearSerializer(serializers.ModelSerializer):
    """
    Serializer for the SchoolYear model.
    Represents an academic year with start and end dates.
    """
    year = serializers.IntegerField(help_text=_("The academic year (e.g., 2023, 2024)."))
    start_date = serializers.DateField(help_text=_("Start date of the school year."))
    end_date = serializers.DateField(help_text=_("End date of the school year."))
    is_active = serializers.BooleanField(help_text=_("Indicates if this is the currently active school year. Only one school year should be active at a time."))

    class Meta:
        model = SchoolYear
        fields = ('id', 'year', 'start_date', 'end_date', 'is_active')

# 2. SubjectSerializer
class SubjectSerializer(serializers.ModelSerializer):
    """
    Serializer for the Subject model.
    Represents an academic subject taught in the school.
    """
    name = serializers.CharField(max_length=100, help_text=_("Name of the subject (e.g., Mathematics, History)."))
    description = serializers.CharField(required=False, allow_blank=True, style={'base_template': 'textarea.html'}, help_text=_("Optional description of the subject."))

    class Meta:
        model = Subject
        fields = ('id', 'name', 'description')

# 3. SchoolClassListSerializer (Para listas)
class SchoolClassListSerializer(serializers.ModelSerializer):
    """
    A simplified serializer for listing SchoolClass instances.
    Provides key information for display in lists.
    """
    grade_level_name = serializers.CharField(source='grade_level.name', read_only=True, help_text=_("Name of the grade level for this class."))
    school_year_str = serializers.CharField(source='school_year.__str__', read_only=True, help_text=_("String representation of the school year (e.g., '2023-2024')."))
    main_teacher_name = serializers.SerializerMethodField(method_name='get_main_teacher_name_typed', read_only=True, help_text=_("Full name of the main teacher, if assigned.")) # Renamed method_name

    class Meta:
        model = SchoolClass
        fields = ('id', 'name', 'grade_level_name', 'school_year_str', 'main_teacher_name')

    def get_main_teacher_name_typed(self, obj: SchoolClass) -> str | None: # Renamed method and added type hint
        if obj.main_teacher:
            return obj.main_teacher.get_full_name() or obj.main_teacher.username
        return None

# 4. GradeLevelSerializer (já importado de apps.students.serializers)
# Ensure this import is correct and GradeLevelSerializer is well-defined in apps.students.serializers

# 5. UserSerializer (já importado de apps.accounts.serializers)
# Ensure this import is correct

# 6. SchoolClassDetailSerializer
class SchoolClassDetailSerializer(serializers.ModelSerializer):
    """
    Detailed serializer for a SchoolClass instance.
    Includes nested details for school year, grade level, and main teacher.
    """
    school_year = SchoolYearSerializer(read_only=True, help_text=_("Details of the school year for this class."))
    grade_level = GradeLevelSerializer(read_only=True, help_text=_("Details of the grade level for this class.")) # Assuming GradeLevelSerializer is from apps.students
    main_teacher = UserSerializer(read_only=True, help_text=_("Details of the main teacher assigned to this class, if any.")) # Assuming UserSerializer is from apps.accounts

    class Meta:
        model = SchoolClass
        fields = ('id', 'name', 'school_year', 'grade_level', 'main_teacher')

# 7. EnrollmentSerializer
class EnrollmentSerializer(serializers.ModelSerializer):
    """
    Serializer for student Enrollments.
    Handles creation of new enrollments and updating the status of existing ones.
    Student and School Class cannot be changed after an enrollment is created.
    """
    student_details = StudentSimpleSerializer(source='student', read_only=True, help_text=_("Basic details of the enrolled student."))
    school_class_details = SchoolClassListSerializer(source='school_class', read_only=True, help_text=_("Basic details of the class the student is enrolled in."))
    status_display = serializers.CharField(source='get_status_display', read_only=True, help_text=_("Display name for the enrollment status."))
    enrollment_date = serializers.DateField(read_only=True, help_text=_("Date the enrollment was recorded. Automatically set on creation if not provided, but generally read-only post-creation."))

    # student and school_class are PrimaryKeyRelatedField for write operations
    student = serializers.PrimaryKeyRelatedField(
        queryset=Student.objects.all(),
        write_only=True,
        help_text=_("ID of the student to be enrolled. Student must have an 'ACTIVE' registration status.")
    )
    school_class = serializers.PrimaryKeyRelatedField(
        queryset=SchoolClass.objects.select_related('school_year').all(), # Optimized queryset
        write_only=True,
        help_text=_("ID of the school class to enroll the student into. Class must belong to an active school year.")
    )
    status = serializers.ChoiceField(
        choices=Enrollment.STATUS_CHOICES,
        default=Enrollment.STATUS_ACTIVE,
        help_text=_("Status of the enrollment. Defaults to 'Active' upon creation. Can be updated to 'Completed', 'Transferred Out', or 'Dropped Out'.")
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
            'status', # Writeable (with choices and default)
            'status_display' # Read-only
        )
        # For updates, student and school_class are effectively read-only due to validation logic.
        # enrollment_date is also primarily system-set or set on creation.
        read_only_fields = ('status_display',) # Add 'enrollment_date' if strictly system-set post-creation

    def validate_student(self, student_instance: Student) -> Student:
        """
        Validate that the student's registration_status is ACTIVE.
        """
        if student_instance.registration_status != Student.RegistrationStatus.ACTIVE:
            raise serializers.ValidationError(
                _("Student's registration status must be ACTIVE to create an enrollment. Current status: %(status)s.") %
                {'status': student_instance.get_registration_status_display()}
            )
        return student_instance

    def validate_school_class(self, school_class_instance: SchoolClass) -> SchoolClass:
        """
        Validate that the SchoolClass belongs to an active SchoolYear.
        """
        if not school_class_instance.school_year.is_active:
            raise serializers.ValidationError(
                _("Enrollments can only be made into classes of an active school year. School year %(year)s is not active.") %
                {'year': school_class_instance.school_year.year}
            )
        return school_class_instance

    def validate(self, data: dict) -> dict:
        """
        Validate against duplicate active enrollments for the same student in the same school year.
        Also prevents changing student or school_class on update.
        """
        student = data.get('student')
        school_class = data.get('school_class')

        if self.instance is None: # Creating a new enrollment
            if student and school_class:
                # Check for existing active enrollment in the same school year
                existing_active_enrollment = Enrollment.objects.filter(
                    student=student,
                    school_class__school_year=school_class.school_year,
                    status=Enrollment.STATUS_ACTIVE
                ).exists()
                if existing_active_enrollment:
                    raise serializers.ValidationError(
                        _("This student is already actively enrolled in another class for the school year %(year)s.") %
                        {'year': school_class.school_year.year}
                    )
            # If enrollment_date is not provided, set it to today
            if 'enrollment_date' not in data:
                data['enrollment_date'] = timezone.now().date()

        else: # Updating an existing enrollment
            if 'student' in data and data['student'] != self.instance.student:
                raise serializers.ValidationError({"student": _("Cannot change the student after enrollment creation.")})
            if 'school_class' in data and data['school_class'] != self.instance.school_class:
                raise serializers.ValidationError({"school_class": _("Cannot change the school class after enrollment creation.")})
            # Prevent changing enrollment_date on update, unless specific logic allows
            if 'enrollment_date' in data and data['enrollment_date'] != self.instance.enrollment_date:
                 raise serializers.ValidationError({"enrollment_date": _("Enrollment date cannot be changed after creation through this endpoint.")})

        return data

    def create(self, validated_data):
        # Ensure enrollment_date is set if not provided (already handled in validate for creation)
        if 'enrollment_date' not in validated_data:
            validated_data['enrollment_date'] = timezone.now().date()
        return super().create(validated_data)


# 20. AnnouncementSerializer
class AnnouncementSerializer(serializers.ModelSerializer):
    """
    Serializer for Announcements.
    Handles creation, update, and display of announcements with various targeting options.
    The 'author' field is automatically set to the logged-in user in the ViewSet.
    """
    author_details = UserSerializer(source='author', read_only=True, help_text=_("Details of the user who authored the announcement."))
    publication_date = serializers.DateTimeField(read_only=True, help_text=_("Date and time when the announcement was published (system-set)."))

    title = serializers.CharField(max_length=255, help_text=_("Title of the announcement."))
    content = serializers.CharField(style={'base_template': 'textarea.html'}, help_text=_("Main content of the announcement."))

    target_grade_levels = serializers.PrimaryKeyRelatedField(
        queryset=GradeLevel.objects.all(),
        many=True,
        required=False,
        allow_empty=True,
        help_text=_("Optional. List of Grade Level IDs to target. Ignored if 'is_school_wide' is true.")
    )
    target_school_classes = serializers.PrimaryKeyRelatedField(
        queryset=SchoolClass.objects.all(),
        many=True,
        required=False,
        allow_empty=True,
        help_text=_("Optional. List of School Class IDs to target. Ignored if 'is_school_wide' is true.")
    )
    target_user_types = serializers.JSONField(
        required=False,
        allow_null=True,
        help_text=_("Optional. List of user type strings (e.g., [\"PARENT\", \"STUDENT\"]) to target. Ignored if 'is_school_wide' is true.")
    )
    is_school_wide = serializers.BooleanField(default=False, help_text=_("If true, targets all users in the school, overriding other target fields."))
    expiry_date = serializers.DateTimeField(required=False, allow_null=True, help_text=_("Optional. Date and time after which the announcement should no longer be considered active."))

    # Read-only fields for displaying details of targeted entities
    target_grade_levels_details = GradeLevelSerializer(source='target_grade_levels', many=True, read_only=True, help_text=_("Detailed list of targeted grade levels."))
    target_school_classes_details = SchoolClassListSerializer(source='target_school_classes', many=True, read_only=True, help_text=_("Detailed list of targeted school classes."))

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

    def validate_target_user_types(self, value: list | None) -> list | None:
        if value is None:
            return value
        if not isinstance(value, list):
            raise serializers.ValidationError(_("target_user_types must be a list."))

        valid_user_types = [choice[0] for choice in User.USER_TYPE_CHOICES]
        for item in value:
            if not isinstance(item, str) or item not in valid_user_types:
                raise serializers.ValidationError(
                    _("Invalid user type '%(user_type)s'. Valid choices are: %(valid_choices)s") %
                    {'user_type': item, 'valid_choices': ", ".join(valid_user_types)}
                )
        return value

    def validate(self, data: dict) -> dict:
        is_creating = self.instance is None

        # Determine effective value of is_school_wide
        is_school_wide = data.get('is_school_wide', self.instance.is_school_wide if not is_creating else False)

        # If not school-wide, at least one specific target must be provided
        if not is_school_wide:
            # For updates, if a field is not in `data`, use the instance's current value.
            # For creates, if not in `data`, it's None or default empty list.
            target_user_types = data.get('target_user_types', self.instance.target_user_types if not is_creating else None)
            target_grade_levels = data.get('target_grade_levels', list(self.instance.target_grade_levels.all()) if not is_creating and self.instance else [])
            target_school_classes = data.get('target_school_classes', list(self.instance.target_school_classes.all()) if not is_creating and self.instance else [])

            # Check if any targeting is actually specified
            has_target_user_types = bool(target_user_types)
            has_target_grade_levels = bool(target_grade_levels)
            has_target_school_classes = bool(target_school_classes)

            if not has_target_user_types and not has_target_grade_levels and not has_target_school_classes:
                raise serializers.ValidationError(
                    _("If the announcement is not school-wide, at least one targeting option (user types, grade levels, or school classes) must be specified.")
                )

        expiry_date = data.get('expiry_date', self.instance.expiry_date if not is_creating else None)
        # publication_date is set on create, or already exists on instance for update
        publication_date = self.instance.publication_date if not is_creating else timezone.now()

        if expiry_date and expiry_date < publication_date:
             raise serializers.ValidationError(_("Expiry date cannot be before the publication date."))

        # If is_school_wide is set, we might want to clear other fields in create/update
        # This serializer will ensure that if is_school_wide=True, other fields are ignored for targeting logic by the model/view.
        return data

    def _handle_m2m_fields(self, instance: Announcement, validated_data: dict, is_create: bool):
        """Helper to set M2M fields, respecting if data was provided."""
        if 'target_grade_levels' in validated_data or is_create:
            target_grade_levels_data = validated_data.pop('target_grade_levels', [])
            instance.target_grade_levels.set(target_grade_levels_data)

        if 'target_school_classes' in validated_data or is_create:
            target_school_classes_data = validated_data.pop('target_school_classes', [])
            instance.target_school_classes.set(target_school_classes_data)

    def create(self, validated_data: dict) -> Announcement:
        # Author is set in the viewset's perform_create
        announcement = Announcement(**validated_data) # M2M fields removed by pop in _handle_m2m_fields if called before super
        # Temporarily remove M2M data before creating the instance
        m2m_grade_levels = validated_data.pop('target_grade_levels', [])
        m2m_school_classes = validated_data.pop('target_school_classes', [])

        announcement = Announcement.objects.create(**validated_data)

        announcement.target_grade_levels.set(m2m_grade_levels)
        announcement.target_school_classes.set(m2m_school_classes)

        return announcement

    def update(self, instance: Announcement, validated_data: dict) -> Announcement:
        # Handle M2M fields first
        m2m_grade_levels = validated_data.pop('target_grade_levels', None)
        m2m_school_classes = validated_data.pop('target_school_classes', None)

        # Update standard fields using super's update or manually
        instance = super().update(instance, validated_data)

        if m2m_grade_levels is not None:
            instance.target_grade_levels.set(m2m_grade_levels)
        if m2m_school_classes is not None:
            instance.target_school_classes.set(m2m_school_classes)

        return instance


# 8. GradingPeriodSerializer
# ... (rest of the file remains the same for now)
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
    created_by_name = serializers.SerializerMethodField(method_name='get_created_by_name_typed', read_only=True) # Renamed method_name
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

    def get_created_by_name_typed(self, obj: SchoolEvent) -> str | None: # Renamed method and added type hint
        if obj.created_by:
            return obj.created_by.get_full_name() or obj.created_by.username
        return None

# 12. DidacticMaterialSerializer (Read-focused)
class DidacticMaterialSerializer(serializers.ModelSerializer):
    file_url = serializers.SerializerMethodField(method_name='get_file_url_typed', read_only=True, help_text="URL to access the material file.") # Added help_text and renamed method_name
    subject_name = serializers.CharField(source='subject.name', read_only=True, help_text="Name of the subject.")
    school_class_name = serializers.CharField(source='school_class.__str__', read_only=True, allow_null=True, help_text="Name of the school class, if specific.")
    uploader_info = UserSerializer(source='uploader', read_only=True, help_text="Details of the user who uploaded the material.")

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
        read_only_fields = ('upload_date', 'file_url') # file_url is already read_only by definition

    def get_file_url_typed(self, obj: DidacticMaterial) -> str | None: # Renamed method and added type hint
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
    """
    Serializer for the batch re-enrollment action.
    Validates the target school year for re-enrolling students from a source school year.
    """
    target_school_year_id = serializers.IntegerField(
        help_text=_("ID of the SchoolYear to re-enroll students into.")
    )
    # source_school_year_id will come from the URL (viewset's pk) and be injected into context

    def validate_target_school_year_id(self, value: int) -> int:
        try:
            target_year = SchoolYear.objects.get(pk=value)
        except SchoolYear.DoesNotExist:
            raise serializers.ValidationError(_("Target school year not found."))

        # Example validation: Target year should probably be active or not too far in the past.
        # if not target_year.is_active and target_year.end_date < timezone.now().date() - timezone.timedelta(days=365):
        #     raise serializers.ValidationError(_("Target school year is too old or not active."))
        return value

    def validate(self, data: dict) -> dict:
        source_school_year_id = self.context.get('source_school_year_id')
        target_school_year_id = data.get('target_school_year_id')

        if source_school_year_id is None:
            # This should be ensured by the view providing context.
            raise DjangoValidationError(_("Source school year ID must be provided in context for validation."))

        if source_school_year_id == target_school_year_id:
            raise serializers.ValidationError({
                "target_school_year_id": _("Target school year cannot be the same as the source school year.")
            })

        try:
            source_year = SchoolYear.objects.get(pk=source_school_year_id)
            # target_year already fetched in field validation, but can fetch again if preferred
            target_year = SchoolYear.objects.get(pk=target_school_year_id)

            if target_year.start_date <= source_year.end_date:
                 raise serializers.ValidationError({
                     "target_school_year_id": _("Target school year must start after the source school year ends.")
                 })
            # Example: Ensure target year is not excessively far in the future (e.g., more than 1 year ahead of current)
            # This kind of specific business logic can be added as needed.
            # current_date = timezone.now().date()
            # if target_year.start_date > current_date.replace(year=current_date.year + 2):
            #      raise serializers.ValidationError({
            #          "target_school_year_id": _("Target school year is too far in the future.")
            #      })

        except SchoolYear.DoesNotExist:
            # Should be caught by individual field validation or context provision.
            raise DjangoValidationError(_("Invalid source or target school year ID during cross-field validation."))

        return data


# 21. EnrollmentReportSerializer
class EnrollmentReportSerializer(serializers.ModelSerializer):
    """
    Serializer for generating a CSV report of enrollments.
    Flattens related data for student, class, grade level, and school year.
    """
    enrollment_id = serializers.IntegerField(source='id', read_only=True, help_text=_("Unique ID of the enrollment record."))
    student_name = serializers.CharField(source='student.user.get_full_name', read_only=True, help_text=_("Full name of the enrolled student."))
    student_username = serializers.CharField(source='student.user.username', read_only=True, help_text=_("Username of the enrolled student."))
    school_class_name = serializers.CharField(source='school_class.name', read_only=True, help_text=_("Name of the class."))
    grade_level_name = serializers.CharField(source='school_class.grade_level.name', read_only=True, help_text=_("Name of the grade level of the class."))
    school_year = serializers.IntegerField(source='school_class.school_year.year', read_only=True, help_text=_("Academic year of the enrollment."))
    enrollment_status = serializers.CharField(source='get_status_display', read_only=True, help_text=_("Current status of the enrollment (e.g., Active, Completed)."))
    enrollment_date = serializers.DateField(read_only=True, help_text=_("Date when the enrollment was made."))


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

# 22. Dashboard Serializers
class GradeLevelCountSerializer(serializers.Serializer):
    """Represents count of students per grade level."""
    grade_level_name = serializers.CharField()
    count = serializers.IntegerField()

class DashboardSummaryDataSerializer(serializers.Serializer):
    """Serializer for the data structure returned by DashboardSummaryView."""
    total_active_students = serializers.IntegerField()
    active_students_by_grade_level = GradeLevelCountSerializer(many=True)
    total_preregistered_students = serializers.IntegerField()
    total_pending_validation_students = serializers.IntegerField()
    total_active_enrollments = serializers.IntegerField()
    active_school_years = serializers.IntegerField()
