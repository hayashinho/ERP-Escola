from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase
from apps.accounts.models import User, UserProfile # Added UserProfile
from apps.students.models import Student, StudentDocument, GradeLevel
from django.core.files.uploadedfile import SimpleUploadedFile
# Imports for CSV tests are at the bottom currently, consider moving them up for consistency

class StudentLifecycleManagementTests(APITestCase):
    def setUp(self):
        # Create Users
        self.admin_user = User.objects.create_user(username='admin_student_test', email='admin_student@example.com', password='password123', user_type=User.UserType.ADMIN, is_staff=True)
        self.secretaria_user = User.objects.create_user(username='secretaria_student_test', email='secretaria_student@example.com', password='password123', user_type=User.UserType.STAFF, is_staff=True) # Assuming STAFF can be Secretaria
        self.regular_user = User.objects.create_user(username='regular_student_test', email='regular_student@example.com', password='password123', user_type=User.UserType.PARENT)

        # Create GradeLevel
        self.grade_level = GradeLevel.objects.create(name="1st Grade", order_in_sequence=1)

        # Create Student with an associated user
        self.student_user_for_lifecycle = User.objects.create_user(username='student_lc_test', email='student_lc@example.com', password='password123', user_type=User.UserType.STUDENT)
        self.student_for_lifecycle = Student.objects.create(
            user=self.student_user_for_lifecycle,
            grade_level_pretended=self.grade_level,
            registration_status=Student.RegistrationStatus.PRE_REGISTERED
        )

        # URLs for StudentManagementViewSet
        self.student_list_url = reverse('students:student_management-list')
        self.student_detail_url = reverse('students:student_management-detail', kwargs={'pk': self.student_for_lifecycle.pk})

    # --- Student Registration Status Tests ---
    def test_secretaria_can_update_student_status_to_pending_validation(self):
        self.client.force_authenticate(user=self.secretaria_user)
        payload = {'registration_status': Student.RegistrationStatus.PENDING_VALIDATION}
        response = self.client.patch(self.student_detail_url, payload)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.student_for_lifecycle.refresh_from_db()
        self.assertEqual(self.student_for_lifecycle.registration_status, Student.RegistrationStatus.PENDING_VALIDATION)

    def test_secretaria_can_update_student_status_to_active(self):
        self.client.force_authenticate(user=self.secretaria_user)
        self.student_for_lifecycle.registration_status = Student.RegistrationStatus.PENDING_VALIDATION
        self.student_for_lifecycle.save()

        payload = {'registration_status': Student.RegistrationStatus.ACTIVE}
        response = self.client.patch(self.student_detail_url, payload)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.student_for_lifecycle.refresh_from_db()
        self.assertEqual(self.student_for_lifecycle.registration_status, Student.RegistrationStatus.ACTIVE)

    def test_secretaria_can_reject_student_with_reason(self):
        self.client.force_authenticate(user=self.secretaria_user)
        rejection_reason_text = "Documentation incomplete."
        payload = {
            'registration_status': Student.RegistrationStatus.REJECTED,
            'rejection_reason': rejection_reason_text
        }
        response = self.client.patch(self.student_detail_url, payload)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.student_for_lifecycle.refresh_from_db()
        self.assertEqual(self.student_for_lifecycle.registration_status, Student.RegistrationStatus.REJECTED)
        self.assertEqual(self.student_for_lifecycle.rejection_reason, rejection_reason_text)

    def test_rejection_reason_cleared_if_status_not_rejected(self):
        self.client.force_authenticate(user=self.secretaria_user)
        self.student_for_lifecycle.registration_status = Student.RegistrationStatus.REJECTED
        self.student_for_lifecycle.rejection_reason = "Initial reason"
        self.student_for_lifecycle.save()

        payload = {'registration_status': Student.RegistrationStatus.ACTIVE} # Change to a non-rejected status
        response = self.client.patch(self.student_detail_url, payload)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.student_for_lifecycle.refresh_from_db()
        self.assertEqual(self.student_for_lifecycle.registration_status, Student.RegistrationStatus.ACTIVE)
        self.assertIsNone(self.student_for_lifecycle.rejection_reason)

    def test_regular_user_cannot_update_student_status(self):
        self.client.force_authenticate(user=self.regular_user)
        payload = {'registration_status': Student.RegistrationStatus.ACTIVE}
        response = self.client.patch(self.student_detail_url, payload)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_student_other_fields_are_readonly_for_secretaria(self):
        self.client.force_authenticate(user=self.secretaria_user)
        original_enrollment_date = self.student_for_lifecycle.enrollment_date
        new_user_for_student = User.objects.create_user(username="newstudentuser", email="new@s.com", user_type=User.UserType.STUDENT)

        payload = {
            'registration_status': Student.RegistrationStatus.ACTIVE,
            'enrollment_date': '2025-01-01', # Attempt to change read-only field
            'user': new_user_for_student.pk # Attempt to change user
        }
        response = self.client.patch(self.student_detail_url, payload)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.student_for_lifecycle.refresh_from_db()
        self.assertEqual(self.student_for_lifecycle.registration_status, Student.RegistrationStatus.ACTIVE)
        self.assertEqual(self.student_for_lifecycle.enrollment_date, original_enrollment_date) # Should not change
        self.assertEqual(self.student_for_lifecycle.user, self.student_user_for_lifecycle) # Should not change


