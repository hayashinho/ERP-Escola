from django.urls import reverse
from django.contrib.auth import get_user_model
from django.contrib.auth.signals import user_logged_in, user_logged_out, user_login_failed
from django.contrib.contenttypes.models import ContentType
from django.test import TestCase, RequestFactory
from django.urls import path # Import path
from rest_framework import status
from rest_framework.test import APITestCase
from django.utils import timezone
from datetime import timedelta

from apps.accounts.models import User as AuthUser # Using the project's User model
from apps.students.models import Student, GradeLevel
from apps.academics.models import SchoolYear, SchoolClass, Enrollment, Announcement
from apps.communications.models import MessageThread, Message # For testing M2M in signals

from apps.auditing.models import AuditLog
from apps.auditing.utils import log_action # For direct testing if needed, and by decorator
from apps.auditing.decorators import audit_view_action
from apps.auditing.signals import MODELS_TO_AUDIT # To check if models are audited

# Mock view for decorator testing
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.utils.translation import gettext_lazy as _


# --- Helper to get client IP, similar to the one in utils ---
def get_test_client_ip(request):
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        ip = x_forwarded_for.split(',')[0]
    else:
        ip = request.META.get('REMOTE_ADDR')
    return ip


# --- Test for Signals ---
class AuditLogSignalTests(TestCase):
    def setUp(self):
        self.user = AuthUser.objects.create_user(username='testuser_audit_signal', password='password', email='asignal@example.com', user_type=AuthUser.USER_TYPE_STUDENT)
        self.factory = RequestFactory()

    def test_user_logged_in_signal(self):
        request = self.factory.get('/fake-login')
        request.user = self.user
        request.META['REMOTE_ADDR'] = '1.2.3.4'

        user_logged_in.send(sender=self.user.__class__, request=request, user=self.user)

        log = AuditLog.objects.latest('timestamp')
        self.assertEqual(log.user, self.user)
        self.assertEqual(log.action_type, AuditLog.ACTION_LOGIN_SUCCESS)
        self.assertEqual(log.ip_address, '1.2.3.4')
        self.assertEqual(log.details.get('username'), self.user.get_username())

    def test_user_login_failed_signal(self):
        request = self.factory.post('/fake-login-fail', {'username': 'attempt_user'})
        request.META['REMOTE_ADDR'] = '1.2.3.5'
        credentials = {'username': 'attempt_user'}

        user_login_failed.send(sender=None, credentials=credentials, request=request)

        log = AuditLog.objects.latest('timestamp')
        self.assertIsNone(log.user)
        self.assertEqual(log.action_type, AuditLog.ACTION_LOGIN_FAILED)
        self.assertEqual(log.ip_address, '1.2.3.5')
        self.assertEqual(log.details.get('attempted_username'), 'attempt_user')

    def test_user_logged_out_signal(self):
        request = self.factory.post('/fake-logout')
        request.user = self.user
        request.META['REMOTE_ADDR'] = '1.2.3.6'

        user_logged_out.send(sender=self.user.__class__, request=request, user=self.user)

        log = AuditLog.objects.latest('timestamp')
        self.assertEqual(log.user, self.user)
        self.assertEqual(log.action_type, AuditLog.ACTION_LOGOUT)
        self.assertEqual(log.ip_address, '1.2.3.6')

    def test_post_save_created_signal(self):
        student_user = AuthUser.objects.create_user(username='new_student_signal', password='password', user_type=AuthUser.USER_TYPE_STUDENT)
        # Ensure student_profile is created if needed by str(student) or other parts
        # UserProfile.objects.create(user=student_user) # If UserProfile is separate and used by str()

        student = Student.objects.create(user=student_user)

        log = AuditLog.objects.filter(
            target_content_type=ContentType.objects.get_for_model(student),
            target_object_id=str(student.pk)
        ).latest('timestamp')

        self.assertEqual(log.action_type, AuditLog.ACTION_CREATED)
        self.assertIsNone(log.user)
        self.assertEqual(log.target_object_repr, str(student))

    def test_post_save_updated_signal(self):
        student_user = AuthUser.objects.create_user(username='update_student_signal', password='password', user_type=AuthUser.USER_TYPE_STUDENT)
        # UserProfile.objects.create(user=student_user)
        student = Student.objects.create(user=student_user)
        AuditLog.objects.all().delete()

        student.registration_status = Student.STATUS_ACTIVE
        student.save(update_fields=['registration_status'])

        log = AuditLog.objects.filter(
            target_content_type=ContentType.objects.get_for_model(student),
            target_object_id=str(student.pk)
        ).latest('timestamp')

        self.assertEqual(log.action_type, AuditLog.ACTION_UPDATED)
        self.assertIsNone(log.user)
        self.assertIn('registration_status', log.details.get('updated_fields', []))

    def test_post_delete_signal(self):
        student_user = AuthUser.objects.create_user(username='delete_student_signal', password='password', user_type=AuthUser.USER_TYPE_STUDENT)
        # UserProfile.objects.create(user=student_user)
        student = Student.objects.create(user=student_user)
        student_pk = str(student.pk)
        student_repr = str(student)
        AuditLog.objects.all().delete()

        student.delete()

        log = AuditLog.objects.filter(
            target_content_type=ContentType.objects.get_for_model(Student),
            target_object_id=student_pk
        ).latest('timestamp')

        self.assertEqual(log.action_type, AuditLog.ACTION_DELETED)
        self.assertIsNone(log.user)
        self.assertEqual(log.target_object_repr, student_repr)


