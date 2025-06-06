from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase
from apps.accounts.models import User

class UserEmailManagementViewSetTests(APITestCase):
    def setUp(self):
        # Create users for testing
        self.admin_user = User.objects.create_user(username='admin', email='admin@example.com', password='password123', user_type=User.UserType.ADMIN, is_staff=True)
        self.student_user = User.objects.create_user(username='student', email='student@example.com', password='password123', user_type=User.UserType.STUDENT)
        self.staff_user = User.objects.create_user(username='staff', email='staff@example.com', password='password123', user_type=User.UserType.STAFF)
        self.parent_user = User.objects.create_user(username='parent', email='parent@example.com', password='password123', user_type=User.UserType.PARENT)


        # URL for the viewset
        self.list_url = reverse('user-email-management-list')

    def get_detail_url(self, user_id):
        return reverse('user-email-management-detail', kwargs={'pk': user_id})

    # Test Listing Users
    def test_list_users_as_admin(self):
        self.client.force_authenticate(user=self.admin_user)
        response = self.client.get(self.list_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 4) # Admin, Student, Staff, Parent

    def test_list_users_as_non_admin(self):
        self.client.force_authenticate(user=self.student_user)
        response = self.client.get(self.list_url)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    # Test Filtering Users by user_type
    def test_filter_users_by_student_type_as_admin(self):
        self.client.force_authenticate(user=self.admin_user)
        response = self.client.get(self.list_url, {'user_type': 'STUDENT'})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]['username'], self.student_user.username)

    def test_filter_users_by_staff_type_as_admin(self):
        self.client.force_authenticate(user=self.admin_user)
        response = self.client.get(self.list_url, {'user_type': 'STAFF'})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]['username'], self.staff_user.username)

    def test_filter_users_by_parent_type_as_admin(self):
        self.client.force_authenticate(user=self.admin_user)
        response = self.client.get(self.list_url, {'user_type': 'PARENT'})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]['username'], self.parent_user.username)

    # Test Retrieving a Single User
    def test_retrieve_single_user_as_admin(self):
        self.client.force_authenticate(user=self.admin_user)
        response = self.client.get(self.get_detail_url(self.student_user.id))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['username'], self.student_user.username)
        self.assertEqual(response.data['email'], self.student_user.email)

    def test_retrieve_single_user_as_non_admin(self):
        self.client.force_authenticate(user=self.student_user)
        response = self.client.get(self.get_detail_url(self.staff_user.id))
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    # Test Updating User's Email
    def test_update_user_email_as_admin(self):
        self.client.force_authenticate(user=self.admin_user)
        new_email = 'newstudentemail@example.com'
        data = {'email': new_email}
        response = self.client.patch(self.get_detail_url(self.student_user.id), data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.student_user.refresh_from_db()
        self.assertEqual(self.student_user.email, new_email)
        self.assertEqual(response.data['email'], new_email)

    def test_update_user_email_as_non_admin(self):
        self.client.force_authenticate(user=self.student_user)
        new_email = 'newstaffemail@example.com'
        data = {'email': new_email}
        response = self.client.patch(self.get_detail_url(self.staff_user.id), data)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.staff_user.refresh_from_db()
        self.assertNotEqual(self.staff_user.email, new_email)

    # Test Only Email Can Be Updated
    def test_only_email_can_be_updated_as_admin(self):
        self.client.force_authenticate(user=self.admin_user)
        original_username = self.student_user.username
        original_first_name = self.student_user.first_name
        new_email = 'anothernewemail@example.com'
        data = {
            'email': new_email,
            'username': 'cannotchangeusername',
            'first_name': 'CannotChangeFirstName',
            'user_type': User.UserType.STAFF # Try to change user_type
        }
        response = self.client.put(self.get_detail_url(self.student_user.id), data) # PUT to send all fields
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.student_user.refresh_from_db()
        self.assertEqual(self.student_user.email, new_email)
        self.assertEqual(self.student_user.username, original_username) # Should not change
        self.assertEqual(self.student_user.first_name, original_first_name) # Should not change
        self.assertEqual(self.student_user.user_type, User.UserType.STUDENT) # Should not change
        self.assertEqual(response.data['email'], new_email)
        self.assertEqual(response.data['username'], original_username)
        self.assertEqual(response.data['user_type'], User.UserType.STUDENT.upper())


    # Test Permission Enforcement (already covered by individual tests, but an explicit one is good)
    def test_unauthenticated_access_list(self):
        self.client.logout()
        response = self.client.get(self.list_url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED) # Or 403 if default is DenyAny

    def test_unauthenticated_access_detail(self):
        self.client.logout()
        response = self.client.get(self.get_detail_url(self.student_user.id))
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED) # Or 403

    def test_unauthenticated_access_update(self):
        self.client.logout()
        new_email = 'unauth@example.com'
        data = {'email': new_email}
        response = self.client.patch(self.get_detail_url(self.student_user.id), data)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED) # Or 403
        self.student_user.refresh_from_db()
        self.assertNotEqual(self.student_user.email, new_email)