class StudentDocumentManagementTests(APITestCase):
    def setUp(self):
        # Users
        self.admin_user = User.objects.create_user(username='admin_doc_test', email='admin_doc@example.com', password='password123', user_type=User.UserType.ADMIN, is_staff=True)
        self.secretaria_user = User.objects.create_user(username='secretaria_doc_test', email='secretaria_doc@example.com', password='password123', user_type=User.UserType.STAFF, is_staff=True)
        self.regular_user = User.objects.create_user(username='regular_doc_test', email='regular_doc@example.com', password='password123', user_type=User.UserType.PARENT)

        # GradeLevel
        self.grade_level = GradeLevel.objects.create(name="2nd Grade", order_in_sequence=2)

        # Student
        self.student_user_for_docs = User.objects.create_user(username='student_doc_test', email='student_doc@example.com', password='password123', user_type=User.UserType.STUDENT)
        self.student_for_docs = Student.objects.create(user=self.student_user_for_docs, grade_level_pretended=self.grade_level)

        # Document
        # Create a dummy file for upload
        self.dummy_file = SimpleUploadedFile("file.pdf", b"file_content", content_type="application/pdf")
        self.student_document = StudentDocument.objects.create(
            student=self.student_for_docs,
            document_type=StudentDocument.DocumentTypeChoices.BIRTH_CERTIFICATE,
            file=self.dummy_file,
            validation_status=StudentDocument.ValidationStatus.PENDING
        )

        # URLs for StudentDocumentManagementViewSet
        self.doc_list_url = reverse('students:student_document_management-list')
        self.doc_detail_url = reverse('students:student_document_management-detail', kwargs={'pk': self.student_document.pk})

    # --- Student Document Validation Status Tests ---
    def test_secretaria_can_approve_document(self):
        self.client.force_authenticate(user=self.secretaria_user)
        payload = {'validation_status': StudentDocument.ValidationStatus.APPROVED, 'notes': 'All good.'}
        response = self.client.patch(self.doc_detail_url, payload)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.student_document.refresh_from_db()
        self.assertEqual(self.student_document.validation_status, StudentDocument.ValidationStatus.APPROVED)
        self.assertEqual(self.student_document.notes, 'All good.')

    def test_secretaria_can_reject_document_with_notes(self):
        self.client.force_authenticate(user=self.secretaria_user)
        rejection_note = "Signature missing on page 2."
        payload = {'validation_status': StudentDocument.ValidationStatus.REJECTED, 'notes': rejection_note}
        response = self.client.patch(self.doc_detail_url, payload)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.student_document.refresh_from_db()
        self.assertEqual(self.student_document.validation_status, StudentDocument.ValidationStatus.REJECTED)
        self.assertEqual(self.student_document.notes, rejection_note)

    def test_regular_user_cannot_update_document_status(self):
        self.client.force_authenticate(user=self.regular_user)
        payload = {'validation_status': StudentDocument.ValidationStatus.APPROVED}
        response = self.client.patch(self.doc_detail_url, payload)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_document_other_fields_are_readonly_for_secretaria(self):
        self.client.force_authenticate(user=self.secretaria_user)
        original_doc_type = self.student_document.document_type

        payload = {
            'validation_status': StudentDocument.ValidationStatus.APPROVED,
            'document_type': StudentDocument.DocumentTypeChoices.PHOTO_ID, # Attempt to change
            'notes': 'Updated notes'
        }
        response = self.client.patch(self.doc_detail_url, payload)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.student_document.refresh_from_db()
        self.assertEqual(self.student_document.validation_status, StudentDocument.ValidationStatus.APPROVED)
        self.assertEqual(self.student_document.notes, 'Updated notes')
        self.assertEqual(self.student_document.document_type, original_doc_type) # Should not change

    def test_list_documents_and_filter_by_status_as_secretaria(self):
        self.client.force_authenticate(user=self.secretaria_user)
        # Create another document with a different status
        StudentDocument.objects.create(
            student=self.student_for_docs,
            document_type=StudentDocument.DocumentTypeChoices.PHOTO_ID,
            file=SimpleUploadedFile("another.pdf", b"content", content_type="application/pdf"),
            validation_status=StudentDocument.ValidationStatus.APPROVED
        )

        # Filter for PENDING
        response = self.client.get(self.doc_list_url, {'validation_status': StudentDocument.ValidationStatus.PENDING})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]['id'], self.student_document.id)


