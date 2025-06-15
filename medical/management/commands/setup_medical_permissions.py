from django.core.management.base import BaseCommand
from django.contrib.auth.models import Group, Permission
from django.contrib.contenttypes.models import ContentType
from medical.models import Appointment, Prescription

class Command(BaseCommand):
    help = 'Configure les permissions pour le module médical'

    def handle(self, *args, **options):
        # Créer les groupes
        doctors_group, created = Group.objects.get_or_create(name='Médecins')
        patients_group, created = Group.objects.get_or_create(name='Patients')
        
        # Permissions pour les médecins
        appointment_ct = ContentType.objects.get_for_model(Appointment)
        prescription_ct = ContentType.objects.get_for_model(Prescription)
        
        doctor_permissions = [
            Permission.objects.get_or_create(
                codename='can_manage_appointments',
                name='Can manage appointments',
                content_type=appointment_ct
            )[0],
            Permission.objects.get_or_create(
                codename='can_prescribe',
                name='Can create prescriptions',
                content_type=prescription_ct
            )[0],
        ]
        
        doctors_group.permissions.set(doctor_permissions)
        
        self.stdout.write(
            self.style.SUCCESS('Permissions configurées avec succès')
        )