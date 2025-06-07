from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    MyGradesViewSet,
    MyAttendanceViewSet,
    MySchoolEventsViewSet,
    MyDidacticMaterialsViewSet,
    MyTeacherAssignmentsViewSet,
    TeacherGradeViewSet,
    TeacherAttendanceViewSet,
    TeacherSchoolEventViewSet,
    TeacherDidacticMaterialViewSet, # TeacherDidacticMaterialViewSet importado
    EnrollmentViewSet, # Importar EnrollmentViewSet
    SchoolYearViewSet, # Importar SchoolYearViewSet
    AnnouncementViewSet, # Importar AnnouncementViewSet
    EnrollmentListCSVExportView, # Moved import to top
    DashboardSummaryView # Moved import to top
)
# Adicionar aqui outros ViewSets do app 'academics' se necessário no futuro
# Ex: from .views import SubjectViewSet, SchoolClassViewSet

app_name = 'academics'  # Define o namespace do app

# Cria uma instância do DefaultRouter
router = DefaultRouter()

# Registra os ViewSets "My Data" (para alunos/pais)
router.register(r'my-data/grades', MyGradesViewSet, basename='my-grades')
router.register(r'my-data/attendance', MyAttendanceViewSet, basename='my-attendance')
router.register(r'my-data/events', MySchoolEventsViewSet, basename='my-events')
router.register(r'my-data/materials', MyDidacticMaterialsViewSet, basename='my-materials')

# Registra os ViewSets para Professores
router.register(r'teacher/my-assignments', MyTeacherAssignmentsViewSet, basename='my-teacher-assignments')
router.register(r'teacher/grades', TeacherGradeViewSet, basename='teacher-grades')
router.register(r'teacher/attendance', TeacherAttendanceViewSet, basename='teacher-attendance')
router.register(r'teacher/events', TeacherSchoolEventViewSet, basename='teacher-events')
router.register(r'teacher/materials', TeacherDidacticMaterialViewSet, basename='teacher-materials') # Novo ViewSet registrado


# Registra outros ViewSets administrativos ou gerais para o app 'academics' (exemplo)
# router.register(r'school-years', SchoolYearViewSet, basename='schoolyear')
# router.register(r'subjects', SubjectViewSet, basename='subject')
# router.register(r'school-classes', SchoolClassViewSet, basename='schoolclass')
router.register(r'enrollments', EnrollmentViewSet, basename='enrollment')
router.register(r'school-years', SchoolYearViewSet, basename='schoolyear')
router.register(r'announcements', AnnouncementViewSet, basename='announcement')


from .views import DashboardSummaryView # Import the new view

# As urlpatterns do app são definidas pelas URLs geradas pelo router.
urlpatterns = [
    path('', include(router.urls)),
    path('dashboard/summary/', DashboardSummaryView.as_view(), name='dashboard-summary'),
    path('reports/enrollment-list/csv/', EnrollmentListCSVExportView.as_view(), name='enrollment_list_csv_export'),
    # Adicionar outras URLs específicas do app aqui, se não forem baseadas em ViewSets.
]
