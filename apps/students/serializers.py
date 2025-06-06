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
        read_only_fields = ('upload_date', 'file_url')

    def get_file_url(self, obj):
        request = self.context.get('request')
        if obj.file and request:
            return request.build_absolute_uri(obj.file.url)
        return None

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
            'rejection_reason', # Adicionado na última migração
            'documents',
            'parent_associations',
        )

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
