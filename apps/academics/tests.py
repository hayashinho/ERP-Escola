from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase
from apps.accounts.models import User # Reverted import
from apps.students.models import Student, GradeLevel as StudentGradeLevel # Reverted import
from apps.academics.models import SchoolYear, SchoolClass, Enrollment, Announcement # Import Announcement
from django.utils import timezone

class EnrollmentManagementTests(APITestCase):
    def setUp(self):
        # Users
        self.admin_user = User.objects.create_user(username='admin_enroll_test', email='admin_enroll@example.com', password='password123', user_type=User.USER_TYPE_ADMIN, is_staff=True)
        self.regular_user = User.objects.create_user(username='regular_enroll_test', email='regular_enroll@example.com', password='password123', user_type=User.USER_TYPE_PARENT)

        # School Year
        self.active_school_year = SchoolYear.objects.create(
            year=timezone.now().year,
            start_date=timezone.now().date() - timezone.timedelta(days=30),
            end_date=timezone.now().date() + timezone.timedelta(days=300),
            is_active=True
        )
        self.inactive_school_year = SchoolYear.objects.create(
            year=timezone.now().year - 1,
            start_date=(timezone.now().date() - timezone.timedelta(days=30)) - timezone.timedelta(days=365),
            end_date=(timezone.now().date() + timezone.timedelta(days=300)) - timezone.timedelta(days=365),
            is_active=False
        )

        # Student Grade Level (from students app)
        self.student_grade_level = StudentGradeLevel.objects.create(name="10th Grade", order_in_sequence=10)

        # School Class in Active Year
        self.school_class_active_year = SchoolClass.objects.create(
            name="Class A",
            school_year=self.active_school_year,
            grade_level=self.student_grade_level
        )
        # School Class in Inactive Year
        self.school_class_inactive_year = SchoolClass.objects.create(
            name="Class B",
            school_year=self.inactive_school_year,
            grade_level=self.student_grade_level
        )
        self.another_active_school_class = SchoolClass.objects.create(
            name="Class C - Active",
            school_year=self.active_school_year, # Active year
            grade_level=self.student_grade_level # Same grade level, different class
        )

        # Students
        self.active_student_user = User.objects.create_user(username='student_active', email='s_active@example.com', password='password123', user_type=User.USER_TYPE_STUDENT)
        self.active_student = Student.objects.create(user=self.active_student_user, grade_level_pretended=self.student_grade_level, registration_status=Student.STATUS_ACTIVE)

        self.pending_student_user = User.objects.create_user(username='student_pending', email='s_pending@example.com', password='password123', user_type=User.USER_TYPE_STUDENT)
        self.pending_student = Student.objects.create(user=self.pending_student_user, grade_level_pretended=self.student_grade_level, registration_status=Student.STATUS_PENDING_VALIDATION)

        self.other_active_student_user = User.objects.create_user(username='student_other_active', email='s_other@example.com', password='password123', user_type=User.USER_TYPE_STUDENT)
        self.other_active_student = Student.objects.create(user=self.other_active_student_user, grade_level_pretended=self.student_grade_level, registration_status=Student.STATUS_ACTIVE)


        # Enrollment URL
        self.enrollments_url = reverse('academics:enrollment-list')

    def get_enrollment_detail_url(self, enrollment_id):
        return reverse('academics:enrollment-detail', kwargs={'pk': enrollment_id})

    # --- Test Enrollment Creation ---
    def test_admin_create_enrollment_success(self):
        self.client.force_authenticate(user=self.admin_user)
        payload = {
            'student': self.active_student.pk,
            'school_class': self.school_class_active_year.pk
        }
        response = self.client.post(self.enrollments_url, payload)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Enrollment.objects.count(), 1)
        enrollment = Enrollment.objects.first()
        self.assertEqual(enrollment.student, self.active_student)
        self.assertEqual(enrollment.school_class, self.school_class_active_year)
        self.assertEqual(enrollment.status, Enrollment.STATUS_ACTIVE) # Default status

    def test_admin_create_enrollment_inactive_student(self):
        self.client.force_authenticate(user=self.admin_user)
        payload = {
            'student': self.pending_student.pk,
            'school_class': self.school_class_active_year.pk
        }
        response = self.client.post(self.enrollments_url, payload)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('student', response.data) # Check if error is related to student field

    def test_admin_create_enrollment_class_in_inactive_year(self):
        self.client.force_authenticate(user=self.admin_user)
        payload = {
            'student': self.active_student.pk,
            'school_class': self.school_class_inactive_year.pk
        }
        response = self.client.post(self.enrollments_url, payload)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('school_class', response.data)

    def test_admin_create_enrollment_duplicate_active_enrollment_same_year(self):
        self.client.force_authenticate(user=self.admin_user)
        # First enrollment (successful)
        Enrollment.objects.create(student=self.active_student, school_class=self.school_class_active_year, status=Enrollment.STATUS_ACTIVE)

        # Attempt to enroll same student in another class in the same active year
        another_class_same_year = SchoolClass.objects.create(
            name="Class C",
            school_year=self.active_school_year, # Same active year
            grade_level=self.student_grade_level
        )
        payload = {
            'student': self.active_student.pk,
            'school_class': another_class_same_year.pk
        }
        response = self.client.post(self.enrollments_url, payload)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        # Check for the specific validation error from the serializer
        self.assertTrue(any("student is already actively enrolled" in str(error) for error_list in response.data.values() for error in error_list))


    def test_regular_user_cannot_create_enrollment(self):
        self.client.force_authenticate(user=self.regular_user)
        payload = {
            'student': self.active_student.pk,
            'school_class': self.school_class_active_year.pk
        }
        response = self.client.post(self.enrollments_url, payload)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    # --- Test Enrollment Update (Status) ---
    def test_admin_update_enrollment_status(self):
        self.client.force_authenticate(user=self.admin_user)
        enrollment = Enrollment.objects.create(student=self.active_student, school_class=self.school_class_active_year)

        payload = {'status': Enrollment.STATUS_COMPLETED}
        response = self.client.patch(self.get_enrollment_detail_url(enrollment.id), payload)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        enrollment.refresh_from_db()
        self.assertEqual(enrollment.status, Enrollment.STATUS_COMPLETED)

    def test_admin_cannot_change_student_or_class_on_update(self):
        self.client.force_authenticate(user=self.admin_user)
        enrollment = Enrollment.objects.create(student=self.active_student, school_class=self.school_class_active_year)

        payload = {
            'status': Enrollment.STATUS_DROPPED_OUT,
            'student': self.other_active_student.pk, # Attempt to change student
            'school_class': self.another_active_school_class.pk # Attempt to change to a VALID class
        }
        response = self.client.patch(self.get_enrollment_detail_url(enrollment.id), payload)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        # DRF might stop at the first error in the validate() method or combine field errors.
        # We expect an error about 'student' or 'school_class' field change attempt.
        # The current serializer logic raises for 'student' first if both are attempted.
        self.assertTrue('student' in response.data or 'school_class' in response.data)
        if 'student' in response.data:
            self.assertEqual(response.data['student'][0].code, 'invalid') # Specific code for "cannot change"
        if 'school_class' in response.data: # This might not be reached if 'student' error was raised
             self.assertEqual(response.data['school_class'][0].code, 'invalid')


        enrollment.refresh_from_db()
        # Status should not have changed because student/class change is disallowed
        self.assertNotEqual(enrollment.status, Enrollment.STATUS_DROPPED_OUT)
        self.assertEqual(enrollment.student, self.active_student)
        self.assertEqual(enrollment.school_class, self.school_class_active_year)

    def test_regular_user_cannot_update_enrollment_status(self):
        self.client.force_authenticate(user=self.regular_user)
        enrollment = Enrollment.objects.create(student=self.active_student, school_class=self.school_class_active_year)
        payload = {'status': Enrollment.STATUS_COMPLETED}
        response = self.client.patch(self.get_enrollment_detail_url(enrollment.id), payload)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    # --- Test Enrollment Filtering ---
    def test_filter_enrollments_by_student(self):
        self.client.force_authenticate(user=self.admin_user)
        Enrollment.objects.create(student=self.active_student, school_class=self.school_class_active_year)
        Enrollment.objects.create(student=self.other_active_student, school_class=self.school_class_active_year)

        response = self.client.get(self.enrollments_url, {'student': self.active_student.pk})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]['student_details']['user'], self.active_student.user.pk)

    def test_filter_enrollments_by_school_class(self):
        self.client.force_authenticate(user=self.admin_user)
        class_c = SchoolClass.objects.create(name="Class C", school_year=self.active_school_year, grade_level=self.student_grade_level)
        Enrollment.objects.create(student=self.active_student, school_class=self.school_class_active_year)
        Enrollment.objects.create(student=self.other_active_student, school_class=class_c)

        response = self.client.get(self.enrollments_url, {'school_class': class_c.pk})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]['school_class_details']['id'], class_c.pk)

    def test_filter_enrollments_by_status(self):
        self.client.force_authenticate(user=self.admin_user)
        Enrollment.objects.create(student=self.active_student, school_class=self.school_class_active_year, status=Enrollment.STATUS_ACTIVE)
        Enrollment.objects.create(student=self.other_active_student, school_class=self.school_class_active_year, status=Enrollment.STATUS_COMPLETED)

        response = self.client.get(self.enrollments_url, {'status': Enrollment.STATUS_COMPLETED})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]['status'], Enrollment.STATUS_COMPLETED)

    def test_filter_enrollments_by_school_year(self):
        self.client.force_authenticate(user=self.admin_user)
        Enrollment.objects.create(student=self.active_student, school_class=self.school_class_active_year) # Active year
        Enrollment.objects.create(student=self.other_active_student, school_class=self.school_class_inactive_year) # Inactive year

        response = self.client.get(self.enrollments_url, {'school_class__school_year': self.active_school_year.pk})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]['school_class_details']['school_year_str'], str(self.active_school_year.year))

        response_year_direct = self.client.get(self.enrollments_url, {'school_class__school_year__year': self.active_school_year.year})
        self.assertEqual(response_year_direct.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response_year_direct.data), 1)
        self.assertEqual(response_year_direct.data[0]['school_class_details']['school_year_str'], str(self.active_school_year.year))

    # --- Test Enrollment Deletion (If allowed) ---
    def test_admin_can_delete_enrollment(self):
        self.client.force_authenticate(user=self.admin_user)
        enrollment = Enrollment.objects.create(student=self.active_student, school_class=self.school_class_active_year)

        response = self.client.delete(self.get_enrollment_detail_url(enrollment.id))
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertEqual(Enrollment.objects.count(), 0)

    def test_regular_user_cannot_delete_enrollment(self):
        self.client.force_authenticate(user=self.regular_user)
        enrollment = Enrollment.objects.create(student=self.active_student, school_class=self.school_class_active_year)

        response = self.client.delete(self.get_enrollment_detail_url(enrollment.id))
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(Enrollment.objects.count(), 1)


