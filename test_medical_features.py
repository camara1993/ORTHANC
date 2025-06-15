#!/usr/bin/env python
"""
Script de test pour les fonctionnalités médicales
"""
import os
import sys
import django

# Configuration Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'orthanc_client.settings')
django.setup()

from django.utils import timezone
from datetime import date, time, timedelta
from accounts.models import UserProfile
from dicom_viewer.models import Patient, DoctorPatientRelation
from medical.models import Prescription, PrescriptionItem, Appointment, DoctorAvailability

def create_test_users():
    """Créer les utilisateurs de test"""
    print("📌 Création des utilisateurs de test...")
    
    # Admin
    admin, _ = UserProfile.objects.get_or_create(
        username='admin',
        defaults={
            'email': 'admin@example.com',
            'first_name': 'Admin',
            'last_name': 'System',
            'role': 'admin',
            'is_staff': True,
            'is_superuser': True,
        }
    )
    admin.set_password('admin123')
    admin.save()
    print(f"✅ Admin créé: {admin.username}")
    
    # Médecin
    doctor, _ = UserProfile.objects.get_or_create(
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
    doctor.set_password('doctor123')
    doctor.save()
    print(f"✅ Médecin créé: {doctor.username}")
    
    # Patient
    patient_user, _ = UserProfile.objects.get_or_create(
        username='patient1',
        defaults={
            'email': 'patient1@example.com',
            'first_name': 'Marie',
            'last_name': 'Dupont',
            'role': 'patient',
        }
    )
    patient_user.set_password('patient123')
    patient_user.save()
    print(f"✅ Patient créé: {patient_user.username}")
    
    return admin, doctor, patient_user

def create_test_patient_record(patient_user):
    """Créer un dossier patient"""
    print("\n📌 Création du dossier patient...")
    
    patient, _ = Patient.objects.get_or_create(
        patient_id='PAT001',
        defaults={
            'name': f"{patient_user.first_name} {patient_user.last_name}",
            'birth_date': date(1990, 5, 15),
            'sex': 'F',
            'user': patient_user,
            'orthanc_id': 'test-orthanc-id',
        }
    )
    print(f"✅ Dossier patient créé: {patient.name}")
    
    return patient

def create_doctor_patient_relation(doctor, patient):
    """Créer la relation médecin-patient"""
    print("\n📌 Création de la relation médecin-patient...")
    
    relation, _ = DoctorPatientRelation.objects.get_or_create(
        doctor=doctor,
        patient=patient,
        defaults={
            'is_active': True,
            'notes': 'Patient suivi régulièrement',
        }
    )
    print(f"✅ Relation créée: Dr. {doctor.last_name} - {patient.name}")
    
    return relation

def create_doctor_availability(doctor):
    """Créer les disponibilités du médecin"""
    print("\n📌 Création des disponibilités du médecin...")
    
    # Lundi à Vendredi, 9h-12h et 14h-18h
    for day in range(5):  # 0=Lundi, 4=Vendredi
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
    
    print("✅ Disponibilités créées: Lun-Ven 9h-12h et 14h-18h")

def create_test_prescription(doctor, patient):
    """Créer une ordonnance de test"""
    print("\n📌 Création d'une ordonnance de test...")
    
    prescription = Prescription.objects.create(
        doctor=doctor,
        patient=patient,
        valid_until=timezone.now().date() + timedelta(days=30),
        notes="Prendre les médicaments pendant les repas. Revenir si les symptômes persistent."
    )
    
    # Ajouter des médicaments
    medications = [
        {
            'medication_name': 'Paracétamol',
            'dosage': '500mg',
            'frequency': '3/jour',
            'duration': '7 jours',
            'quantity': 21,
            'instructions': 'En cas de douleur ou fièvre'
        },
        {
            'medication_name': 'Amoxicilline',
            'dosage': '1g',
            'frequency': '2/jour',
            'duration': '7 jours',
            'quantity': 14,
            'instructions': 'Antibiotique - Prendre pendant les repas'
        },
    ]
    
    for med in medications:
        PrescriptionItem.objects.create(prescription=prescription, **med)
    
    print(f"✅ Ordonnance créée avec {len(medications)} médicaments")
    
    return prescription

def create_test_appointment(doctor, patient):
    """Créer un rendez-vous de test"""
    print("\n📌 Création d'un rendez-vous de test...")
    
    # Rendez-vous dans 3 jours à 10h
    appointment_date = timezone.now().date() + timedelta(days=3)
    
    appointment = Appointment.objects.create(
        patient=patient,
        doctor=doctor,
        appointment_date=appointment_date,
        appointment_time=time(10, 0),
        appointment_type='consultation',
        duration_minutes=30,
        status='pending',
        reason="Consultation de suivi",
        created_by=patient.user,
    )
    
    print(f"✅ Rendez-vous créé: {appointment_date} à 10h00")
    
    return appointment

def main():
    print("🚀 Démarrage du script de test des fonctionnalités médicales\n")
    
    # Créer les utilisateurs
    admin, doctor, patient_user = create_test_users()
    
    # Créer le dossier patient
    patient = create_test_patient_record(patient_user)
    
    # Créer la relation médecin-patient
    create_doctor_patient_relation(doctor, patient)
    
    # Créer les disponibilités du médecin
    create_doctor_availability(doctor)
    
    # Créer une ordonnance
    create_test_prescription(doctor, patient)
    
    # Créer un rendez-vous
    create_test_appointment(doctor, patient)
    
    print("\n✅ Toutes les données de test ont été créées avec succès!")
    print("\n📋 Comptes de test créés:")
    print("- Admin: admin / admin123")
    print("- Médecin: dr.martin / doctor123")
    print("- Patient: patient1 / patient123")
    print("\n🎯 Vous pouvez maintenant tester les fonctionnalités!")

if __name__ == '__main__':
    main()