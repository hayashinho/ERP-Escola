from django.db import transaction
from django.shortcuts import get_object_or_404 # Para obter objetos ou retornar 404
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status, serializers, viewsets # Adicionado viewsets
from rest_framework.permissions import AllowAny, IsAdminUser # Adicionado IsAdminUser
from rest_framework.decorators import action # Adicionado action
from rest_framework.parsers import MultiPartParser, FormParser

from apps.accounts.serializers import UserRegistrationSerializer # Reverted import
from apps.accounts.models import UserProfile, User # Reverted import
from apps.students.models import Student, GradeLevel, StudentParentAssociation, StudentDocument
from apps.students.serializers import StudentSerializer # Importar StudentSerializer

# Define a minimal serializer for drf-spectacular to pick up
class EmptySerializer(serializers.Serializer): # Make sure 'serializers' is imported if not already
    pass

class PreRegistrationAPIView(APIView):
    """
    Handles the public pre-registration process for new students.

    This endpoint is publicly accessible and expects a multipart/form-data payload
    due to file uploads for student documents.

    **Key Expected Payload Fields:**
    - `parent_user_data` (JSON string or form fields): Data for the parent's User account (e.g., username, email, password).
    - `parent_profile_data` (JSON string or form fields): Data for the parent's UserProfile (e.g., CPF, address).
    - `parent_relationship_type` (string): Relationship of the parent to the student (e.g., 'MOTHER', 'FATHER').
    - `student_user_data` (JSON string or form fields): Data for the student's User account.
    - `student_profile_data` (JSON string or form fields): Data for the student's UserProfile.
    - `student_data` (JSON string or form fields): Data for the Student record itself (e.g., `grade_level_pretended_id`, `allergies`).
        - `grade_level_pretended_id` (integer, required in `student_data`): ID of the GradeLevel the student is applying for.
    - `document_types` (list of strings): List of document types being uploaded (e.g., ['RG', 'CPF_STUDENT']). Must match `document_files`.
    - `document_files` (list of files): List of uploaded document files. Must match `document_types`.

    **On Success (HTTP 201 Created):**
    Returns a success message with IDs of created entities.

    **On Failure (HTTP 400 Bad Request or 500 Internal Server Error):**
    Returns an error message detailing the issue.
    """
    serializer_class = EmptySerializer # For schema generation; actual validation is custom.
    permission_classes = [AllowAny]
    parser_classes = (MultiPartParser, FormParser)

    def post(self, request, *args, **kwargs):
        parent_user_data = request.data.get('parent_user_data', {})
        parent_profile_data = request.data.get('parent_profile_data', {})
        parent_relationship_type = request.data.get('parent_relationship_type')
        student_user_data = request.data.get('student_user_data', {})
        student_profile_data = request.data.get('student_profile_data', {})
        student_data_payload = request.data.get('student_data', {})

        document_types = request.data.getlist('document_types')
        uploaded_files = request.FILES.getlist('document_files')

        if not parent_user_data:
            return Response({"error": "Dados do responsável ('parent_user_data') não fornecidos."}, status=status.HTTP_400_BAD_REQUEST)
        if not parent_relationship_type:
            return Response({"error": "Tipo de relação do responsável ('parent_relationship_type') não fornecido."}, status=status.HTTP_400_BAD_REQUEST)
        if not student_user_data:
            return Response({"error": "Dados do usuário aluno ('student_user_data') não fornecidos."}, status=status.HTTP_400_BAD_REQUEST)
        if not student_data_payload.get('grade_level_pretended_id'):
             return Response({"error": "ID da série pretendida ('grade_level_pretended_id') não fornecido em 'student_data'."}, status=status.HTTP_400_BAD_REQUEST)

        if len(document_types) != len(uploaded_files):
            return Response(
                {"error": "A quantidade de 'document_types' não corresponde à quantidade de 'document_files'."},
                status=status.HTTP_400_BAD_REQUEST
            )

        valid_doc_types_from_model = [choice[0] for choice in StudentDocument.DOCUMENT_TYPE_CHOICES]
        for doc_type in document_types:
            if doc_type not in valid_doc_types_from_model:
                return Response(
                    {"error": f"Tipo de documento '{doc_type}' inválido. Escolha entre: {', '.join(valid_doc_types_from_model)}."},
                    status=status.HTTP_400_BAD_REQUEST
                )

        valid_relationship_types = [choice[0] for choice in StudentParentAssociation.RELATIONSHIP_CHOICES]
        if parent_relationship_type not in valid_relationship_types:
            return Response(
                {"error": f"Tipo de relação ('{parent_relationship_type}') inválido. Escolha entre: {', '.join(valid_relationship_types)}."},
                status=status.HTTP_400_BAD_REQUEST
            )

        parent_user_data['user_type'] = User.USER_TYPE_PARENT
        student_user_data['user_type'] = User.USER_TYPE_STUDENT

        parent_user_serializer = UserRegistrationSerializer(data=parent_user_data)
        student_user_serializer = UserRegistrationSerializer(data=student_user_data)

        try:
            if not parent_user_serializer.is_valid(raise_exception=False):
                return Response(parent_user_serializer.errors, status=status.HTTP_400_BAD_REQUEST)
            if not student_user_serializer.is_valid(raise_exception=False):
                return Response(student_user_serializer.errors, status=status.HTTP_400_BAD_REQUEST)

            try:
                grade_level_id = int(student_data_payload.get('grade_level_pretended_id'))
                grade_level = GradeLevel.objects.get(pk=grade_level_id)
            except (ValueError, TypeError, GradeLevel.DoesNotExist):
                 return Response({"error": "ID da série pretendida ('grade_level_pretended_id') inválido ou não encontrado."}, status=status.HTTP_400_BAD_REQUEST)

            with transaction.atomic():
                parent_user = parent_user_serializer.save()
                UserProfile.objects.create(user=parent_user, **parent_profile_data)

                student_user = student_user_serializer.save()
                UserProfile.objects.create(user=student_user, **student_profile_data)

                allowed_student_fields = {'allergies', 'observations'}
                student_direct_data = {
                    k: v for k, v in student_data_payload.items() if k in allowed_student_fields
                }
                student = Student.objects.create(
                    user=student_user,
                    grade_level_pretended=grade_level,
                    registration_status=Student.STATUS_PENDING_VALIDATION,
                    **student_direct_data
                )

                StudentParentAssociation.objects.create(
                    student=student,
                    parent_user=parent_user,
                    relationship_type=parent_relationship_type
                )

                created_documents_info = []
                for doc_type, uploaded_file in zip(document_types, uploaded_files):
                    doc = StudentDocument.objects.create(
                        student=student,
                        document_type=doc_type,
                        file=uploaded_file,
                        document_name=uploaded_file.name
                    )
                    created_documents_info.append({
                        'document_type': doc.get_document_type_display(),
                        'file_name': doc.file.name,
                        'document_id': doc.id
                    })

            return Response({
                'message': 'Pré-cadastro realizado com sucesso! Responsável, aluno, perfis, associação e documentos processados.',
                'parent_user_id': parent_user.id,
                'student_user_id': student_user.id,
                'student_record_id': student.user_id,
                'documents_processed': len(created_documents_info),
                'created_documents': created_documents_info
            }, status=status.HTTP_201_CREATED)

        except Exception as e:
            return Response({"error": "Ocorreu um erro interno durante o pré-cadastro.", "detail": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class PendingRegistrationViewSet(viewsets.ReadOnlyModelViewSet):
    """
    Manages student registrations that are pending validation by administrative staff.

    **Permissions:** Requires admin user status.

    **Supported Actions:**
    - `list`: Retrieves students with 'Pending Validation' status.
    - `retrieve`: Gets details of a specific student pending validation.
    - `approve` (custom action): Approves a student's registration.
    - `reject` (custom action): Rejects a student's registration, requiring a reason.
    """
    queryset = Student.objects.none()  # Base queryset for schema generation; actual data from get_queryset.
    serializer_class = StudentSerializer # Used for list and retrieve actions.
    permission_classes = [IsAdminUser] # Apenas usuários admin/staff podem acessar
    lookup_field = 'pk' # Student model's PK is 'user' (OneToOneField to User) which acts as 'pk'

    def get_queryset(self):
        """
        Retorna apenas alunos com status 'PENDING_VALIDATION'.
        Otimiza a consulta com select_related e prefetch_related.
        """
        return Student.objects.filter(
            registration_status=Student.STATUS_PENDING_VALIDATION
        ).select_related(
            'user', 'user__profile', 'grade_level_pretended'
        ).prefetch_related(
            'documents',
            'parent_associations',
            'parent_associations__parent_user',
            'parent_associations__parent_user__profile'
        ).order_by('user__date_joined') # Ordenar pelos mais antigos primeiro

    @action(detail=True, methods=['post'], url_path='approve-registration')
    def approve(self, request, pk=None):
        """
        Approves a student's pending registration.

        Changes the student's `registration_status` to 'ACTIVE'.
        No request body is expected.
        """
        student = get_object_or_404(Student, pk=pk)
        if student.registration_status != Student.RegistrationStatus.PENDING_VALIDATION:
            return Response(
                {'error': 'Este aluno não está pendente de validação.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        student.registration_status = Student.STATUS_ACTIVE
        # Opcional: definir data de matrícula se não definida antes
        # if not student.enrollment_date:
        #     student.enrollment_date = timezone.now().date()
        student.save()
        return Response({'status': 'success', 'message': f'Matrícula do aluno {student} aprovada.'})

    @action(detail=True, methods=['post'], url_path='reject-registration')
    def reject(self, request, pk=None):
        """
        Rejeita o registro de um aluno.
        Muda o status para 'REJECTED' e registra o motivo.

        **Expected Request Body:**
        ```json
        {
            "reason": "Detailed reason for rejection."
        }
        ```
        """
        student = get_object_or_404(Student, pk=pk)
        if student.registration_status != Student.RegistrationStatus.PENDING_VALIDATION:
            return Response(
                {'error': 'This student is not pending validation.'}, # Changed to English
                status=status.HTTP_400_BAD_REQUEST
            )

        rejection_reason = request.data.get('reason')
        if not rejection_reason:
            return Response(
                {'error': 'Rejection reason is required.'}, # Changed to English
                status=status.HTTP_400_BAD_REQUEST
            )

        student.registration_status = Student.RegistrationStatus.REJECTED # Corrected constant
        student.rejection_reason = rejection_reason
        student.save(update_fields=['registration_status', 'rejection_reason']) # Specify update_fields
        return Response({'status': 'success', 'message': f'Student registration {student} rejected.'}) # Changed to English


class StudentManagementViewSet(viewsets.ModelViewSet):
    """
    Provides administrative management of student records by Secretaria/staff.

    **Permissions:** Requires admin user status (or specific 'Secretaria' group).

    **Supported Actions:**
    - `list`: Retrieves a list of all students. Supports filtering by `registration_status` and `grade_level_pretended`.
    - `retrieve`: Gets details of a specific student.
    - `partial_update` (PATCH): Updates specific fields of a student record (e.g., `registration_status`, `allergies`, `observations`, `rejection_reason`).
      Refer to `StudentSerializer` for updatable fields.

    Direct creation (POST), full update (PUT), and deletion (DELETE) are typically not performed
    through this endpoint, but through more specific processes like pre-registration or enrollment actions.
    """
    queryset = Student.objects.all().select_related(
        'user', 'user__profile', 'grade_level_pretended'
    ).prefetch_related(
        'documents',
        'parent_associations',
        'parent_associations__parent_user',
        'parent_associations__parent_user__profile'
    ).order_by('user__username')
    serializer_class = StudentSerializer
    permission_classes = [IsAdminUser] # Or a more specific 'Secretaria' permission
    http_method_names = ['get', 'patch', 'head', 'options'] # Allow only these methods

    # Add filtering for registration_status
    filterset_fields = ['registration_status', 'grade_level_pretended']

    # The StudentSerializer's update method already handles the logic for
    # updating registration_status and rejection_reason (conditionally).
    # It also ensures other fields are read-only as defined.


from rest_framework_csv.renderers import CSVRenderer
from rest_framework import generics
from rest_framework.permissions import IsAdminUser # Import IsAdminUser
from django.db.models import Subquery, OuterRef, F, CharField, IntegerField
from apps.academics.models import Enrollment, SchoolClass, SchoolYear # Reverted import
from .models import Student # Import Student model
from .serializers import StudentReportSerializer # Import the new report serializer
from django.utils import timezone
from apps.auditing.decorators import audit_view_action # Import decorator
from apps.auditing.models import AuditLog # Import AuditLog for action types

class StudentListCSVExportView(generics.ListAPIView):
    """
    API View to export a list of students to a CSV file.

    **Permissions:** Requires admin user status.

    **Supported Query Parameters for Filtering:**
    - `grade_level_id` (integer): Filter students by their current enrolled grade level ID (based on active enrollment in `school_year_id` if provided).
    - `registration_status` (string): Filter students by their registration status (e.g., 'ACTIVE', 'PRE_REGISTERED').
    - `school_year_id` (integer): Specify the school year context for determining 'current_grade_level_name' and 'active_enrollment_school_year' annotations.
                                 If provided, `grade_level_id` filter will apply to enrollments within this school year.

    The output CSV includes student details, profile information, and annotated enrollment data.
    """
    renderer_classes = (CSVRenderer,)
    serializer_class = StudentReportSerializer # Defines columns for the CSV report.
    permission_classes = [IsAdminUser] # Or your specific permission

    def get_queryset(self):
        queryset = Student.objects.select_related('user__profile').all()

        # Parameters for filtering active enrollment context
        school_year_id = self.request.query_params.get('school_year_id')

        # Annotate with latest active enrollment data for a specific school year if provided
        # This is a simplified approach: assumes one active enrollment per student per year.
        # A more robust solution might be needed for complex cases (e.g. multiple active enrollments).
        active_enrollment_qs = Enrollment.objects.filter(
            student=OuterRef('pk'),
            status=Enrollment.STATUS_ACTIVE
        ).order_by('-enrollment_date') # Get the latest if multiple (though ideally should be one)

        if school_year_id:
            try:
                # Ensure school_year_id is valid before using in subquery
                SchoolYear.objects.get(pk=school_year_id)
                active_enrollment_qs = active_enrollment_qs.filter(school_class__school_year_id=school_year_id)
            except (ValueError, SchoolYear.DoesNotExist):
                # Handle invalid school_year_id, perhaps by returning no enrollments or raising error
                # For now, the subquery will just not match if school_year_id is invalid.
                pass # Or active_enrollment_qs = Enrollment.objects.none() to be safe

        queryset = queryset.annotate(
            annotated_grade_level_name=Subquery(
                active_enrollment_qs.values('school_class__grade_level__name')[:1],
                output_field=CharField(null=True)
            ),
            annotated_school_year=Subquery(
                active_enrollment_qs.values('school_class__school_year__year')[:1],
                output_field=IntegerField(null=True)
            )
        )
        # The serializer fields `current_grade_level_name` and `active_enrollment_school_year`
        # will map to these annotated fields. We need to ensure the source names match.
        # Let's rename them in the queryset to match serializer expectations directly.
        queryset = queryset.annotate(
            current_grade_level_name=F('annotated_grade_level_name'),
            active_enrollment_school_year=F('annotated_school_year')
        )

        # Filtering
        grade_level_id = self.request.query_params.get('grade_level_id')
        if grade_level_id:
            # This filters based on the annotated grade_level_name from the active enrollment.
            # To filter by PK, we'd need to filter on the subquery's school_class__grade_level_id.
            # For simplicity with the current annotation, this filters if name matches.
            # A more direct filter on ID:
            queryset = queryset.filter(enrollments__school_class__grade_level_id=grade_level_id, enrollments__status=Enrollment.STATUS_ACTIVE)
            if school_year_id: # Ensure this enrollment is in the specified school year
                 queryset = queryset.filter(enrollments__school_class__school_year_id=school_year_id)


        registration_status = self.request.query_params.get('registration_status')
        if registration_status:
            queryset = queryset.filter(registration_status=registration_status)

        # Ensure distinct students if filters cause duplicates due to joins
        return queryset.distinct()

    def get_filename(self, request=None, format=None):
        timestamp = timezone.now().strftime('%Y%m%d_%H%M%S')
        return f'student_list_report_{timestamp}.csv'

    def list(self, request, *args, **kwargs):
        response = super().list(request, *args, **kwargs)
        # Set filename for download
        response['Content-Disposition'] = f'attachment; filename="{self.get_filename()}"'
        return response

    @audit_view_action(
        action_type=AuditLog.ACTION_EXPORTED,
        details_extractor=lambda view, req, resp, *args, **kwargs: {
            'report_name': 'Student List CSV',
            'filters_applied': req.query_params.dict()
        }
    )
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)


from .serializers import StudentDocumentSerializer # Import StudentDocumentSerializer

class StudentDocumentManagementViewSet(viewsets.ModelViewSet):
    """
    ViewSet for Secretaria/administrative staff to manage student documents.
    Focuses on validating documents by updating their `validation_status` and `notes`.

    **Permissions:** Requires admin user status (or specific 'Secretaria' group).

    **Supported Actions:**
    - `list`: Retrieves a list of student documents. Supports filtering by `validation_status`, `document_type`, and `student` (student ID).
    - `retrieve`: Gets details of a specific student document.
    - `partial_update` (PATCH): Updates the `validation_status` and/or `notes` of a document.
      Refer to `StudentDocumentSerializer` for updatable fields.

    Creation (POST), full update (PUT), and deletion (DELETE) of documents are typically handled
    during pre-registration or other dedicated document upload processes.
    """
    queryset = StudentDocument.objects.all().select_related(
        'student', 'student__user'
    ).order_by('student__user__username', 'document_type')
    serializer_class = StudentDocumentSerializer
    permission_classes = [IsAdminUser] # Or a more specific 'Secretaria' permission
    http_method_names = ['get', 'patch', 'head', 'options'] # Allow only these methods

    # Add filtering for validation_status and document_type
    filterset_fields = ['validation_status', 'document_type', 'student']

    # The StudentDocumentSerializer's update method handles the logic for
    # updating validation_status and notes, and ensures other fields are read-only.