class BatchReenrollmentTests(APITestCase):
    def setUp(self):
        self.admin_user = User.objects.create_user(username='admin_reenroll', email='admin_reenroll@example.com', password='password123', user_type=User.USER_TYPE_ADMIN, is_staff=True)

        # School Years
        self.year1 = SchoolYear.objects.create(year=2023, start_date='2023-01-15', end_date='2023-12-15', is_active=False)
        self.year2 = SchoolYear.objects.create(year=2024, start_date='2024-01-15', end_date='2024-12-15', is_active=True) # Target year for re-enrollment

        # Grade Levels (using StudentGradeLevel from students.models)
        self.grade1 = StudentGradeLevel.objects.create(name="Grade 1", order_in_sequence=1)
        self.grade2 = StudentGradeLevel.objects.create(name="Grade 2", order_in_sequence=2)
        self.last_grade = StudentGradeLevel.objects.create(name="Last Grade", order_in_sequence=3) # A terminal grade

        # School Classes
        self.class_g1_y1 = SchoolClass.objects.create(name="G1-A Y1", school_year=self.year1, grade_level=self.grade1)
        self.class_g2_y1 = SchoolClass.objects.create(name="G2-A Y1", school_year=self.year1, grade_level=self.grade2)

        self.class_g2_y2 = SchoolClass.objects.create(name="G2-A Y2", school_year=self.year2, grade_level=self.grade2)
        self.class_g3_y2 = SchoolClass.objects.create(name="G3-A Y2", school_year=self.year2, grade_level=self.last_grade) # For students moving to last_grade

        # Students
        s1_user = User.objects.create_user(username='student1_br', email='s1_br@example.com', password='p', user_type=User.USER_TYPE_STUDENT)
        self.student1 = Student.objects.create(user=s1_user, registration_status=Student.STATUS_ACTIVE, grade_level_pretended=self.grade1)

        s2_user = User.objects.create_user(username='student2_br', email='s2_br@example.com', password='p', user_type=User.USER_TYPE_STUDENT)
        self.student2 = Student.objects.create(user=s2_user, registration_status=Student.STATUS_ACTIVE, grade_level_pretended=self.grade2)

        s3_user = User.objects.create_user(username='student3_grad', email='s3_grad@example.com', password='p', user_type=User.USER_TYPE_STUDENT)
        self.student3_graduating = Student.objects.create(user=s3_user, registration_status=Student.STATUS_ACTIVE, grade_level_pretended=self.last_grade)

        # Initial Enrollments in Year 1
        self.enrollment1_y1 = Enrollment.objects.create(student=self.student1, school_class=self.class_g1_y1, status=Enrollment.STATUS_ACTIVE)
        self.enrollment2_y1 = Enrollment.objects.create(student=self.student2, school_class=self.class_g2_y1, status=Enrollment.STATUS_ACTIVE)
        self.enrollment3_y1 = Enrollment.objects.create(student=self.student3_graduating, school_class=SchoolClass.objects.create(name="LG-A Y1", school_year=self.year1, grade_level=self.last_grade), status=Enrollment.STATUS_ACTIVE)

        self.batch_reenroll_url = reverse('academics:schoolyear-batch-reenroll', kwargs={'pk': self.year1.pk})
        self.client.force_authenticate(user=self.admin_user)

    def test_successful_batch_reenrollment(self):
        payload = {'target_school_year_id': self.year2.pk}
        response = self.client.post(self.batch_reenroll_url, payload)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['successfully_reenrolled'], 2) # student1 to G2, student2 to G3 (last_grade)
        self.assertEqual(response.data['skipped_graduating_or_no_next_grade'], 1) # student3_graduating

        # Check new enrollments
        self.assertTrue(Enrollment.objects.filter(student=self.student1, school_class=self.class_g2_y2, status=Enrollment.STATUS_ACTIVE).exists())
        self.assertTrue(Enrollment.objects.filter(student=self.student2, school_class=self.class_g3_y2, status=Enrollment.STATUS_ACTIVE).exists())

        # Check old enrollments updated
        self.enrollment1_y1.refresh_from_db()
        self.assertEqual(self.enrollment1_y1.status, Enrollment.STATUS_COMPLETED)
        self.enrollment2_y1.refresh_from_db()
        self.assertEqual(self.enrollment2_y1.status, Enrollment.STATUS_COMPLETED)
        self.enrollment3_y1.refresh_from_db() # Graduating student's old enrollment also completed
        self.assertEqual(self.enrollment3_y1.status, Enrollment.STATUS_COMPLETED)

    def test_target_year_same_as_source_year(self):
        payload = {'target_school_year_id': self.year1.pk} # Target is same as source
        response = self.client.post(self.batch_reenroll_url, payload)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('non_field_errors', response.data) # Or specific field if serializer context is different

    def test_student_already_enrolled_in_target_year(self):
        # Pre-enroll student1 in target year
        Enrollment.objects.create(student=self.student1, school_class=self.class_g2_y2, status=Enrollment.STATUS_ACTIVE)

        payload = {'target_school_year_id': self.year2.pk}
        response = self.client.post(self.batch_reenroll_url, payload)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['successfully_reenrolled'], 1) # Only student2
        self.assertEqual(response.data['skipped_already_enrolled_in_target_year'], 1) # student1 skipped

    def test_no_class_for_next_grade_in_target_year(self):
        # student1 is in grade1 (self.class_g1_y1), next is grade2.
        # Delete the only class for grade2 in year2 to simulate no class available
        self.class_g2_y2.delete()

        payload = {'target_school_year_id': self.year2.pk}
        response = self.client.post(self.batch_reenroll_url, payload)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        # student1 (G1->G2) will be skipped, student2 (G2->G3) should succeed, student3 (G3->grad) will be skipped.
        self.assertEqual(response.data['successfully_reenrolled'], 1) # student2
        self.assertEqual(response.data['skipped_no_class_found_in_target_year'], 1) # student1
        self.assertEqual(response.data['skipped_graduating_or_no_next_grade'], 1) # student3

    def test_graduating_student_is_skipped(self):
        # Only student3_graduating is enrolled in self.year1 for this test
        self.enrollment1_y1.delete()
        self.enrollment2_y1.delete()

        payload = {'target_school_year_id': self.year2.pk}
        response = self.client.post(self.batch_reenroll_url, payload)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['successfully_reenrolled'], 0)
        self.assertEqual(response.data['skipped_graduating_or_no_next_grade'], 1)

    def test_non_admin_cannot_batch_reenroll(self):
        regular_user = User.objects.create_user(username='testuser_reenroll', email='tu_reenroll@example.com', password='p', user_type=User.USER_TYPE_TEACHER)
        self.client.force_authenticate(user=regular_user)
        payload = {'target_school_year_id': self.year2.pk}
        response = self.client.post(self.batch_reenroll_url, payload)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_invalid_target_year_id(self):
        payload = {'target_school_year_id': 9999} # Non-existent year
        response = self.client.post(self.batch_reenroll_url, payload)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('target_school_year_id', response.data)


