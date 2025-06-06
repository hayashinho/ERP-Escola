from rest_framework import serializers
from apps.students.models import GradeLevel, Student, StudentParentAssociation, StudentDocument
from apps.accounts.serializers import UserSerializer # Importar UserSerializer

class GradeLevelSerializer(serializers.ModelSerializer):
    """
    Serializer para o modelo GradeLevel.
    """
    class Meta:
        model = GradeLevel
        fields = '__all__' # Inclui 'id', 'name', 'order_in_sequence'

class StudentDocumentSerializer(serializers.ModelSerializer):
    """
    Serializer para o modelo StudentDocument.
    """
    file_url = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = StudentDocument
        fields = (
            'id', 'student', 'document_type', 'get_document_type_display', 'document_name',
            'file', 'file_url', 'upload_date', 'validation_status',
            'get_validation_status_display', 'is_optional', 'notes'
        )
        read_only_fields = (
            'id',
            'student',
            'document_type',
            'get_document_type_display',
            'document_name', # Typically set from filename on creation
            'file', # File itself should not be changed via this update
            'file_url',
            'upload_date',
            'get_validation_status_display',
            'is_optional', # Should be defined by document type, not changed per instance
        )

    def get_file_url(self, obj):
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
        if instance.validation_status == StudentDocument.ValidationStatus.APPROVED:
            # Example: Clear notes if document is approved, or set a default note.
            # instance.notes = "Document approved."
            pass # Keep notes as provided by user for now

        instance.save(update_fields=['validation_status', 'notes'])
        return instance

class StudentParentAssociationSerializer(serializers.ModelSerializer):
    """
    Serializer para o modelo StudentParentAssociation.
    """
    parent_user_details = UserSerializer(source='parent_user', read_only=True)
    relationship_type_display = serializers.CharField(source='get_relationship_type_display', read_only=True)

    class Meta:
        model = StudentParentAssociation
        fields = (
            'id',
            'parent_user',
            'parent_user_details',
            'relationship_type',
            'relationship_type_display',
        )

class StudentSerializer(serializers.ModelSerializer):
    """
    Serializer para o modelo Student.
    Inclui detalhes do usuário, série pretendida, documentos e associações de pais.
    """
    user_details = UserSerializer(source='user', read_only=True)
    grade_level_pretended_details = GradeLevelSerializer(source='grade_level_pretended', read_only=True)
    documents = StudentDocumentSerializer(many=True, read_only=True)
    parent_associations = StudentParentAssociationSerializer(many=True, read_only=True)
    registration_status_display = serializers.CharField(source='get_registration_status_display', read_only=True)

    class Meta:
        model = Student
        fields = (
            'user', # This is the PK and effectively the ID of the student
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
            'user', # Cannot change the user associated with the student record
            'user_details',
            'grade_level_pretended', # Should be set on creation or specific action
            'grade_level_pretended_details',
            'enrollment_date', # Typically set by system or specific action
            'school_entry_date', # Typically set by system or specific action
            'documents',
            'parent_associations',
            'registration_status_display', # This is a display field
        )

    def update(self, instance, validated_data):
        # Allow updating registration_status and rejection_reason
        # Other fields in validated_data will be handled by super().update() if they are not read_only
        instance.registration_status = validated_data.get('registration_status', instance.registration_status)

        # Only allow rejection_reason if status is REJECTED
        if instance.registration_status == Student.RegistrationStatus.REJECTED:
            instance.rejection_reason = validated_data.get('rejection_reason', instance.rejection_reason)
        else:
            # If status is not REJECTED, clear any existing rejection_reason
            instance.rejection_reason = None

        # For other potentially updatable fields by Secretaria (e.g. allergies, observations)
        instance.allergies = validated_data.get('allergies', instance.allergies)
        instance.observations = validated_data.get('observations', instance.observations)

        instance.save()
        return instance

class StudentSimpleSerializer(serializers.ModelSerializer):
    """
    Serializer simplificado para o modelo Student, focado em identificação.
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
    student_enrollment_date = serializers.DateField(source='enrollment_date', read_only=True) # Student's own enrollment_date

    # Fields to be annotated by the ViewSet's queryset
    current_grade_level_name = serializers.CharField(read_only=True, allow_null=True)
    active_enrollment_school_year = serializers.IntegerField(read_only=True, allow_null=True) # Assuming year is an integer

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
