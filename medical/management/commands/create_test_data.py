from django.core.management.base import BaseCommand
from django.utils import timezone
from accounts.models import UserProfile
from dicom_viewer.models import Patient, DoctorPatientRelation
from medical.models import DoctorAvailability
from datetime import time

class Command(BaseCommand):
    help = 'Crée des données de test pour les fonctionnalités médicales'
    
    def handle(self, *args, **options):
        self.stdout.write('Création des données de test...')
        
        # Créer un médecin de test
        doctor, created = UserProfile.objects.get_or_create(
            username='dr.martin',
            defaults={
                'email': 'dr.martin@example.com',
                'first_name': 'Jean',
                'last_name': 'Martin',
                'role': 'doctor',
                'specialization': 'Médecine Générale',
                'license_number': 'MED123456',
            }
        )
        
        if created:
            doctor.set_password('test123')
            doctor.save()
            self.stdout.write(self.style.SUCCESS(f'Médecin créé: {doctor.username}'))
        
        # Créer des disponibilités pour le médecin
        weekdays = [0, 1, 2, 3, 4]  # Lundi à Vendredi
        for day in weekdays:
            # Matin
            DoctorAvailability.objects.get_or_create(
                doctor=doctor,
                weekday=day,
                start_time=time(9, 0),
                defaults={'end_time': time(12, 0)}
            )
            # Après-midi
            DoctorAvailability.objects.get_or_create(
                doctor=doctor,
                weekday=day,
                start_time=time(14, 0),
                defaults={'end_time': time(18, 0)}
            )
        
        # Créer des relations médecin-patient
        patients = Patient.objects.all()[:5]  # Les 5 premiers patients
        for patient in patients:
            relation, created = DoctorPatientRelation.objects.get_or_create(
                doctor=doctor,
                patient=patient
            )
            if created:
                self.stdout.write(self.style.SUCCESS(f'Relation créée: Dr. {doctor.last_name} - {patient.name}'))
        
        self.stdout.write(self.style.SUCCESS('Données de test créées avec succès!'))