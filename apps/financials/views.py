from decimal import Decimal
from django.db import transaction
from django.utils import timezone # Importar timezone
from rest_framework import viewsets, status
from rest_framework.permissions import IsAuthenticated, IsAdminUser
from rest_framework.response import Response
from rest_framework.decorators import action # Importar action
from django_filters.rest_framework import DjangoFilterBackend, FilterSet, DateFromToRangeFilter
from django_filters import CharFilter

from apps.accounts.models import User
from apps.students.models import Student, StudentParentAssociation
from .models import Fee, Payment, FeeEditLog
from .serializers import FeeSerializer, PaymentSerializer, FeeWriteSerializer, PaymentWriteSerializer


class BaseMyFinancialDataViewSet(viewsets.ReadOnlyModelViewSet):
    permission_classes = [IsAuthenticated]

    def _filter_queryset_by_user_role(self, initial_queryset, student_related_field_lookup):
        user = self.request.user
        if not student_related_field_lookup:
            if user.is_staff or user.is_superuser:
                return initial_queryset
            return initial_queryset.none()
        if user.user_type == User.USER_TYPE_STUDENT:
            try:
                return initial_queryset.filter(**{student_related_field_lookup: user.pk})
            except Student.DoesNotExist:
                return initial_queryset.none()
        elif user.user_type == User.USER_TYPE_PARENT:
            try:
                student_pks = StudentParentAssociation.objects.filter(
                    parent_user=user
                ).values_list('student__user_id', flat=True)
                if not student_pks:
                    return initial_queryset.none()
                lookup_with_in = f"{student_related_field_lookup}_id__in"
                if student_related_field_lookup.endswith('__student'):
                    lookup_with_in = f"{student_related_field_lookup}_id__in"
                return initial_queryset.filter(**{lookup_with_in: list(student_pks)})
            except Exception:
                return initial_queryset.none()
        else:
            if user.is_staff or user.is_superuser:
                return initial_queryset
            return initial_queryset.none()


class FeeFilter(FilterSet):
    due_date = DateFromToRangeFilter()
    status = CharFilter(field_name='status')
    class Meta:
        model = Fee
        fields = ['status', 'due_date']


class MyFeesViewSet(BaseMyFinancialDataViewSet):
    serializer_class = FeeSerializer
    filterset_class = FeeFilter
    def get_queryset(self):
        initial_queryset = Fee.objects.select_related('student__user', 'school_year').order_by('-due_date')
        return self._filter_queryset_by_user_role(initial_queryset, student_related_field_lookup='student')


class PaymentFilter(FilterSet):
    payment_date = DateFromToRangeFilter()
    payment_method = CharFilter(field_name='payment_method')
    class Meta:
        model = Payment
        fields = ['payment_date', 'payment_method']


class MyPaymentsViewSet(BaseMyFinancialDataViewSet):
    serializer_class = PaymentSerializer
    filterset_class = PaymentFilter
    def get_queryset(self):
        initial_queryset = Payment.objects.select_related('fee__student__user', 'fee__school_year', 'confirmed_by').order_by('-payment_date')
        return self._filter_queryset_by_user_role(initial_queryset, student_related_field_lookup='fee__student')


class FeeManagementViewSet(viewsets.ModelViewSet):
    queryset = Fee.objects.select_related('student__user', 'school_year').order_by('-due_date')
    permission_classes = [IsAuthenticated, IsAdminUser]
    filterset_class = FeeFilter

    def get_serializer_class(self):
        if self.action in ['list', 'retrieve', 'regenerate_slip', 'overdue_report']: # Adicionado actions para usar FeeSerializer
            return FeeSerializer
        return FeeWriteSerializer

    def perform_update(self, serializer):
        original_fee = self.get_object()
        validated_data = serializer.validated_data
        edit_reason = validated_data.pop('edit_reason', None)
        if not edit_reason:
            edit_reason = self.request.data.get('edit_reason', 'Alteração via painel administrativo.')

        if 'amount' in validated_data and original_fee.amount != validated_data['amount']:
            FeeEditLog.objects.create(
                fee=original_fee, edited_by=self.request.user, field_changed='amount',
                previous_value=str(original_fee.amount), new_value=str(validated_data['amount']),
                reason=edit_reason
            )
        if 'due_date' in validated_data and original_fee.due_date != validated_data['due_date']:
            FeeEditLog.objects.create(
                fee=original_fee, edited_by=self.request.user, field_changed='due_date',
                previous_value=str(original_fee.due_date), new_value=str(validated_data['due_date']),
                reason=edit_reason
            )
        if 'status' in validated_data and original_fee.status != validated_data['status']:
            FeeEditLog.objects.create(
                fee=original_fee, edited_by=self.request.user, field_changed='status',
                previous_value=original_fee.get_status_display(),
                new_value=dict(Fee.STATUS_CHOICES).get(validated_data['status'], validated_data['status']),
                reason=edit_reason
            )
        super().perform_update(serializer)

    @action(detail=True, methods=['get'], url_path='regenerate-slip')
    def regenerate_slip(self, request, pk=None):
        """
        Retorna os dados de uma taxa específica para permitir a regeneração de um boleto.
        A lógica de geração do boleto em si seria externa ou em outra função.
        """
        fee = self.get_object()
        serializer = self.get_serializer(fee) # Usa FeeSerializer conforme get_serializer_class
        return Response({'message': 'Dados da taxa para regeneração do boleto.', 'fee': serializer.data})

    @action(detail=False, methods=['get'], url_path='overdue-report')
    def overdue_report(self, request):
        """
        Retorna um relatório paginado de taxas vencidas e não totalmente pagas.
        """
        overdue_fees_queryset = Fee.objects.filter(
            status__in=[Fee.STATUS_PENDING, Fee.STATUS_OVERDUE, Fee.STATUS_PARTIALLY_PAID],
            due_date__lt=timezone.now().date()
        ).select_related('student__user', 'school_year').order_by('due_date', 'student')

        # Aplicar filtros existentes, se houver (ex: ?status=PENDING)
        # A classe FeeFilter já está definida para este ViewSet
        filtered_queryset = self.filter_queryset(overdue_fees_queryset)

        page = self.paginate_queryset(filtered_queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)

        serializer = self.get_serializer(filtered_queryset, many=True)
        return Response(serializer.data)


class PaymentManagementViewSet(viewsets.ModelViewSet):
    queryset = Payment.objects.select_related(
        'fee__student__user', 'fee__school_year', 'confirmed_by'
    ).order_by('-payment_date')
    permission_classes = [IsAuthenticated, IsAdminUser]
    filterset_class = PaymentFilter

    def get_serializer_class(self):
        if self.action in ['list', 'retrieve']:
            return PaymentSerializer
        return PaymentWriteSerializer

    @transaction.atomic
    def perform_create(self, serializer):
        payment = serializer.save(confirmed_by=self.request.user)
        fee = payment.fee
        current_amount_paid = fee.amount_paid if fee.amount_paid is not None else Decimal('0.00')
        fee.amount_paid = current_amount_paid + payment.amount_paid
        if fee.payment_date is None or payment.payment_date > fee.payment_date:
            fee.payment_date = payment.payment_date

        if fee.amount_paid >= fee.total_value:
            fee.status = Fee.STATUS_PAID
        elif fee.amount_paid > Decimal('0.00'):
            fee.status = Fee.STATUS_PARTIALLY_PAID
        fee.save()
