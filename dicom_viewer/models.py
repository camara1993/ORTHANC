from django.db import models
from django.conf import settings
from django.utils import timezone

class Patient(models.Model):
    orthanc_id = models.CharField(max_length=100, unique=True)
    patient_id = models.CharField(max_length=100)
    name = models.CharField(max_length=200)
    birth_date = models.DateField(null=True, blank=True)
    sex = models.CharField(max_length=10, blank=True)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True,
        related_name='patient_records'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'patients'
        ordering = ['-created_at']

    # Ajouter ces méthodes à la classe Patient

    def get_age(self):
        """Retourne l'âge du patient"""
        if not self.birth_date:
            return None
        
        today = timezone.now().date()
        age = today.year - self.birth_date.year - ((today.month, today.day) < (self.birth_date.month, self.birth_date.day))
        return age

    def get_active_prescriptions(self):
        """Retourne les prescriptions actives du patient"""
        from medical.models import Prescription
        return self.prescriptions.filter(
            is_active=True,
            valid_until__gte=timezone.now().date()
        )

    def get_upcoming_appointments(self):
        """Retourne les prochains rendez-vous du patient"""
        from medical.models import Appointment
        return self.appointments.filter(
            appointment_date__gte=timezone.now().date(),
            status__in=['pending', 'confirmed']
        ).order_by('appointment_date', 'appointment_time')

class Study(models.Model):
    orthanc_id = models.CharField(max_length=100, unique=True)
    study_instance_uid = models.CharField(max_length=200)
    patient = models.ForeignKey(Patient, on_delete=models.CASCADE, related_name='studies')
    study_date = models.DateField(null=True, blank=True)
    study_time = models.TimeField(null=True, blank=True)
    study_description = models.TextField(blank=True)
    accession_number = models.CharField(max_length=100, blank=True)
    referring_physician = models.CharField(max_length=200, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'studies'
        ordering = ['-study_date', '-study_time']

class Series(models.Model):
    orthanc_id = models.CharField(max_length=100, unique=True)
    series_instance_uid = models.CharField(max_length=200)
    study = models.ForeignKey(Study, on_delete=models.CASCADE, related_name='series')
    modality = models.CharField(max_length=20)
    series_number = models.IntegerField(null=True, blank=True)
    series_description = models.TextField(blank=True)
    body_part = models.CharField(max_length=100, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'series'
        ordering = ['series_number']

class Instance(models.Model):
    orthanc_id = models.CharField(max_length=100, unique=True)
    sop_instance_uid = models.CharField(max_length=200)
    series = models.ForeignKey(Series, on_delete=models.CASCADE, related_name='instances')
    instance_number = models.IntegerField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'instances'
        ordering = ['instance_number']

class AccessLog(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    patient = models.ForeignKey(Patient, on_delete=models.CASCADE, null=True, blank=True)
    study = models.ForeignKey(Study, on_delete=models.CASCADE, null=True, blank=True)
    action = models.CharField(max_length=50)
    timestamp = models.DateTimeField(auto_now_add=True)
    ip_address = models.GenericIPAddressField()

    # Si vous voulez ajouter un champ details, ajoutez :
    details = models.TextField(blank=True, null=True)
    
    class Meta:
        db_table = 'access_logs'
        ordering = ['-timestamp']

class DoctorPatientRelation(models.Model):
    """Relation entre médecin et patient"""
    doctor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='doctor_patients',
        limit_choices_to={'role': 'doctor'}
    )
    patient = models.ForeignKey(
        Patient,
        on_delete=models.CASCADE,
        related_name='patient_doctors'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    is_active = models.BooleanField(default=True)
    notes = models.TextField(blank=True)
    
    class Meta:
        db_table = 'doctor_patient_relations'
        unique_together = ['doctor', 'patient']
        ordering = ['-created_at']
    
    def __str__(self):
        return f"Dr. {self.doctor.get_full_name()} - {self.patient.name}"