import csv # For CSV parsing in tests
import io # For CSV parsing in tests

class EnrollmentListCSVExportViewTests(APITestCase):
    def setUp(self):
        self.admin_user = User.objects.create_user(username='enroll_csv_admin', email='enroll_csv@example.com', password='password123', user_type=User.USER_TYPE_ADMIN, is_staff=True)
        self.non_admin_user = User.objects.create_user(username='enroll_csv_teacher', email='enroll_csv_teacher@example.com', password='password123', user_type=User.USER_TYPE_TEACHER)

        # School Years
        self.year_2023 = SchoolYear.objects.create(year=2023, start_date='2023-01-01', end_date='2023-12-31', is_active=False)
        self.year_2024 = SchoolYear.objects.create(year=2024, start_date='2024-01-01', end_date='2024-12-31', is_active=True)

        # Grade Levels
        self.grade1 = StudentGradeLevel.objects.create(name="G1", order_in_sequence=1)
        self.grade2 = StudentGradeLevel.objects.create(name="G2", order_in_sequence=2)

        # School Classes
        self.class_g1_y2024 = SchoolClass.objects.create(name="G1-2024", school_year=self.year_2024, grade_level=self.grade1)
        self.class_g2_y2024 = SchoolClass.objects.create(name="G2-2024", school_year=self.year_2024, grade_level=self.grade2)
        self.class_g1_y2023 = SchoolClass.objects.create(name="G1-2023", school_year=self.year_2023, grade_level=self.grade1)

        # Students
        s1_user = User.objects.create_user(username='enroll_s1', email='enroll_s1@e.com', first_name="Enrolled", last_name="StudentOne", user_type=User.USER_TYPE_STUDENT)
        self.student1 = Student.objects.create(user=s1_user, registration_status=Student.STATUS_ACTIVE)

        s2_user = User.objects.create_user(username='enroll_s2', email='enroll_s2@e.com', first_name="Enrolled", last_name="StudentTwo", user_type=User.USER_TYPE_STUDENT)
        self.student2 = Student.objects.create(user=s2_user, registration_status=Student.STATUS_ACTIVE)

        s3_user = User.objects.create_user(username='enroll_s3', email='enroll_s3@e.com', first_name="Enrolled", last_name="StudentThree", user_type=User.USER_TYPE_STUDENT)
        self.student3 = Student.objects.create(user=s3_user, registration_status=Student.STATUS_ACTIVE)

        # Enrollments
        self.enrollment1 = Enrollment.objects.create(student=self.student1, school_class=self.class_g1_y2024, status=Enrollment.STATUS_ACTIVE)
        self.enrollment2 = Enrollment.objects.create(student=self.student2, school_class=self.class_g2_y2024, status=Enrollment.STATUS_ACTIVE)
        self.enrollment3 = Enrollment.objects.create(student=self.student3, school_class=self.class_g1_y2023, status=Enrollment.STATUS_COMPLETED)


        self.export_url = reverse('academics:enrollment_list_csv_export')
        self.client.force_authenticate(user=self.admin_user)

    def _parse_csv_response(self, response):
        content = response.content.decode('utf-8')
        reader = csv.reader(io.StringIO(content))
        headers = next(reader)
        data_rows = list(reader)
        return headers, data_rows

    def test_csv_export_basic_structure_and_data(self):
        response = self.client.get(self.export_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response['Content-Type'], 'text/csv; charset=utf-8') # Already correct from previous attempt
        self.assertTrue(response['Content-Disposition'].startswith('attachment; filename="enrollment_list_report_'))

        headers, data_rows = self._parse_csv_response(response)

        expected_headers = sorted([ # Expect alphabetically sorted headers
            'enrollment_id', 'student_name', 'student_username',
            'school_class_name', 'grade_level_name', 'school_year',
            'enrollment_status', 'enrollment_date'
        ])
        self.assertEqual(headers, expected_headers) # This was the failing assertion
        self.assertEqual(len(data_rows), 3) # All three enrollments

        # Check data for enrollment1
        e1_data = next(row for row in data_rows if row[headers.index('enrollment_id')] == str(self.enrollment1.id))
        self.assertEqual(e1_data[headers.index('student_name')], "Enrolled StudentOne")
        self.assertEqual(e1_data[headers.index('student_username')], "enroll_s1")
        self.assertEqual(e1_data[headers.index('school_class_name')], self.class_g1_y2024.name)
        self.assertEqual(e1_data[headers.index('grade_level_name')], self.grade1.name)
        self.assertEqual(e1_data[headers.index('school_year')], str(self.year_2024.year))
        self.assertEqual(e1_data[headers.index('enrollment_status')], "Ativa") # Display value for STATUS_ACTIVE

    def test_csv_export_filter_by_school_year(self):
        response = self.client.get(self.export_url, {'school_year_id': self.year_2024.pk})
        headers, data_rows = self._parse_csv_response(response)
        self.assertEqual(len(data_rows), 2) # enrollment1 and enrollment2
        for row in data_rows:
            self.assertEqual(row[headers.index('school_year')], str(self.year_2024.year))

    def test_csv_export_filter_by_grade_level(self):
        response = self.client.get(self.export_url, {'grade_level_id': self.grade1.pk, 'school_year_id': self.year_2024.pk})
        headers, data_rows = self._parse_csv_response(response)
        self.assertEqual(len(data_rows), 1)
        self.assertEqual(data_rows[0][headers.index('enrollment_id')], str(self.enrollment1.id))

    def test_csv_export_filter_by_school_class(self):
        response = self.client.get(self.export_url, {'school_class_id': self.class_g2_y2024.pk})
        headers, data_rows = self._parse_csv_response(response)
        self.assertEqual(len(data_rows), 1)
        self.assertEqual(data_rows[0][headers.index('enrollment_id')], str(self.enrollment2.id))

    def test_csv_export_filter_by_status(self):
        response = self.client.get(self.export_url, {'status': Enrollment.STATUS_COMPLETED})
        headers, data_rows = self._parse_csv_response(response)
        self.assertEqual(len(data_rows), 1)
        self.assertEqual(data_rows[0][headers.index('enrollment_id')], str(self.enrollment3.id))
        self.assertEqual(data_rows[0][headers.index('enrollment_status')], "Concluída")

    def test_csv_export_filter_by_student(self):
        response = self.client.get(self.export_url, {'student_id': self.student1.pk})
        headers, data_rows = self._parse_csv_response(response)
        self.assertEqual(len(data_rows), 1)
        self.assertEqual(data_rows[0][headers.index('enrollment_id')], str(self.enrollment1.id))

    def test_csv_export_permission_denied_for_non_admin(self):
        self.client.force_authenticate(user=self.non_admin_user)
        response = self.client.get(self.export_url)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)


