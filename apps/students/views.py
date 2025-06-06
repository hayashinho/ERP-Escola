from django.db import transaction
from django.shortcuts import get_object_or_404 # Para obter objetos ou retornar 404
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status, serializers, viewsets # Adicionado viewsets
from rest_framework.permissions import AllowAny, IsAdminUser # Adicionado IsAdminUser
from rest_framework.decorators import action # Adicionado action
from rest_framework.parsers import MultiPartParser, FormParser

from apps.accounts.serializers import UserRegistrationSerializer
from apps.accounts.models import UserProfile, User
from apps.students.models import Student, GradeLevel, StudentParentAssociation, StudentDocument
from apps.students.serializers import StudentSerializer # Importar StudentSerializer

class PreRegistrationAPIView(APIView):
    """
    API View para o processo de pré-cadastro de alunos.
    Esta view será acessível publicamente.
    Espera um payload multipart/form-data com as seguintes chaves principais:
    - "parent_user_data" (JSON string ou campos de formulário prefixados): Dados para User do responsável.
    - "parent_profile_data" (JSON string ou campos de formulário prefixados): Dados para UserProfile do responsável.
    - "parent_relationship_type": Tipo de relação do responsável.
    - "student_user_data" (JSON string ou campos de formulário prefixados): Dados para User do aluno.
    - "student_profile_data" (JSON string ou campos de formulário prefixados): Dados para UserProfile do aluno.
    - "student_data" (JSON string ou campos de formulário prefixados): Dados para Student.
    - "document_types" (lista): Lista dos tipos de documentos enviados.
    - "document_files" (lista de arquivos): Lista dos arquivos de documentos.
    """
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
    ViewSet para listar e recuperar registros de alunos pendentes de validação.
    Permite que administradores aprovem ou rejeitem esses registros.
    """
    serializer_class = StudentSerializer
    permission_classes = [IsAdminUser] # Apenas usuários admin/staff podem acessar

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
        Aprova o registro de um aluno.
        Muda o status para 'ACTIVE' e pode definir a data de matrícula.
        """
        student = get_object_or_404(Student, pk=pk)
        if student.registration_status != Student.STATUS_PENDING_VALIDATION:
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
        """
        student = get_object_or_404(Student, pk=pk)
        if student.registration_status != Student.STATUS_PENDING_VALIDATION:
            return Response(
                {'error': 'Este aluno não está pendente de validação.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        rejection_reason = request.data.get('reason')
        if not rejection_reason:
            return Response(
                {'error': 'O motivo da rejeição é obrigatório.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        student.registration_status = Student.STATUS_REJECTED
        student.rejection_reason = rejection_reason # Salva o motivo no novo campo
        student.save()
        return Response({'status': 'success', 'message': f'Matrícula do aluno {student} rejeitada.'})
