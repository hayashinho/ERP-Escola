from rest_framework import serializers
from django.utils.translation import gettext_lazy as _ # Added import
from apps.students.models import GradeLevel, Student, StudentParentAssociation, StudentDocument
from apps.accounts.serializers import UserSerializer # Reverted import

class GradeLevelSerializer(serializers.ModelSerializer):
    """
    Serializer for the GradeLevel model.
    Represents a specific grade level in the school (e.g., 1st Grade, 10th Grade).
    """
    name = serializers.CharField(help_text=_("Name of the grade level (e.g., '1st Grade', 'Jardim II')."))
    order_in_sequence = serializers.IntegerField(help_text=_("Numeric order for sorting grade levels sequentially."))

    class Meta:
        model = GradeLevel
        fields = ('id', 'name', 'order_in_sequence')

class StudentDocumentSerializer(serializers.ModelSerializer):
    """
    Serializer for the StudentDocument model.
    Manages documents associated with a student. Allows updating validation status and notes.
    """
    student = serializers.PrimaryKeyRelatedField(read_only=True, help_text=_("The student this document belongs to."))
    document_type = serializers.ChoiceField(choices=StudentDocument.DOCUMENT_TYPE_CHOICES, read_only=True, help_text=_("Type of the document (e.g., RG, CPF, Birth Certificate)."))
    get_document_type_display = serializers.CharField(read_only=True, help_text=_("Display name for the document type.")) # Removed source
    document_name = serializers.CharField(read_only=True, help_text=_("Name of the document, often derived from the filename."))
    file = serializers.FileField(read_only=True, help_text=_("The uploaded file itself."))
    file_url = serializers.SerializerMethodField(read_only=True, help_text=_("URL to access the document file."))
    upload_date = serializers.DateField(read_only=True, help_text=_("Date when the document was uploaded."))
    validation_status = serializers.ChoiceField(
        choices=StudentDocument.VALIDATION_STATUS_CHOICES,
        help_text=_("Current validation status of the document (e.g., Pending, Approved, Rejected). This field is updatable.")
    )
    get_validation_status_display = serializers.CharField(read_only=True, help_text=_("Display name for the validation status.")) # Removed source
    is_optional = serializers.BooleanField(read_only=True, help_text=_("Indicates if this document type is optional for the student."))
    notes = serializers.CharField(
        required=False, allow_blank=True, style={'base_template': 'textarea.html'},
        help_text=_("Administrative notes regarding the document or its validation. This field is updatable.")
    )

    class Meta:
        model = StudentDocument
        fields = (
            'id', 'student', 'document_type', 'get_document_type_display', 'document_name',
            'file', 'file_url', 'upload_date', 'validation_status',
            'get_validation_status_display', 'is_optional', 'notes'
        )
        # Most fields are read-only as they are set during creation or derived.
        # `validation_status` and `notes` are updatable via the `update` method.
        read_only_fields = (
            'id', 'student', 'document_type', 'get_document_type_display',
            'document_name', 'file', 'file_url', 'upload_date',
            'get_validation_status_display', 'is_optional'
        )


    def get_file_url(self, obj: StudentDocument) -> str | None:
        request = self.context.get('request')
        if obj.file and request:
            return request.build_absolute_uri(obj.file.url)
        return None

    def update(self, instance, validated_data):
        instance.validation_status = validated_data.get('validation_status', instance.validation_status)
        instance.notes = validated_data.get('notes', instance.notes)

        # Ensure that if status is not REJECTED, notes might be cleared or handled as per business logic
        # For now, we allow notes to be updated regardless of status,
        # but specific logic can be added e.g., if status is APPROVED, clear notes.
        if instance.validation_status == StudentDocument.STATUS_APPROVED: # Corrected
            # Example: Clear notes if document is approved, or set a default note.
            # instance.notes = "Document approved."
            pass # Keep notes as provided by user for now

        instance.save(update_fields=['validation_status', 'notes'])
        return instance

class StudentParentAssociationSerializer(serializers.ModelSerializer):
    """
    Serializer for the StudentParentAssociation model.
    Links a student to a parent/guardian user and specifies the relationship type.
    """
    parent_user = serializers.PrimaryKeyRelatedField(
        queryset=StudentParentAssociation.objects.all(), # queryset is required for writable PrimaryKeyRelatedField if used for write
        help_text=_("The user ID of the parent/guardian.")
    )
    parent_user_details = UserSerializer(source='parent_user', read_only=True, help_text=_("Detailed information of the parent/guardian user."))
    relationship_type = serializers.ChoiceField(
        choices=StudentParentAssociation.RELATIONSHIP_CHOICES,
        help_text=_("Type of relationship (e.g., Mother, Father, Guardian).")
    )
    relationship_type_display = serializers.CharField(source='get_relationship_type_display', read_only=True, help_text=_("Display name for the relationship type."))

    class Meta:
        model = StudentParentAssociation
        fields = (
            'id',
            'parent_user', # ID of the User model instance for the parent
            'parent_user_details', # Nested User details
            'relationship_type',
            'relationship_type_display',
        )
        # If this serializer were to be used for writing associations directly (e.g. nested under student),
        # 'student' field would also be needed, or handled in the parent serializer's create/update.

