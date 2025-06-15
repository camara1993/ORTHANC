from django import template
from dicom_viewer.models import DoctorPatientRelation

register = template.Library()

@register.filter
def is_my_patient(patient, doctor):
    """Vérifie si un patient est assigné à un médecin"""
    if not doctor or doctor.role != 'doctor':
        return False
    
    return DoctorPatientRelation.objects.filter(
        doctor=doctor,
        patient=patient,
        is_active=True
    ).exists()

@register.filter
def has_active_prescription(patient):
    """Vérifie si le patient a des prescriptions actives"""
    from medical.models import Prescription
    from django.utils import timezone
    
    return Prescription.objects.filter(
        patient=patient,
        is_active=True,
        valid_until__gte=timezone.now().date()
    ).exists()