from django import template
from django.utils import timezone

register = template.Library()

@register.filter
def status_color(status):
    """Retourne la couleur Bootstrap pour un statut de rendez-vous"""
    colors = {
        'pending': 'warning',
        'confirmed': 'success',
        'cancelled': 'danger',
        'completed': 'secondary',
        'no_show': 'dark',
    }
    return colors.get(status, 'primary')

@register.filter
def time_until(appointment_date):
    """Retourne le temps restant jusqu'au rendez-vous"""
    if not appointment_date:
        return ""
    
    now = timezone.now().date()
    delta = appointment_date - now
    
    if delta.days < 0:
        return "Passé"
    elif delta.days == 0:
        return "Aujourd'hui"
    elif delta.days == 1:
        return "Demain"
    else:
        return f"Dans {delta.days} jours"

@register.filter
def age_from_birthdate(birth_date):
    """Calcule l'âge à partir de la date de naissance"""
    if not birth_date:
        return None
    
    today = timezone.now().date()
    age = today.year - birth_date.year - ((today.month, today.day) < (birth_date.month, birth_date.day))
    return age

@register.simple_tag
def get_appointment_count(doctor, date=None):
    """Retourne le nombre de rendez-vous pour un médecin à une date donnée"""
    from medical.models import Appointment
    
    queryset = Appointment.objects.filter(
        doctor=doctor,
        status__in=['pending', 'confirmed']
    )
    
    if date:
        queryset = queryset.filter(appointment_date=date)
    
    return queryset.count()