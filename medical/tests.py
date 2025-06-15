from django.test import TestCase, Client
from django.contrib.auth import get_user_model
from django.utils import timezone
from datetime import date, time, timedelta
from .models import Appointment, DoctorAvailability
from dicom_viewer.models import Patient
from .utils import AppointmentManager

User = get_user_model()

class AppointmentTestCase(TestCase):
    def setUp(self):
        # Créer un médecin
        self.doctor = User.objects.create_user(
            username='dr_test',
            email='doctor@test.com',
            password='testpass123',
            role='doctor',
            first_name='John',
            last_name='Doe'
        )
        
        # Créer un patient
        self.patient = Patient.objects.create(
            orthanc_id='test-patient-id',
            patient_id='PAT001',
            name='Jane Smith',
            birth_date=date(1990, 1, 1),
            sex='F'
        )
        
        # Créer une disponibilité
        DoctorAvailability.objects.create(
            doctor=self.doctor,
            weekday=1,  # Mardi
            start_time=time(9, 0),
            end_time=time(17, 0)
        )
    
    def test_create_appointment(self):
        """Test de création d'un rendez-vous"""
        appointment = Appointment.objects.create(
            patient=self.patient,
            doctor=self.doctor,
            appointment_date=date.today() + timedelta(days=1),
            appointment_time=time(10, 0),
            reason='Consultation de routine',
            duration_minutes=30
        )
        
        self.assertEqual(appointment.status, 'pending')
        self.assertFalse(appointment.is_past)
        self.assertTrue(appointment.can_be_confirmed)
    
    def test_appointment_conflicts(self):
        """Test de détection des conflits"""
        # Créer un premier rendez-vous
        appointment1 = Appointment.objects.create(
            patient=self.patient,
            doctor=self.doctor,
            appointment_date=date.today() + timedelta(days=1),
            appointment_time=time(10, 0),
            reason='Premier RDV',
            duration_minutes=30
        )
        
        # Créer un rendez-vous en conflit
        appointment2 = Appointment(
            patient=self.patient,
            doctor=self.doctor,
            appointment_date=date.today() + timedelta(days=1),
            appointment_time=time(10, 15),  # Se chevauche avec le premier
            reason='Deuxième RDV',
            duration_minutes=30
        )
        
        conflicts = appointment2.get_conflicting_appointments()
        self.assertEqual(len(conflicts), 1)
        self.assertEqual(conflicts[0], appointment1)
    
    def test_available_slots(self):
        """Test de récupération des créneaux disponibles"""
        test_date = date.today() + timedelta(days=1)
        
        # Si c'est un mardi, on devrait avoir des créneaux disponibles
        if test_date.weekday() == 1:
            slots = AppointmentManager.get_available_slots(
                self.doctor, test_date, 30
            )
            self.assertGreater(len(slots), 0)

class AppointmentViewsTestCase(TestCase):
    def setUp(self):
        self.client = Client()
        self.doctor = User.objects.create_user(
            username='dr_test',
            email='doctor@test.com',
            password='testpass123',
            role='doctor'
        )
        
    def test_appointment_list_requires_auth(self):
        """Test que la liste des RDV nécessite une authentification"""
        response = self.client.get('/medical/appointments/')
        self.assertEqual(response.status_code, 302)  # Redirection vers login
    
    def test_doctor_can_access_appointments(self):
        """Test qu'un médecin peut accéder à ses RDV"""
        self.client.login(username='dr_test', password='testpass123')
        response = self.client.get('/medical/appointments/')
        self.assertEqual(response.status_code, 200)