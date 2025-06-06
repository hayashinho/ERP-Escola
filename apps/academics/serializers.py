from rest_framework import serializers
from apps.academics.models import (
    SchoolYear, Subject, SchoolClass, Enrollment,
    GradingPeriod, Grade, Attendance, SchoolEvent, DidacticMaterial,
    TeacherAssignment
)
from apps.students.models import GradeLevel
from apps.students.serializers import GradeLevelSerializer, StudentSimpleSerializer
from apps.accounts.serializers import UserSerializer
from django.utils.translation import gettext_lazy as _
from django.core.exceptions import ValidationError as DjangoValidationError


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
class EnrollmentStudentRelatedField(serializers.RelatedField):
    def to_representation(self, value):
        return value.user.get_full_name() or value.user.username

class EnrollmentSchoolClassRelatedField(serializers.RelatedField):
    def to_representation(self, value):
        return f"{value.name} ({value.school_year.year})"

class EnrollmentSerializer(serializers.ModelSerializer):
    student_name = EnrollmentStudentRelatedField(source='student', read_only=True)
    school_class_info = EnrollmentSchoolClassRelatedField(source='school_class', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)

    class Meta:
        model = Enrollment
        fields = (
            'id',
            'student',
            'student_name',
            'school_class',
            'school_class_info',
            'enrollment_date',
            'status',
            'status_display'
        )
        read_only_fields = ('enrollment_date',)


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
