from django.urls import path
from . import views

app_name = 'administration'

urlpatterns = [
    # Dashboard principal
    path('', views.dashboard, name='dashboard'),
    
    # Gestion des utilisateurs
    path('users/', views.user_management, name='user_management'),
    path('users/<int:user_id>/', views.user_detail, name='user_detail'),
    path('users/<int:user_id>/toggle/', views.toggle_user_status, name='toggle_user_status'),
    
    # Logs et audit
    path('access-logs/', views.access_logs, name='access_logs'),
    
    # Monitoring Orthanc
    path('orthanc-monitor/', views.orthanc_monitor, name='orthanc_monitor'),
    path('sync/', views.sync_orthanc, name='sync_orthanc'),
    
    # Paramètres système
    path('system-settings/', views.system_settings, name='system_settings'),
    
    # Gestion des patients
    path('patients/create/', views.patient_create, name='patient_create'),
    path('patients/<int:patient_id>/edit/', views.patient_edit, name='patient_edit'),
    path('doctor-patient-assign/', views.doctor_patient_assign, name='doctor_patient_assign'),
    
    # API endpoints
    path('api/dashboard-stats/', views.api_dashboard_stats, name='api_dashboard_stats'),
    path('api/server-status/', views.api_server_status, name='api_server_status'),
]