# --- Mock View for Decorator Test ---
_decorated_view_instance = None # To hold the instance for target_object_getter

class MockDecoratedView(APIView):
    permission_classes = [IsAuthenticated]
    student_target = None # Class variable to hold target

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        global _decorated_view_instance
        _decorated_view_instance = self # Store instance for getter

    def get_target_object_method(self, request, *args, **kwargs):
        if 'pk' in kwargs and kwargs['pk'] == '1':
            return MockDecoratedView.student_target
        return None

    def extract_details_method(self, request, response, *args, **kwargs):
        return {"query_params": request.query_params.dict(), "status_code": response.status_code}

    @audit_view_action(
        action_type='TEST_ACTION_SUCCESS',
        target_object_getter=lambda view, req, *a, **kw: view.get_target_object_method(req, *a, **kw),
        details_extractor=lambda view, req, resp, *a, **kw: view.extract_details_method(req, resp, *a, **kw)
    )
    def get(self, request, *args, **kwargs):
        if request.query_params.get("fail_request") == "true":
            return Response({"message": "Failed as requested"}, status=status.HTTP_400_BAD_REQUEST)
        return Response({"message": "Success"}, status=status.HTTP_200_OK)

# --- Test for Decorator ---
class AuditLogDecoratorTests(APITestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = AuthUser.objects.create_user(username='test_decorator_user', password='password', user_type=AuthUser.USER_TYPE_STAFF)
        student_user = AuthUser.objects.create_user(username='student_for_decorator', password='password', user_type=AuthUser.USER_TYPE_STUDENT)
        # UserProfile.objects.create(user=student_user) # If needed for str(student_target)
        MockDecoratedView.student_target = Student.objects.create(user=student_user)


    def setUp(self):
        self.client.force_authenticate(user=self.user)
        from django.urls import path # Local import for test URLconf
        self.urlpatterns = [
            path('mock-decorated-view/', MockDecoratedView.as_view(), name='mock_decorated_view'),
            path('mock-decorated-view/<str:pk>/', MockDecoratedView.as_view(), name='mock_decorated_view_detail')
        ]


    def test_decorator_logs_on_success(self):
        with self.settings(ROOT_URLCONF=__name__):
            url = reverse('mock_decorated_view_detail', kwargs={'pk': '1'}) + "?param=test"
            response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        log = AuditLog.objects.latest('timestamp')
        self.assertEqual(log.user, self.user)
        self.assertEqual(log.action_type, 'TEST_ACTION_SUCCESS')
        self.assertIsNotNone(log.ip_address)
        self.assertEqual(log.target_object, MockDecoratedView.student_target)
        self.assertEqual(log.details['query_params']['param'], 'test')
        self.assertEqual(log.details['status_code'], 200)

    def test_decorator_no_log_on_failure(self):
        initial_log_count = AuditLog.objects.count()
        with self.settings(ROOT_URLCONF=__name__):
            url = reverse('mock_decorated_view') + "?fail_request=true"
            response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(AuditLog.objects.count(), initial_log_count)


# --- Test for AuditLogViewSet ---
class AuditLogViewSetTests(APITestCase):
    @classmethod
    def setUpTestData(cls):
        # Create users first, which might trigger audit logs if User model is audited by signals
        cls.admin_user = AuthUser.objects.create_superuser('auditadmin', 'auditadmin@example.com', 'password', user_type=AuthUser.USER_TYPE_ADMIN)
        cls.other_user = AuthUser.objects.create_user('audituser2', 'audituser2@example.com', 'password', user_type=AuthUser.USER_TYPE_TEACHER)

        # Now clear any audit logs created during user setup
        AuditLog.objects.all().delete()

        # UserProfile.objects.create(user=cls.admin_user) # If needed for str(user)
        # UserProfile.objects.create(user=cls.other_user)

        # Create specific logs for testing
        cls.log1_user1 = AuditLog.objects.create(user=cls.admin_user, action_type=AuditLog.ACTION_LOGIN_SUCCESS, ip_address="192.168.0.1", details={"test":1})
        cls.log2_user2 = AuditLog.objects.create(user=cls.other_user, action_type=AuditLog.ACTION_CREATED, target_object=cls.other_user, details={"field":"X"}) # target_object is other_user
        cls.log3_system = AuditLog.objects.create(action_type=AuditLog.ACTION_EXPORTED, ip_address="10.0.0.1", details={"report":"students"})

        # Ensure varied timestamps for ordering tests
        cls.log1_user1.timestamp = timezone.now() - timedelta(days=2)
        cls.log1_user1.save()
        cls.log2_user2.timestamp = timezone.now() - timedelta(days=1)
        cls.log2_user2.save()
        # log3_system is latest

        cls.list_url = reverse('auditing:auditlog-list')

    def setUp(self):
        self.client.force_authenticate(user=self.admin_user)

    def test_admin_can_list_logs(self):
        response = self.client.get(self.list_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        # No pagination by default, response.data is the list
        self.assertEqual(len(response.data), 3)
        self.assertEqual(response.data[0]['id'], self.log3_system.id)

    def test_non_admin_cannot_list_logs(self):
        self.client.force_authenticate(user=self.other_user)
        response = self.client.get(self.list_url)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_filter_by_username(self):
        response = self.client.get(self.list_url, {'user__username': self.admin_user.username})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.data # No pagination
        self.assertEqual(len(data), 1)
        self.assertEqual(data[0]['user']['username'], self.admin_user.username)

    def test_filter_by_action_type(self):
        response = self.client.get(self.list_url, {'action_type': AuditLog.ACTION_CREATED})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.data # No pagination
        self.assertEqual(len(data), 1)
        self.assertEqual(data[0]['action_type'], AuditLog.ACTION_CREATED)

    def test_filter_by_timestamp_range(self):
        # Test with a range that should capture log2_user2 and log3_system
        # log1 is 2 days old, log2 is 1 day old, log3 is current
        after_date = (timezone.now() - timedelta(days=1, hours=12)).isoformat()
        before_date = (timezone.now() + timedelta(hours=1)).isoformat() # Ensure current is included

        response = self.client.get(self.list_url, {'timestamp__gte': after_date, 'timestamp__lte': before_date})
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
        data = response.data # No pagination
        self.assertEqual(len(data), 2)
        log_ids = {item['id'] for item in data}
        self.assertIn(self.log2_user2.id, log_ids)
        self.assertIn(self.log3_system.id, log_ids)


    def test_search_logs(self):
        response = self.client.get(self.list_url, {'search': self.other_user.username})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.data # No pagination
        self.assertEqual(len(data), 1)
        self.assertEqual(data[0]['id'], self.log2_user2.id)

        response = self.client.get(self.list_url, {'search': 'students'})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.data # No pagination
        self.assertEqual(len(data), 1)
        self.assertEqual(data[0]['id'], self.log3_system.id)


    def test_ordering_logs(self):
        response = self.client.get(self.list_url, {'ordering': 'timestamp'}) # Oldest first
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.data # No pagination
        self.assertEqual(data[0]['id'], self.log1_user1.id)

    def test_auditlog_api_is_readonly(self):
        detail_url = reverse('auditing:auditlog-detail', kwargs={'pk': self.log1_user1.pk})

        response = self.client.post(self.list_url, {"action_type": "HACK", "details":{}}, format='json')
        self.assertEqual(response.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)

        response = self.client.put(detail_url, {"action_type": "HACK_PUT", "details":{}}, format='json')
        self.assertEqual(response.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)

        response = self.client.patch(detail_url, {"details":{"new":1}}, format='json')
        self.assertEqual(response.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)

        response = self.client.delete(detail_url)
        self.assertEqual(response.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)

# This is needed to make Django's test runner find URLs for the mock view
# This needs to be at the module level for Django's URL resolver overriding via settings to work
urlpatterns = [
    path('mock-decorated-view/', MockDecoratedView.as_view(), name='mock_decorated_view'),
    path('mock-decorated-view/<str:pk>/', MockDecoratedView.as_view(), name='mock_decorated_view_detail'),
]