class AnnouncementTests(APITestCase):
    def setUp(self):
        self.admin_user = User.objects.create_user(username='admin_announce', email='admin_announce@example.com', password='password123', user_type=User.USER_TYPE_ADMIN, is_staff=True)
        self.staff_user = User.objects.create_user(username='staff_announce', email='staff_announce@example.com', password='password123', user_type=User.USER_TYPE_STAFF, is_staff=True)
        self.teacher_user = User.objects.create_user(username='teacher_announce', email='teacher_announce@example.com', password='password123', user_type=User.USER_TYPE_TEACHER)
        self.parent_user = User.objects.create_user(username='parent_announce', email='parent_announce@example.com', password='password123', user_type=User.USER_TYPE_PARENT)

        self.grade_level1 = StudentGradeLevel.objects.create(name="Grade X", order_in_sequence=10)
        self.grade_level2 = StudentGradeLevel.objects.create(name="Grade Y", order_in_sequence=11)

        self.school_year = SchoolYear.objects.create(year=2024, start_date='2024-01-01', end_date='2024-12-31', is_active=True)
        self.class1_gX = SchoolClass.objects.create(name="Class 10A", school_year=self.school_year, grade_level=self.grade_level1)
        self.class2_gY = SchoolClass.objects.create(name="Class 11A", school_year=self.school_year, grade_level=self.grade_level2)

        self.announcements_url = reverse('academics:announcement-list')
        self.client.force_authenticate(user=self.admin_user) # Default to admin for most tests

    def get_announcement_detail_url(self, announcement_id):
        return reverse('academics:announcement-detail', kwargs={'pk': announcement_id})

    def test_create_school_wide_announcement(self):
        payload = {
            'title': 'School Holiday',
            'content': 'School will be closed tomorrow.',
            'is_school_wide': True
        }
        response = self.client.post(self.announcements_url, payload)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['title'], payload['title'])
        self.assertEqual(response.data['author'], self.admin_user.pk)
        self.assertTrue(response.data['is_school_wide'])
        announcement = Announcement.objects.get(pk=response.data['id'])
        self.assertEqual(announcement.author, self.admin_user)

    def test_create_announcement_for_specific_user_types(self):
        payload = {
            'title': 'PTA Meeting',
            'content': 'Meeting for all parents and teachers.',
            'target_user_types': [User.USER_TYPE_PARENT, User.USER_TYPE_TEACHER] # Already correct
        }
        response = self.client.post(self.announcements_url, payload, format='json') # Specify JSON format
        # Temporarily print response.data to understand the 400 error
        if response.status_code != status.HTTP_201_CREATED:
            print(f"DEBUG: test_create_announcement_for_specific_user_types response.data: {response.data}")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertListEqual(sorted(response.data['target_user_types']), sorted([User.USER_TYPE_PARENT, User.USER_TYPE_TEACHER]))

    def test_create_announcement_for_specific_grades(self):
        payload = {
            'title': 'Grade X Exam Schedule',
            'content': 'Details about upcoming exams for Grade X.',
            'target_grade_levels': [self.grade_level1.pk]
        }
        response = self.client.post(self.announcements_url, payload)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertIn(self.grade_level1.pk, response.data['target_grade_levels'])

    def test_create_announcement_for_specific_classes(self):
        payload = {
            'title': 'Class 10A Field Trip',
            'content': 'Information about the upcoming field trip for Class 10A.',
            'target_school_classes': [self.class1_gX.pk]
        }
        response = self.client.post(self.announcements_url, payload)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertIn(self.class1_gX.pk, response.data['target_school_classes'])

    def test_create_announcement_fails_if_not_school_wide_and_no_target(self):
        payload = {
            'title': 'Empty Target Announcement',
            'content': 'This should fail.',
            'is_school_wide': False
            # No target_user_types, target_grade_levels, or target_school_classes
        }
        response = self.client.post(self.announcements_url, payload)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('non_field_errors', response.data)

    def test_create_announcement_with_expiry_date(self):
        future_expiry = timezone.now() + timezone.timedelta(days=7)
        payload = {
            'title': 'Limited Time Offer',
            'content': 'This offer expires soon!',
            'is_school_wide': True,
            'expiry_date': future_expiry.isoformat()
        }
        response = self.client.post(self.announcements_url, payload)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertIsNotNone(response.data['expiry_date'])

    def test_create_announcement_past_expiry_date_fails(self):
        past_expiry = timezone.now() - timezone.timedelta(days=1)
        payload = {
            'title': 'Expired Offer',
            'content': 'This offer is already expired.',
            'is_school_wide': True,
            'expiry_date': past_expiry.isoformat()
        }
        response = self.client.post(self.announcements_url, payload)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('non_field_errors', response.data) # expiry_date validation in serializer's validate()

    def test_update_announcement(self):
        announcement = Announcement.objects.create(author=self.admin_user, title="Old Title", content="Old Content", is_school_wide=True)
        payload = {'title': 'New Updated Title', 'content': 'Fresh content here.'}
        response = self.client.patch(self.get_announcement_detail_url(announcement.id), payload)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['title'], 'New Updated Title')
        announcement.refresh_from_db()
        self.assertEqual(announcement.title, 'New Updated Title')

    def test_delete_announcement(self):
        announcement = Announcement.objects.create(author=self.admin_user, title="To Delete", content="Delete me", is_school_wide=True)
        response = self.client.delete(self.get_announcement_detail_url(announcement.id))
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(Announcement.objects.filter(pk=announcement.id).exists())

    def test_non_admin_cannot_create_announcement(self):
        self.client.force_authenticate(user=self.parent_user) # Parent user
        payload = {'title': 'Parent Announcement', 'content': 'Content', 'is_school_wide': True}
        response = self.client.post(self.announcements_url, payload)
        # This depends on default permission for AnnouncementViewSet. If IsAdminUser, then 403.
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_filter_announcements_by_author(self):
        Announcement.objects.create(author=self.admin_user, title="Admin Post", content="...", is_school_wide=True)
        Announcement.objects.create(author=self.staff_user, title="Staff Post", content="...", is_school_wide=True)

        response = self.client.get(self.announcements_url, {'author': self.staff_user.pk})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]['author'], self.staff_user.pk)

    def test_filter_announcements_school_wide(self):
        Announcement.objects.create(author=self.admin_user, title="School Wide 1", content="...", is_school_wide=True)
        Announcement.objects.create(author=self.admin_user, title="Not School Wide", content="...", is_school_wide=False, target_user_types=[User.USER_TYPE_TEACHER]) # Already correct

        response = self.client.get(self.announcements_url, {'is_school_wide': 'true'})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertTrue(response.data[0]['is_school_wide'])

        response_false = self.client.get(self.announcements_url, {'is_school_wide': 'false'})
        self.assertEqual(response_false.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response_false.data), 1)
        self.assertFalse(response_false.data[0]['is_school_wide'])


