from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views, api_views

app_name = 'dicom_viewer'

# Router API
router = DefaultRouter()
router.register(r'api/patients', api_views.PatientViewSet, basename='api-patient')
router.register(r'api/studies', api_views.StudyViewSet, basename='api-study')
router.register(r'api/series', api_views.SeriesViewSet, basename='api-series')
router.register(r'api/instances', api_views.InstanceViewSet, basename='api-instance')

urlpatterns = [
    # Vues HTML
    path('patients/', views.patient_list, name='patient_list'),
    path('patients/<int:patient_id>/', views.patient_detail, name='patient_detail'),
    path('patients/<int:patient_id>/sync/', views.sync_patient_ajax, name='sync_patient'),
    path('studies/<int:study_id>/', views.study_detail, name='study_detail'),
    path('viewer/<int:series_id>/', views.dicom_viewer, name='viewer'),
    
    # API REST
    path('', include(router.urls)),
]