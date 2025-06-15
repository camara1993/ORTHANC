from datetime import datetime, timedelta
from django.utils import timezone
from .models import Appointment

class AppointmentManager:
    """Gestionnaire pour les opérations sur les rendez-vous"""
    
    @staticmethod
    def get_available_slots(doctor, date, duration_minutes=30):
        """Retourne les créneaux disponibles pour un médecin à une date donnée"""
        from .models import DoctorAvailability
        
        # Récupérer les disponibilités du médecin pour ce jour
        weekday = date.weekday()
        availabilities = DoctorAvailability.objects.filter(
            doctor=doctor,
            weekday=weekday,
            is_active=True
        )
        
        if not availabilities:
            return []
        
        # Récupérer les rendez-vous existants
        existing_appointments = Appointment.objects.filter(
            doctor=doctor,
            appointment_date=date,
            status__in=['pending', 'confirmed']
        )
        
        available_slots = []
        
        for availability in availabilities:
            current_time = datetime.combine(date, availability.start_time)
            end_time = datetime.combine(date, availability.end_time)
            
            while current_time + timedelta(minutes=duration_minutes) <= end_time:
                slot_start = current_time.time()
                slot_end = (current_time + timedelta(minutes=duration_minutes)).time()
                
                # Vérifier s'il y a un conflit
                has_conflict = False
                for appointment in existing_appointments:
                    apt_start = datetime.combine(date, appointment.appointment_time)
                    apt_end = apt_start + timedelta(minutes=appointment.duration_minutes)
                    
                    if (current_time < apt_end and 
                        current_time + timedelta(minutes=duration_minutes) > apt_start):
                        has_conflict = True
                        break
                
                if not has_conflict:
                    available_slots.append({
                        'time': slot_start,
                        'time_str': slot_start.strftime('%H:%M'),
                        'available': True
                    })
                
                current_time += timedelta(minutes=30)  # Intervalle de 30 minutes
        
        return available_slots
    
    @staticmethod
    def bulk_update_status(appointment_ids, new_status, user):
        """Met à jour le statut de plusieurs rendez-vous"""
        appointments = Appointment.objects.filter(
            id__in=appointment_ids,
            doctor=user if user.role == 'doctor' else None
        )
        
        updated_count = 0
        for appointment in appointments:
            if appointment.status != new_status:
                appointment.status = new_status
                appointment.save()
                
                # Envoyer notification si nécessaire
                if new_status == 'confirmed':
                    appointment.send_notification('confirmed')
                elif new_status == 'cancelled':
                    appointment.send_notification('cancelled')
                
                updated_count += 1
        
        return updated_count
    
    @staticmethod
    def get_doctor_statistics(doctor, start_date=None, end_date=None):
        """Retourne les statistiques d'un médecin"""
        if not start_date:
            start_date = timezone.now().date().replace(day=1)  # Début du mois
        if not end_date:
            end_date = timezone.now().date()
        
        appointments = Appointment.objects.filter(
            doctor=doctor,
            appointment_date__gte=start_date,
            appointment_date__lte=end_date
        )
        
        stats = {
            'total': appointments.count(),
            'pending': appointments.filter(status='pending').count(),
            'confirmed': appointments.filter(status='confirmed').count(),
            'completed': appointments.filter(status='completed').count(),
            'cancelled': appointments.filter(status='cancelled').count(),
            'no_show': appointments.filter(status='no_show').count(),
        }
        
        # Taux de réussite
        total_scheduled = stats['confirmed'] + stats['completed'] + stats['no_show']
        if total_scheduled > 0:
            stats['completion_rate'] = round((stats['completed'] / total_scheduled) * 100, 1)
            stats['no_show_rate'] = round((stats['no_show'] / total_scheduled) * 100, 1)
        else:
            stats['completion_rate'] = 0
            stats['no_show_rate'] = 0
        
        return stats
    
    @staticmethod
    def get_doctor_today_appointments(doctor):
        """Retourne les rendez-vous du jour pour un médecin"""
        from django.utils import timezone
        from .models import Appointment
        
        today = timezone.now().date()
        return Appointment.objects.filter(
            doctor=doctor,
            appointment_date=today
        ).order_by('appointment_time')
    @staticmethod
    def get_doctor_pending_appointments(doctor):
        """Retourne les rendez-vous en attente pour un médecin"""
        from .models import Appointment
        
        return Appointment.objects.filter(
            doctor=doctor,
            status='pending'
        ).order_by('appointment_date', 'appointment_time')