from django.db import models
from django.conf import settings
from django.core.validators import MinValueValidator
from dicom_viewer.models import Patient
import uuid

class Prescription(models.Model):
    """Ordonnances médicales"""
    FREQUENCY_CHOICES = [
        ('1/jour', 'Une fois par jour'),
        ('2/jour', 'Deux fois par jour'),
        ('3/jour', 'Trois fois par jour'),
        ('4/jour', 'Quatre fois par jour'),
        ('1/semaine', 'Une fois par semaine'),
        ('si_besoin', 'Si besoin'),
        ('autre', 'Autre'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    doctor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name='prescriptions_written',
        limit_choices_to={'role': 'doctor'}
    )
    patient = models.ForeignKey(
        Patient,
        on_delete=models.CASCADE,
        related_name='prescriptions'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    valid_until = models.DateField()
    is_active = models.BooleanField(default=True)
    notes = models.TextField(blank=True, help_text="Instructions spéciales")
    
    class Meta:
        db_table = 'prescriptions'
        ordering = ['-created_at']
        permissions = [
            ("can_prescribe", "Can create prescriptions"),
        ]
    
    def __str__(self):
        return f"Ordonnance de {self.patient.name} par Dr. {self.doctor.get_full_name()}"
    
    @property
    def is_expired(self):
        from django.utils import timezone
        return self.valid_until < timezone.now().date()


class PrescriptionItem(models.Model):
    """Lignes de prescription (médicaments)"""
    prescription = models.ForeignKey(
        Prescription,
        on_delete=models.CASCADE,
        related_name='items'
    )
    medication_name = models.CharField(max_length=200)
    dosage = models.CharField(max_length=100)
    frequency = models.CharField(max_length=50, choices=Prescription.FREQUENCY_CHOICES)
    duration = models.CharField(max_length=100, help_text="Ex: 7 jours, 1 mois")
    quantity = models.IntegerField(validators=[MinValueValidator(1)])
    instructions = models.TextField(blank=True)
    
    class Meta:
        db_table = 'prescription_items'
        ordering = ['id']
    
    def __str__(self):
        return f"{self.medication_name} - {self.dosage}"


class Appointment(models.Model):
    """Rendez-vous médicaux"""
    STATUS_CHOICES = [
        ('pending', 'En attente'),
        ('confirmed', 'Confirmé'),
        ('cancelled', 'Annulé'),
        ('completed', 'Terminé'),
        ('no_show', 'Absent'),
    ]
    
    APPOINTMENT_TYPE_CHOICES = [
        ('consultation', 'Consultation'),
        ('followup', 'Suivi'),
        ('examination', 'Examen'),
        ('emergency', 'Urgence'),
        ('teleconsultation', 'Téléconsultation'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    patient = models.ForeignKey(
        Patient,
        on_delete=models.CASCADE,
        related_name='appointments'
    )
    doctor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='appointments',
        limit_choices_to={'role': 'doctor'}
    )
    appointment_date = models.DateField()
    appointment_time = models.TimeField()
    appointment_type = models.CharField(
        max_length=20,
        choices=APPOINTMENT_TYPE_CHOICES,
        default='consultation'
    )
    duration_minutes = models.IntegerField(default=30)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    reason = models.TextField(help_text="Motif de consultation")
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='appointments_created'
    )
    
    class Meta:
        db_table = 'appointments'
        ordering = ['appointment_date', 'appointment_time']
        unique_together = ['doctor', 'appointment_date', 'appointment_time']
    
    def __str__(self):
        return f"RDV {self.patient.name} - {self.appointment_date} {self.appointment_time}"
    
    @property
    def is_past(self):
        from django.utils import timezone
        appointment_datetime = timezone.datetime.combine(
            self.appointment_date,
            self.appointment_time
        )
        return timezone.make_aware(appointment_datetime) < timezone.now()
    
    @property
    def end_time(self):
        from datetime import datetime, timedelta
        start = datetime.combine(self.appointment_date, self.appointment_time)
        end = start + timedelta(minutes=self.duration_minutes)
        return end.time()
    
    @property
    def can_be_confirmed(self):
        """Vérifie si le rendez-vous peut être confirmé"""
        return self.status == 'pending' and not self.is_past
    
    @property
    def can_be_cancelled(self):
        """Vérifie si le rendez-vous peut être annulé"""
        return self.status in ['pending', 'confirmed'] and not self.is_past
    
    @property
    def can_be_completed(self):
        """Vérifie si le rendez-vous peut être marqué comme terminé"""
        return self.status == 'confirmed'
    
    @property
    def can_be_rescheduled(self):
        """Vérifie si le rendez-vous peut être reprogrammé"""
        return self.status in ['pending', 'confirmed'] and not self.is_past
    
    @property
    def time_until_appointment(self):
        """Retourne le temps restant jusqu'au rendez-vous"""
        from django.utils import timezone
        appointment_datetime = timezone.datetime.combine(
            self.appointment_date,
            self.appointment_time
        )
        appointment_datetime = timezone.make_aware(appointment_datetime)
        
        if appointment_datetime > timezone.now():
            delta = appointment_datetime - timezone.now()
            
            if delta.days > 0:
                return f"Dans {delta.days} jour{'s' if delta.days > 1 else ''}"
            elif delta.seconds > 3600:
                hours = delta.seconds // 3600
                return f"Dans {hours}h"
            elif delta.seconds > 60:
                minutes = delta.seconds // 60
                return f"Dans {minutes}min"
            else:
                return "Imminent"
        else:
            return "Passé"
    
    @property
    def duration_display(self):
        """Affichage formaté de la durée"""
        if self.duration_minutes >= 60:
            hours = self.duration_minutes // 60
            minutes = self.duration_minutes % 60
            if minutes > 0:
                return f"{hours}h{minutes:02d}"
            else:
                return f"{hours}h"
        else:
            return f"{self.duration_minutes}min"
    
    def get_conflicting_appointments(self):
        """Retourne les rendez-vous en conflit avec celui-ci"""
        from datetime import datetime, timedelta
        
        start_time = datetime.combine(self.appointment_date, self.appointment_time)
        end_time = start_time + timedelta(minutes=self.duration_minutes)
        
        conflicts = Appointment.objects.filter(
            doctor=self.doctor,
            appointment_date=self.appointment_date,
            status__in=['pending', 'confirmed']
        ).exclude(id=self.id if self.id else None)
        
        conflicting = []
        for appointment in conflicts:
            other_start = datetime.combine(appointment.appointment_date, appointment.appointment_time)
            other_end = other_start + timedelta(minutes=appointment.duration_minutes)
            
            # Vérifier si les créneaux se chevauchent
            if (start_time < other_end and end_time > other_start):
                conflicting.append(appointment)
        
        return conflicting
    
    def has_conflicts(self):
        """Vérifie s'il y a des conflits"""
        return len(self.get_conflicting_appointments()) > 0
    
    def get_status_color(self):
        """Retourne la couleur CSS selon le statut"""
        colors = {
            'pending': 'warning',
            'confirmed': 'success',
            'cancelled': 'danger',
            'completed': 'primary',
            'no_show': 'secondary'
        }
        return colors.get(self.status, 'secondary')
    
    def get_type_icon(self):
        """Retourne l'icône selon le type de rendez-vous"""
        icons = {
            'consultation': 'fas fa-stethoscope',
            'followup': 'fas fa-redo',
            'examination': 'fas fa-search',
            'emergency': 'fas fa-exclamation-triangle',
            'teleconsultation': 'fas fa-video'
        }
        return icons.get(self.appointment_type, 'fas fa-calendar')
    
    def send_notification(self, notification_type='created'):
        """Envoie une notification pour ce rendez-vous"""
        from django.core.mail import send_mail
        from django.template.loader import render_to_string
        from django.conf import settings
        
        if not self.patient.user or not self.patient.user.email:
            return False
        
        context = {
            'appointment': self,
            'patient': self.patient,
            'doctor': self.doctor,
        }
        
        subjects = {
            'created': f"Nouveau rendez-vous avec Dr. {self.doctor.get_full_name()}",
            'confirmed': f"Rendez-vous confirmé - Dr. {self.doctor.get_full_name()}",
            'cancelled': f"Rendez-vous annulé - Dr. {self.doctor.get_full_name()}",
            'reminder': f"Rappel: RDV demain avec Dr. {self.doctor.get_full_name()}"
        }
        
        try:
            subject = subjects.get(notification_type, "Notification de rendez-vous")
            message = render_to_string(f'medical/emails/appointment_{notification_type}.html', context)
            
            send_mail(
                subject,
                message,
                settings.DEFAULT_FROM_EMAIL,
                [self.patient.user.email],
                html_message=message,
                fail_silently=True,
            )
            return True
        except Exception as e:
            print(f"Erreur envoi email: {e}")
            return False
    class Meta:
        db_table = 'appointments'
        ordering = ['appointment_date', 'appointment_time']
        unique_together = ['doctor', 'appointment_date', 'appointment_time']
        indexes = [
            models.Index(fields=['appointment_date', 'status']),
            models.Index(fields=['doctor', 'appointment_date']),
            models.Index(fields=['patient', 'appointment_date']),
        ]




class DoctorAvailability(models.Model):
    """Disponibilités des médecins"""
    WEEKDAYS = [
        (0, 'Lundi'),
        (1, 'Mardi'),
        (2, 'Mercredi'),
        (3, 'Jeudi'),
        (4, 'Vendredi'),
        (5, 'Samedi'),
        (6, 'Dimanche'),
    ]
    
    doctor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='availabilities',
        limit_choices_to={'role': 'doctor'}
    )
    weekday = models.IntegerField(choices=WEEKDAYS)
    start_time = models.TimeField()
    end_time = models.TimeField()
    is_active = models.BooleanField(default=True)
    
    class Meta:
        db_table = 'doctor_availabilities'
        unique_together = ['doctor', 'weekday', 'start_time']
        ordering = ['weekday', 'start_time']
    
    def __str__(self):
        return f"{self.doctor.get_full_name()} - {self.get_weekday_display()} {self.start_time}-{self.end_time}"