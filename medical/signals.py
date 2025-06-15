from django.db.models.signals import post_save
from django.dispatch import receiver
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.conf import settings
from .models import Appointment, Prescription

@receiver(post_save, sender=Appointment)
def send_appointment_notification(sender, instance, created, **kwargs):
    """Envoie une notification lors de la création/modification d'un rendez-vous"""
    if created and instance.patient.user and instance.patient.user.email:
        # Email au patient
        subject = f"Nouveau rendez-vous avec Dr. {instance.doctor.get_full_name()}"
        message = render_to_string('medical/emails/appointment_created.html', {
            'appointment': instance,
        })
        
        try:
            send_mail(
                subject,
                message,
                settings.DEFAULT_FROM_EMAIL,
                [instance.patient.user.email],
                html_message=message,
                fail_silently=True,
            )
        except Exception as e:
            print(f"Erreur envoi email: {e}")
    
    elif not created and instance.status == 'confirmed':
        # Notification de confirmation
        if instance.patient.user and instance.patient.user.email:
            subject = "Rendez-vous confirmé"
            message = f"Votre rendez-vous du {instance.appointment_date} à {instance.appointment_time} avec Dr. {instance.doctor.get_full_name()} est confirmé."
            
            try:
                send_mail(
                    subject,
                    message,
                    settings.DEFAULT_FROM_EMAIL,
                    [instance.patient.user.email],
                    fail_silently=True,
                )
            except Exception as e:
                print(f"Erreur envoi email: {e}")

@receiver(post_save, sender=Prescription)
def send_prescription_notification(sender, instance, created, **kwargs):
    """Envoie une notification lors de la création d'une prescription"""
    if created and instance.patient.user and instance.patient.user.email:
        subject = "Nouvelle ordonnance disponible"
        message = render_to_string('medical/emails/prescription_created.html', {
            'prescription': instance,
        })
        
        try:
            send_mail(
                subject,
                message,
                settings.DEFAULT_FROM_EMAIL,
                [instance.patient.user.email],
                html_message=message,
                fail_silently=True,
            )
        except Exception as e:
            print(f"Erreur envoi email: {e}")