class DashboardSummaryViewTests(APITestCase):
    def setUp(self):
        self.admin_user = User.objects.create_user(username='dash_admin', email='dash_admin@example.com', password='password123', user_type=User.USER_TYPE_ADMIN, is_staff=True) # Corrected username to avoid conflict
        self.non_admin_user = User.objects.create_user(username='dash_teacher', email='dash_teacher@example.com', password='password123', user_type=User.USER_TYPE_TEACHER) # Corrected username

        # School Years
        self.active_year = SchoolYear.objects.create(year=timezone.now().year, start_date=timezone.now().date(), end_date=timezone.now().date() + timezone.timedelta(days=300), is_active=True)
        SchoolYear.objects.create(year=timezone.now().year - 1, start_date=timezone.now().date() - timezone.timedelta(days=365), end_date=timezone.now().date() - timezone.timedelta(days=65), is_active=False)

        # Grade Levels
        self.grade1 = StudentGradeLevel.objects.create(name="Grade 1", order_in_sequence=1)
        self.grade2 = StudentGradeLevel.objects.create(name="Grade 2", order_in_sequence=2)

        # School Classes
        self.class_g1_ay = SchoolClass.objects.create(name="G1AY", school_year=self.active_year, grade_level=self.grade1)
        self.class_g2_ay = SchoolClass.objects.create(name="G2AY", school_year=self.active_year, grade_level=self.grade2)

        # Students and Enrollments
        # Student 1: Active, Grade 1
        s1_user = User.objects.create_user(username='s1_dash', email='s1dash@example.com', user_type=User.USER_TYPE_STUDENT)
        s1 = Student.objects.create(user=s1_user, registration_status=Student.STATUS_ACTIVE, grade_level_pretended=self.grade1)
        Enrollment.objects.create(student=s1, school_class=self.class_g1_ay, status=Enrollment.STATUS_ACTIVE)

        # Student 2: Active, Grade 1
        s2_user = User.objects.create_user(username='s2_dash', email='s2dash@example.com', user_type=User.USER_TYPE_STUDENT)
        s2 = Student.objects.create(user=s2_user, registration_status=Student.STATUS_ACTIVE, grade_level_pretended=self.grade1)
        Enrollment.objects.create(student=s2, school_class=self.class_g1_ay, status=Enrollment.STATUS_ACTIVE)

        # Student 3: Active, Grade 2
        s3_user = User.objects.create_user(username='s3_dash', email='s3dash@example.com', user_type=User.USER_TYPE_STUDENT)
        s3 = Student.objects.create(user=s3_user, registration_status=Student.STATUS_ACTIVE, grade_level_pretended=self.grade2)
        Enrollment.objects.create(student=s3, school_class=self.class_g2_ay, status=Enrollment.STATUS_ACTIVE)

        # Student 4: Pre-registered
        s4_user = User.objects.create_user(username='s4_dash', email='s4dash@example.com', user_type=User.USER_TYPE_STUDENT)
        Student.objects.create(user=s4_user, registration_status=Student.STATUS_PRE_REGISTERED, grade_level_pretended=self.grade1)

        # Student 5: Pending Validation
        s5_user = User.objects.create_user(username='s5_dash', email='s5dash@example.com', user_type=User.USER_TYPE_STUDENT)
        Student.objects.create(user=s5_user, registration_status=Student.STATUS_PENDING_VALIDATION, grade_level_pretended=self.grade1)

        # Student 6: Inactive (but was active in an enrollment that is now completed)
        s6_user = User.objects.create_user(username='s6_dash', email='s6dash@example.com', user_type=User.USER_TYPE_STUDENT)
        s6 = Student.objects.create(user=s6_user, registration_status=Student.STATUS_INACTIVE, grade_level_pretended=self.grade1)
        Enrollment.objects.create(student=s6, school_class=self.class_g1_ay, status=Enrollment.STATUS_COMPLETED)


        self.dashboard_url = reverse('academics:dashboard-summary')

    def test_dashboard_summary_correct_counts(self):
        self.client.force_authenticate(user=self.admin_user)
        response = self.client.get(self.dashboard_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        data = response.data
        self.assertEqual(data['total_active_students'], 3) # s1, s2, s3
        self.assertEqual(data['total_preregistered_students'], 1) # s4
        self.assertEqual(data['total_pending_validation_students'], 1) # s5
        self.assertEqual(data['total_active_enrollments'], 3) # For s1, s2, s3
        self.assertEqual(data['active_school_years'], 1)

        grade_level_summary = data['active_students_by_grade_level']

        # Sort by name to ensure consistent order for comparison
        grade_level_summary_sorted = sorted(grade_level_summary, key=lambda x: x['grade_level_name'])

        expected_grade_summary = [
            {'grade_level_name': self.grade1.name, 'count': 2}, # s1, s2
            {'grade_level_name': self.grade2.name, 'count': 1}, # s3
        ]
        self.assertEqual(len(grade_level_summary_sorted), len(expected_grade_summary))
        for i, item in enumerate(expected_grade_summary):
            self.assertEqual(grade_level_summary_sorted[i]['grade_level_name'], item['grade_level_name'])
            self.assertEqual(grade_level_summary_sorted[i]['count'], item['count'])


    def test_dashboard_summary_permissions(self):
        self.client.force_authenticate(user=self.non_admin_user)
        response = self.client.get(self.dashboard_url)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_dashboard_summary_empty_db(self):
        # Clear relevant data setup by main setUp
        Enrollment.objects.all().delete()
        Student.objects.all().delete()
        User.objects.filter(username__endswith='_dash').delete() # Clean users created in this test class's setUp
        SchoolClass.objects.all().delete()
        StudentGradeLevel.objects.all().delete()
        SchoolYear.objects.all().delete()

        # Re-create a minimal active year for context, but no students/enrollments
        SchoolYear.objects.create(year=timezone.now().year, start_date=timezone.now().date(), end_date=timezone.now().date() + timezone.timedelta(days=300), is_active=True)

        self.client.force_authenticate(user=self.admin_user)
        response = self.client.get(self.dashboard_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        data = response.data
        self.assertEqual(data['total_active_students'], 0)
        self.assertEqual(data['active_students_by_grade_level'], [])
        self.assertEqual(data['total_preregistered_students'], 0)
        self.assertEqual(data['total_pending_validation_students'], 0)
        self.assertEqual(data['total_active_enrollments'], 0)
        self.assertEqual(data['active_school_years'], 1) # The one we just created