class UserManagementViewSetTests(APITestCase):
    def setUp(self):
        self.admin_user = User.objects.create_superuser(username='admin_mgr', email='admin_mgr@example.com', password='password123', user_type=User.USER_TYPE_ADMIN)
        self.staff_user = User.objects.create_user(username='staff_mgr', email='staff_mgr@example.com', password='password123', user_type=User.USER_TYPE_STAFF, is_staff=True)
        self.regular_user = User.objects.create_user(username='regular_mgr', email='regular_mgr@example.com', password='password123', user_type=User.USER_TYPE_PARENT)

        self.user_to_manage = User.objects.create_user(username='testuser1', email='test1@example.com', password='password123', user_type=User.USER_TYPE_TEACHER)

        self.list_create_url = reverse('user-management-list')
        self.detail_url = reverse('user-management-detail', kwargs={'pk': self.user_to_manage.pk})

        # Authenticate as admin user by default for most tests
        self.client.force_authenticate(user=self.admin_user)

    def test_admin_can_list_users(self):
        response = self.client.get(self.list_create_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(len(response.data) >= 4) # admin, staff, regular, user_to_manage

    def test_admin_can_create_user(self):
        payload = {
            'username': 'newteacher',
            'email': 'newteacher@example.com',
            'password': 'newpassword123',
            'user_type': User.USER_TYPE_TEACHER,
            'first_name': 'New',
            'last_name': 'Teacher'
        }
        response = self.client.post(self.list_create_url, payload)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['username'], 'newteacher')
        self.assertEqual(response.data['user_type'], User.USER_TYPE_TEACHER)

        created_user = User.objects.get(username='newteacher')
        self.assertTrue(created_user.check_password('newpassword123'))
        self.assertNotIn('password', response.data) # Password should not be in response

    def test_admin_can_retrieve_user(self):
        response = self.client.get(self.detail_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['username'], self.user_to_manage.username)
        self.assertNotIn('password', response.data)

    def test_admin_can_update_user(self):
        payload = {
            'email': 'updated_test1@example.com',
            'first_name': 'UpdatedFirst',
            'last_name': 'UpdatedLast',
            'user_type': User.USER_TYPE_STAFF,
            'is_active': False,
            'is_staff': True
        }
        response = self.client.patch(self.detail_url, payload)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        self.user_to_manage.refresh_from_db()
        self.assertEqual(self.user_to_manage.email, 'updated_test1@example.com')
        self.assertEqual(self.user_to_manage.first_name, 'UpdatedFirst')
        self.assertEqual(self.user_to_manage.user_type, User.USER_TYPE_STAFF)
        self.assertFalse(self.user_to_manage.is_active)
        self.assertTrue(self.user_to_manage.is_staff)

    def test_admin_cannot_update_username(self):
        original_username = self.user_to_manage.username
        payload = {'username': 'cannotchange_username'}
        response = self.client.patch(self.detail_url, payload)
        # Username is read-only, so it should be ignored, request still 200 OK
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.user_to_manage.refresh_from_db()
        self.assertEqual(self.user_to_manage.username, original_username)
        self.assertEqual(response.data['username'], original_username)


    def test_password_not_updated_via_general_patch(self):
        original_password_hash = self.user_to_manage.password
        payload = {'password': 'newattemptedpassword123'}
        response = self.client.patch(self.detail_url, payload)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.user_to_manage.refresh_from_db()
        self.assertEqual(self.user_to_manage.password, original_password_hash) # Password should not change

    def test_non_admin_cannot_access_usermanagement_viewset(self):
        self.client.force_authenticate(user=self.regular_user)
        response = self.client.get(self.list_create_url)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

        response_detail = self.client.get(self.detail_url)
        self.assertEqual(response_detail.status_code, status.HTTP_403_FORBIDDEN)

    def test_filter_users_by_username(self):
        response = self.client.get(self.list_create_url, {'username': self.user_to_manage.username})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]['username'], self.user_to_manage.username)

    def test_filter_users_by_email(self):
        response = self.client.get(self.list_create_url, {'email': self.user_to_manage.email})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]['email'], self.user_to_manage.email)

    def test_filter_users_by_user_type(self):
        response = self.client.get(self.list_create_url, {'user_type': User.USER_TYPE_TEACHER})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        # At least user_to_manage should be found
        self.assertTrue(len(response.data) >= 1)
        for user_data in response.data:
            if user_data['id'] == self.user_to_manage.id:
                self.assertEqual(user_data['user_type'], User.USER_TYPE_TEACHER)
                break
        else:
            self.fail("user_to_manage not found in filtered list by user_type")

    def test_filter_users_by_is_active(self):
        # Make one user inactive
        self.user_to_manage.is_active = False
        self.user_to_manage.save()

        response = self.client.get(self.list_create_url, {'is_active': 'false'})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        found = False
        for user_data in response.data:
            if user_data['id'] == self.user_to_manage.id:
                self.assertFalse(user_data['is_active'])
                found = True
                break
        self.assertTrue(found, "Inactive user_to_manage not found by filter.")

        response_active = self.client.get(self.list_create_url, {'is_active': 'true'})
        self.assertEqual(response_active.status_code, status.HTTP_200_OK)
        for user_data in response_active.data:
            self.assertTrue(user_data['is_active'])
            self.assertNotEqual(user_data['id'], self.user_to_manage.id) # Ensure our inactive user is not here
