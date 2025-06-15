# medical/urls.py - Mise à jour complète
from django.urls import path
from . import views

app_name = 'medical'

urlpatterns = [
    # Gestion des prescriptions
    path('prescriptions/', views.prescription_list, name='prescription_list'),
    
    # Gestion des rendez-vous
    path('appointments/', views.appointment_list, name='appointment_list'),
    path('appointments/create/', views.appointment_create, name='appointment_create'),
    path('appointments/<uuid:appointment_id>/', views.appointment_detail, name='appointment_detail'),
    path('appointments/<uuid:appointment_id>/update-status/', views.update_appointment_status, name='update_appointment_status'),
    path('appointments/quick-actions/', views.quick_actions_appointments, name='quick_actions_appointments'),
    
    # Planning médecin
    path('schedule/', views.doctor_schedule, name='doctor_schedule'),
    
    # API endpoints pour AJAX
    path('api/appointments/status-update/', views.update_appointment_status, name='api_appointment_status'),
]   