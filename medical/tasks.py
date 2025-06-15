from celery import shared_task
from django.utils import timezone
from datetime import timedelta
from .models import Appointment

@shared_task
def send_appointment_reminders():
    """Envoie des rappels de rendez-vous pour le lendemain"""
    tomorrow = timezone.now().date() + timedelta(days=1)
    
    appointments = Appointment.objects.filter(
        appointment_date=tomorrow,
        status='confirmed'
    )
    
    sent_count = 0
    for appointment in appointments:
        if appointment.send_notification('reminder'):
            sent_count += 1
    
    return f"Rappels envoyés: {sent_count}"

@shared_task
def cleanup_old_appointments():
    """Nettoie les anciens rendez-vous annulés"""
    cutoff_date = timezone.now().date() - timedelta(days=90)
    
    deleted_count = Appointment.objects.filter(
        status='cancelled',
        appointment_date__lt=cutoff_date
    ).delete()[0]
    
    return f"Rendez-vous supprimés: {deleted_count}"

@shared_task
def update_missed_appointments():
    """Met à jour les rendez-vous manqués"""
    yesterday = timezone.now().date() - timedelta(days=1)
    
    missed_appointments = Appointment.objects.filter(
        appointment_date=yesterday,
        status='confirmed'
    )
    
    updated_count = missed_appointments.update(status='no_show')
    return f"Rendez-vous marqués comme manqués: {updated_count}"