import csv
import io
from apps.academics.models import SchoolYear, SchoolClass, Enrollment # For test data setup

class StudentListCSVExportViewTests(APITestCase):
    def setUp(self):
        self.admin_user = User.objects.create_user(username='csv_admin', email='csv_admin@example.com', password='password123', user_type=User.USER_TYPE_ADMIN, is_staff=True)
        self.non_admin_user = User.objects.create_user(username='csv_teacher', email='csv_teacher@example.com', password='password123', user_type=User.USER_TYPE_TEACHER)

        # School Years
        self.active_year = SchoolYear.objects.create(year=2024, start_date='2024-01-01', end_date='2024-12-31', is_active=True)
        self.previous_year = SchoolYear.objects.create(year=2023, start_date='2023-01-01', end_date='2023-12-31', is_active=False)

        # Grade Levels
        self.grade10 = GradeLevel.objects.create(name="Grade 10", order_in_sequence=10)
        self.grade11 = GradeLevel.objects.create(name="Grade 11", order_in_sequence=11)

        # School Classes
        self.class_g10_ay = SchoolClass.objects.create(name="G10-A", school_year=self.active_year, grade_level=self.grade10)
        self.class_g11_ay = SchoolClass.objects.create(name="G11-A", school_year=self.active_year, grade_level=self.grade11)
        self.class_g10_py = SchoolClass.objects.create(name="G10-P", school_year=self.previous_year, grade_level=self.grade10)

        # Students & Profiles & Enrollments
        # Student 1 (Active, Grade 10 in Active Year)
        s1_user = User.objects.create_user(username='student_csv1', email='s_csv1@example.com', first_name="Alice", last_name="Smith")
        self.s1_profile = UserProfile.objects.create(user=s1_user, cpf="111.111.111-11", date_of_birth="2007-01-01")
        self.s1 = Student.objects.create(user=s1_user, registration_status=Student.STATUS_ACTIVE, enrollment_date="2024-01-15")
        Enrollment.objects.create(student=self.s1, school_class=self.class_g10_ay, status=Enrollment.STATUS_ACTIVE)

        # Student 2 (Active, Grade 11 in Active Year)
        s2_user = User.objects.create_user(username='student_csv2', email='s_csv2@example.com', first_name="Bob", last_name="Johnson")
        self.s2_profile = UserProfile.objects.create(user=s2_user, cpf="222.222.222-22", date_of_birth="2006-05-10")
        self.s2 = Student.objects.create(user=s2_user, registration_status=Student.STATUS_ACTIVE, enrollment_date="2024-01-16")
        Enrollment.objects.create(student=self.s2, school_class=self.class_g11_ay, status=Enrollment.STATUS_ACTIVE)

        # Student 3 (Pre-registered, no active enrollment for current year)
        s3_user = User.objects.create_user(username='student_csv3', email='s_csv3@example.com', first_name="Charlie", last_name="Brown")
        self.s3 = Student.objects.create(user=s3_user, registration_status=Student.STATUS_PRE_REGISTERED)

        # Student 4 (Active, but only enrollment in previous year)
        s4_user = User.objects.create_user(username='student_csv4', email='s_csv4@example.com', first_name="Diana", last_name="Prince")
        self.s4 = Student.objects.create(user=s4_user, registration_status=Student.STATUS_ACTIVE)
        Enrollment.objects.create(student=self.s4, school_class=self.class_g10_py, status=Enrollment.STATUS_COMPLETED)


        self.export_url = reverse('students:student_list_csv_export')
        self.client.force_authenticate(user=self.admin_user)

    def _parse_csv_response(self, response):
        content = response.content.decode('utf-8')
        reader = csv.reader(io.StringIO(content))
        headers = next(reader)
        data = list(reader)
        return headers, data

    def test_csv_export_all_students_basic_structure(self):
        response = self.client.get(self.export_url, {'school_year_id': self.active_year.pk}) # Filter by active year for grade info
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response['Content-Type'], 'text/csv')
        self.assertTrue(response['Content-Disposition'].startswith('attachment; filename="student_list_report_'))

        headers, data_rows = self._parse_csv_response(response)

        expected_headers = [
            'user_id', 'username', 'full_name', 'email', 'cpf', 'date_of_birth',
            'student_registration_status', 'student_enrollment_date',
            'current_grade_level_name', 'active_enrollment_school_year'
        ]
        self.assertEqual(headers, expected_headers)

        # Should include all 4 students, but grade/year info only for those with active enrollment in the target year
        self.assertEqual(len(data_rows), 4)

        # Check data for student1 (Alice)
        s1_data = next(row for row in data_rows if row[1] == 'student_csv1') # username is 2nd col
        self.assertEqual(s1_data[headers.index('full_name')], "Alice Smith")
        self.assertEqual(s1_data[headers.index('cpf')], "111.111.111-11")
        self.assertEqual(s1_data[headers.index('student_registration_status')], "Ativo")
        self.assertEqual(s1_data[headers.index('current_grade_level_name')], self.grade10.name)
        self.assertEqual(s1_data[headers.index('active_enrollment_school_year')], str(self.active_year.year))

    def test_csv_export_filter_by_grade_level(self):
        # Filter for Grade 10 in active year
        response = self.client.get(self.export_url, {'grade_level_id': self.grade10.pk, 'school_year_id': self.active_year.pk})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        headers, data_rows = self._parse_csv_response(response)

        self.assertEqual(len(data_rows), 1) # Only student1
        self.assertEqual(data_rows[0][headers.index('username')], 'student_csv1')

    def test_csv_export_filter_by_registration_status(self):
        # Filter for PRE_REGISTERED students (grade/year info might be blank for these)
        response = self.client.get(self.export_url, {'registration_status': Student.STATUS_PRE_REGISTERED})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        headers, data_rows = self._parse_csv_response(response)

        self.assertEqual(len(data_rows), 1)
        self.assertEqual(data_rows[0][headers.index('username')], 'student_csv3')
        self.assertEqual(data_rows[0][headers.index('student_registration_status')], "Pré-Cadastrado")
        # current_grade_level_name and active_enrollment_school_year might be empty if no active enrollment
        self.assertEqual(data_rows[0][headers.index('current_grade_level_name')], '')


    def test_csv_export_filter_by_school_year(self):
        # This filter is primarily to provide context for grade level,
        # but let's test it to ensure it restricts active enrollment info to that year.
        # Student4 has enrollment only in previous_year.
        response = self.client.get(self.export_url, {'school_year_id': self.previous_year.pk})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        headers, data_rows = self._parse_csv_response(response)

        s4_data = next((row for row in data_rows if row[headers.index('username')] == 'student_csv4'), None)
        self.assertIsNotNone(s4_data)
        self.assertEqual(s4_data[headers.index('current_grade_level_name')], self.grade10.name) # Enrolled in G10 in previous year
        self.assertEqual(s4_data[headers.index('active_enrollment_school_year')], str(self.previous_year.year))

        # Student1 should not have grade/year info for previous_year context
        s1_data = next((row for row in data_rows if row[headers.index('username')] == 'student_csv1'), None)
        self.assertIsNotNone(s1_data)
        self.assertEqual(s1_data[headers.index('current_grade_level_name')], '')


    def test_csv_export_permission_denied_for_non_admin(self):
        self.client.force_authenticate(user=self.non_admin_user)
        response = self.client.get(self.export_url)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(response.data[0]['validation_status'], StudentDocument.ValidationStatus.PENDING)

        # Filter for APPROVED
        response = self.client.get(self.doc_list_url, {'validation_status': StudentDocument.ValidationStatus.APPROVED})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]['validation_status'], StudentDocument.ValidationStatus.APPROVED)