class StudentSerializer(serializers.ModelSerializer):
    """
    Serializer for the Student model.
    Provides a comprehensive view of student data, including linked user details,
    pretended grade level, documents, and parent associations.
    Allows updating specific fields like registration status, allergies, and observations.
    """
    user = serializers.PrimaryKeyRelatedField(read_only=True, help_text=_("The user ID associated with this student record. This is the student's primary key."))
    user_details = UserSerializer(source='user', read_only=True, help_text=_("Detailed information of the user account linked to this student."))
    grade_level_pretended = serializers.PrimaryKeyRelatedField(
        queryset=GradeLevel.objects.all(),
        help_text=_("ID of the grade level the student is applying for or intends to join.")
    )
    grade_level_pretended_details = GradeLevelSerializer(source='grade_level_pretended', read_only=True, help_text=_("Detailed information of the pretended grade level."))
    documents = StudentDocumentSerializer(many=True, read_only=True, help_text=_("List of documents associated with the student."))
    parent_associations = StudentParentAssociationSerializer(many=True, read_only=True, help_text=_("List of parents/guardians associated with the student."))

    registration_status = serializers.ChoiceField(
        choices=Student.REGISTRATION_STATUS_CHOICES,
        help_text=_("Current registration status of the student (e.g., Pre-registered, Pending Validation, Approved, Rejected). Updatable.")
    )
    registration_status_display = serializers.CharField(source='get_registration_status_display', read_only=True, help_text=_("Display name for the registration status."))
    enrollment_date = serializers.DateField(read_only=True, help_text=_("Date when the student was officially enrolled (after approval)."))
    school_entry_date = serializers.DateField(read_only=True, help_text=_("Date when the student first joined the school."))

    allergies = serializers.CharField(
        required=False, allow_blank=True, style={'base_template': 'textarea.html'},
        help_text=_("Information about student's allergies. Updatable.")
    )
    observations = serializers.CharField(
        required=False, allow_blank=True, style={'base_template': 'textarea.html'},
        help_text=_("General observations about the student. Updatable.")
    )
    rejection_reason = serializers.CharField(
        required=False, allow_blank=True, style={'base_template': 'textarea.html'},
        help_text=_("Reason for rejection if registration_status is 'Rejected'. Updatable and relevant only when status is 'Rejected'.")
    )

    class Meta:
        model = Student
        fields = (
            'user',
            'user_details',
            'grade_level_pretended',
            'grade_level_pretended_details',
            'enrollment_date',
            'registration_status',
            'registration_status_display',
            'school_entry_date',
            'allergies',
            'observations',
            'rejection_reason',
            'documents',
            'parent_associations',
        )
        read_only_fields = (
            # 'user' is PK, inherently read-only after creation. Explicitly stated above.
            'user_details',
            # 'grade_level_pretended' is updatable on create, read-only here for PATCH context (update view might handle it differently if needed)
            # For StudentManagementViewSet, grade_level_pretended is NOT updatable.
            'grade_level_pretended_details',
            'enrollment_date',
            'school_entry_date',
            'documents',
            'parent_associations',
            'registration_status_display',
        )

    def update(self, instance: Student, validated_data: dict) -> Student:
        fields_to_update = []

        if 'registration_status' in validated_data:
            instance.registration_status = validated_data['registration_status']
            fields_to_update.append('registration_status')

            # Handle rejection_reason based on the new status
            if instance.registration_status == Student.STATUS_REJECTED: # Use constant from model
                instance.rejection_reason = validated_data.get('rejection_reason', instance.rejection_reason)
            else:
                instance.rejection_reason = None # Clear if not rejected
            fields_to_update.append('rejection_reason')

        # Update other allowed fields if present in validated_data
        for field_name in ['allergies', 'observations']:
            if field_name in validated_data:
                setattr(instance, field_name, validated_data[field_name])
                fields_to_update.append(field_name)

        if fields_to_update:
            instance.save(update_fields=fields_to_update)
        return instance

class StudentSimpleSerializer(serializers.ModelSerializer):
    """
    Simplified serializer for the Student model, focused on identification.
    Useful for lists or dropdowns where only basic student info is needed.
    """
    full_name = serializers.CharField(source='user.get_full_name', read_only=True)
    email = serializers.EmailField(source='user.email', read_only=True)

    class Meta:
        model = Student
        # 'user' é a PK de Student.
        fields = ('user', 'full_name', 'email') # 'user' aqui será o user_id (PK)
        # Se quisesse o ID do objeto User em vez do ID do Student (que é o mesmo user_id)
        # poderia ser 'user_id' se o campo no Student fosse nomeado diferentemente, mas como é PK, 'user' é o ID.


class StudentReportSerializer(serializers.ModelSerializer):
    """
    Serializer for generating a CSV report of students.
    Flattens related User and UserProfile data.
    Includes derived fields for current grade level and active enrollment school year.
    """
    user_id = serializers.IntegerField(source='user.id', read_only=True)
    username = serializers.CharField(source='user.username', read_only=True)
    full_name = serializers.CharField(source='user.get_full_name', read_only=True)
    email = serializers.EmailField(source='user.email', read_only=True)

    # UserProfile fields - allow for profile to not exist
    cpf = serializers.CharField(source='user.profile.cpf', read_only=True, allow_null=True)
    date_of_birth = serializers.DateField(source='user.profile.date_of_birth', read_only=True, allow_null=True)

    student_registration_status = serializers.CharField(source='get_registration_status_display', read_only=True)
    student_enrollment_date = serializers.DateField(source='enrollment_date', read_only=True, help_text="Student's initial enrollment date in the school.")

    # Fields to be annotated by the ViewSet's queryset
    current_grade_level_name = serializers.CharField(read_only=True, allow_null=True, help_text="Current grade level name, derived from active enrollment in the specified school year.")
    active_enrollment_school_year = serializers.IntegerField(read_only=True, allow_null=True, help_text="School year of the active enrollment used for determining current grade level.")

    class Meta:
        model = Student
        fields = (
            'user_id',
            'username',
            'full_name',
            'email',
            'cpf',
            'date_of_birth',
            'student_registration_status',
            'student_enrollment_date',
            'current_grade_level_name', # From annotation
            'active_enrollment_school_year', # From annotation
        )
