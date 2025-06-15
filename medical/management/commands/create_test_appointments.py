from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import date, time, timedelta
import random
from accounts.models import UserProfile
from dicom_viewer.models import Patient
from medical.models import Appointment, DoctorAvailability

class Command(BaseCommand):
    help = 'Crée des données de test pour les rendez-vous'

    def handle(self, *args, **options):
        # Créer des médecins de test
        doctors = []
        for i in range(3):
            doctor = UserProfile.objects.create_user(
                username=f'doctor{i+1}',
                email=f'doctor{i+1}@test.com',
                password='testpass123',
                role='doctor',
                first_name=f'Docteur{i+1}',
                last_name='Test',
                specialization=['Généraliste', 'Cardiologue', 'Dermatologue'][i]
            )
            doctors.append(doctor)
            
            # Créer des disponibilités
            for day in range(5):  # Lundi à vendredi
                DoctorAvailability.objects.create(
                    doctor=doctor,
                    weekday=day,
                    start_time=time(9, 0),
                    end_time=time(17, 0)
                )

        # Créer des patients de test
        patients = []
        for i in range(10):
            patient = Patient.objects.create(
                orthanc_id=f'test-patient-{i+1}',
                patient_id=f'PAT{i+1:03d}',
                name=f'Patient Test {i+1}',
                birth_date=date(1980 + i, 1, 1),
                sex=['M', 'F'][i % 2]
            )
            patients.append(patient)

        # Créer des rendez-vous de test
        statuses = ['pending', 'confirmed', 'completed', 'cancelled']
        appointment_types = ['consultation', 'followup', 'examination']
        
        for i in range(50):
            # Date aléatoire dans les 30 prochains jours
            days_ahead = random.randint(1, 30)
            appointment_date = date.today() + timedelta(days=days_ahead)
            
            # Heure aléatoire pendant les heures de bureau
            hour = random.randint(9, 16)
            minute = random.choice([0, 30])
            appointment_time = time(hour, minute)
            
            Appointment.objects.create(
                patient=random.choice(patients),
                doctor=random.choice(doctors),
                appointment_date=appointment_date,
                appointment_time=appointment_time,
                appointment_type=random.choice(appointment_types),
                duration_minutes=random.choice([30, 45, 60]),
                status=random.choice(statuses),
                reason=f'Motif de consultation {i+1}',
                notes=f'Notes pour le rendez-vous {i+1}' if random.random() > 0.5 else ''
            )

        self.stdout.write(
            self.style.SUCCESS(
                f'Créé {len(doctors)} médecins, {len(patients)} patients '
                f'et 50 rendez-vous de test'
            )
        )
