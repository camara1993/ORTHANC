# medical/views.py - Mise à jour complète
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from django.core.paginator import Paginator
from django.db.models import Q, Count
from django.utils import timezone
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_exempt
from datetime import datetime, timedelta
import json

from .models import Appointment, Prescription, DoctorAvailability
from dicom_viewer.models import Patient, AccessLog
from accounts.models import UserProfile

from django.utils.decorators import method_decorator
from django.views.decorators.cache import cache_page
from .utils import AppointmentManager
import uuid

def log_access(user, action, details=None, patient=None):
    """Helper function to log user actions"""
    AccessLog.objects.create(
        user=user,
        action=action,
        details=details,
        patient=patient,
        ip_address='127.0.0.1'  # You can get real IP from request.META
    )

@login_required
def prescription_list(request):
    """Liste des prescriptions selon le rôle"""
    user = request.user
    
    if user.role == 'patient':
        # Patient voit ses propres prescriptions
        try:
            patient = Patient.objects.get(user=user)
            prescriptions = patient.prescriptions.all().order_by('-created_at')
        except Patient.DoesNotExist:
            prescriptions = Prescription.objects.none()
    elif user.role == 'doctor':
        # Médecin voit les prescriptions qu'il a créées
        prescriptions = user.prescriptions_written.all().order_by('-created_at')
    elif user.role == 'admin':
        # Admin voit toutes les prescriptions
        prescriptions = Prescription.objects.all().order_by('-created_at')
    else:
        prescriptions = Prescription.objects.none()
    
    # Pagination
    paginator = Paginator(prescriptions, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'page_obj': page_obj,
        'total_prescriptions': paginator.count,
    }
    
    return render(request, 'medical/prescription_list.html', context)

@login_required
def appointment_list(request):
    """Liste des rendez-vous avec filtres et statuts"""
    user = request.user
    
    # Filtrer selon le rôle
    if user.role == 'patient':
        try:
            patient = Patient.objects.get(user=user)
            appointments = patient.appointments.all()
        except Patient.DoesNotExist:
            appointments = Appointment.objects.none()
    elif user.role == 'doctor':
        appointments = user.appointments.all()
    elif user.role == 'admin':
        appointments = Appointment.objects.all()
    else:
        appointments = Appointment.objects.none()
    
    # Filtres
    status_filter = request.GET.get('status', '')
    date_filter = request.GET.get('date', '')
    search_query = request.GET.get('search', '')
    
    if status_filter:
        appointments = appointments.filter(status=status_filter)
    
    if date_filter:
        if date_filter == 'today':
            appointments = appointments.filter(appointment_date=timezone.now().date())
        elif date_filter == 'week':
            start_week = timezone.now().date()
            end_week = start_week + timedelta(days=7)
            appointments = appointments.filter(
                appointment_date__gte=start_week,
                appointment_date__lte=end_week
            )
        elif date_filter == 'month':
            start_month = timezone.now().date().replace(day=1)
            appointments = appointments.filter(appointment_date__gte=start_month)
    
    if search_query:
        appointments = appointments.filter(
            Q(patient__name__icontains=search_query) |
            Q(reason__icontains=search_query) |
            Q(doctor__first_name__icontains=search_query) |
            Q(doctor__last_name__icontains=search_query)
        )
    
    # Annotations et tri
    appointments = appointments.select_related('patient', 'doctor').order_by(
        'appointment_date', 'appointment_time'
    )
    
    # Statistiques pour les médecins
    stats = {}
    if user.role == 'doctor':
        today = timezone.now().date()
        stats = {
            'today_count': user.appointments.filter(appointment_date=today).count(),
            'pending_count': user.appointments.filter(status='pending').count(),
            'confirmed_count': user.appointments.filter(status='confirmed').count(),
            'total_week': user.appointments.filter(
                appointment_date__gte=today,
                appointment_date__lte=today + timedelta(days=7)
            ).count(),
        }
    
    # Pagination
    paginator = Paginator(appointments, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'page_obj': page_obj,
        'total_appointments': paginator.count,
        'status_filter': status_filter,
        'date_filter': date_filter,
        'search_query': search_query,
        'stats': stats,
        'status_choices': Appointment.STATUS_CHOICES,
    }
    
    return render(request, 'medical/appointment_list.html', context)

@login_required
def appointment_detail(request, appointment_id):
    """Détail d'un rendez-vous"""
    appointment = get_object_or_404(Appointment, pk=appointment_id)
    
    # Vérifier les permissions
    if request.user.role == 'patient' and appointment.patient.user != request.user:
        messages.error(request, "Accès non autorisé")
        return redirect('medical:appointment_list')
    elif request.user.role == 'doctor' and appointment.doctor != request.user:
        messages.error(request, "Accès non autorisé")
        return redirect('medical:appointment_list')
    
    context = {
        'appointment': appointment,
    }
    
    return render(request, 'medical/appointment_detail.html', context)

@login_required
@require_http_methods(["POST"])
def update_appointment_status(request, appointment_id):
    """Mettre à jour le statut d'un rendez-vous (AJAX)"""
    try:
        appointment = get_object_or_404(Appointment, pk=appointment_id)
        
        # Seul le médecin peut changer le statut
        if request.user != appointment.doctor and request.user.role != 'admin':
            return JsonResponse({
                'success': False,
                'error': 'Seul le médecin peut modifier le statut du rendez-vous'
            }, status=403)
        
        data = json.loads(request.body)
        new_status = data.get('status')
        notes = data.get('notes', '')
        
        # Valider le nouveau statut
        valid_statuses = [choice[0] for choice in Appointment.STATUS_CHOICES]
        if new_status not in valid_statuses:
            return JsonResponse({
                'success': False,
                'error': 'Statut invalide'
            }, status=400)
        
        # Mettre à jour le rendez-vous
        old_status = appointment.status
        appointment.status = new_status
        if notes:
            appointment.notes = notes
        appointment.save()
        
        # Logger l'action
        log_access(
            request.user,
            'update_appointment_status',
            details=f"Rendez-vous {appointment.id} : {old_status} → {new_status}",
            patient=appointment.patient
        )
        
        # Message de succès
        status_messages = {
            'confirmed': 'Rendez-vous confirmé',
            'cancelled': 'Rendez-vous annulé',
            'completed': 'Rendez-vous marqué comme terminé',
            'no_show': 'Patient marqué comme absent',
            'pending': 'Rendez-vous remis en attente'
        }
        
        message = status_messages.get(new_status, 'Statut mis à jour')
        
        return JsonResponse({
            'success': True,
            'message': message,
            'new_status': new_status,
            'status_display': appointment.get_status_display()
        })
        
    except json.JSONDecodeError:
        return JsonResponse({
            'success': False,
            'error': 'Données JSON invalides'
        }, status=400)
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)

@login_required
def doctor_schedule(request):
    """Planning du médecin avec ses rendez-vous"""
    if request.user.role != 'doctor':
        messages.error(request, "Accès réservé aux médecins")
        return redirect('core:home')
    
    # Date sélectionnée (par défaut aujourd'hui)
    selected_date = request.GET.get('date')
    if selected_date:
        try:
            selected_date = datetime.strptime(selected_date, '%Y-%m-%d').date()
        except ValueError:
            selected_date = timezone.now().date()
    else:
        selected_date = timezone.now().date()
    
    # Rendez-vous du jour sélectionné
    daily_appointments = request.user.appointments.filter(
        appointment_date=selected_date
    ).order_by('appointment_time')
    
    # Disponibilités du médecin pour ce jour
    weekday = selected_date.weekday()
    availabilities = request.user.availabilities.filter(
        weekday=weekday,
        is_active=True
    ).order_by('start_time')
    
    # Statistiques rapides
    stats = {
        'pending': request.user.appointments.filter(status='pending').count(),
        'confirmed_today': daily_appointments.filter(status='confirmed').count(),
        'total_today': daily_appointments.count(),
    }
    
    # Prochaine semaine pour navigation
    week_dates = []
    start_week = selected_date - timedelta(days=selected_date.weekday())
    for i in range(7):
        date = start_week + timedelta(days=i)
        appointment_count = request.user.appointments.filter(
            appointment_date=date
        ).count()
        week_dates.append({
            'date': date,
            'appointment_count': appointment_count,
            'is_selected': date == selected_date
        })
    
    context = {
        'selected_date': selected_date,
        'daily_appointments': daily_appointments,
        'availabilities': availabilities,
        'stats': stats,
        'week_dates': week_dates,
    }
    
    return render(request, 'medical/doctor_schedule.html', context)

@login_required
def appointment_create(request):
    """Créer un nouveau rendez-vous"""
    if request.user.role not in ['doctor', 'admin']:
        messages.error(request, "Accès non autorisé")
        return redirect('medical:appointment_list')
    
    # Patient pré-sélectionné depuis l'URL
    preselected_patient_id = request.GET.get('patient')
    preselected_patient = None
    if preselected_patient_id:
        try:
            preselected_patient = Patient.objects.get(pk=preselected_patient_id)
        except Patient.DoesNotExist:
            preselected_patient = None
    
    if request.method == 'POST':
        try:
            # Récupérer les données du formulaire
            patient_id = request.POST.get('patient_id')
            appointment_date = request.POST.get('appointment_date')
            appointment_time = request.POST.get('appointment_time')
            appointment_type = request.POST.get('appointment_type', 'consultation')
            duration_minutes = int(request.POST.get('duration_minutes', 30))
            reason = request.POST.get('reason')
            notes = request.POST.get('notes', '')
            
            # Valider les données
            if not all([patient_id, appointment_date, appointment_time, reason]):
                messages.error(request, "Tous les champs obligatoires doivent être remplis.")
                return redirect('medical:appointment_create')
            
            patient = get_object_or_404(Patient, pk=patient_id)
            doctor = request.user if request.user.role == 'doctor' else None
            
            if not doctor:
                doctor_id = request.POST.get('doctor_id')
                doctor = get_object_or_404(UserProfile, pk=doctor_id, role='doctor')
            
            # Vérifier la disponibilité
            from datetime import datetime
            appointment_datetime = datetime.strptime(
                f"{appointment_date} {appointment_time}", 
                "%Y-%m-%d %H:%M"
            )
            
            # Vérifier les conflits
            existing_appointment = Appointment.objects.filter(
                doctor=doctor,
                appointment_date=appointment_datetime.date(),
                appointment_time=appointment_datetime.time(),
                status__in=['pending', 'confirmed']
            ).exists()
            
            if existing_appointment:
                messages.error(request, "Un rendez-vous existe déjà à cette heure.")
                return redirect('medical:appointment_create')
            
            # Créer le rendez-vous
            appointment = Appointment.objects.create(
                patient=patient,
                doctor=doctor,
                appointment_date=appointment_datetime.date(),
                appointment_time=appointment_datetime.time(),
                appointment_type=appointment_type,
                duration_minutes=duration_minutes,
                reason=reason,
                notes=notes,
                created_by=request.user,
                status='pending'
            )
            
            # Logger l'action
            log_access(
                request.user,
                'create_appointment',
                details=f"Nouveau rendez-vous créé pour {patient.name}",
                patient=patient
            )
            
            # Envoyer notification
            try:
                appointment.send_notification('created')
            except:
                pass  # Ne pas faire échouer la création si l'email échoue
            
            messages.success(request, f"Rendez-vous créé avec succès pour {patient.name}")
            return redirect('medical:appointment_detail', appointment_id=appointment.id)
            
        except Exception as e:
            messages.error(request, f"Erreur lors de la création : {str(e)}")
    
    # Données pour le formulaire
    patients = Patient.objects.all().order_by('name')
    doctors = UserProfile.objects.filter(role='doctor', is_active=True).order_by('last_name')
    
    context = {
        'patients': patients,
        'doctors': doctors,
        'preselected_patient': preselected_patient,
        'appointment_types': Appointment.APPOINTMENT_TYPE_CHOICES,
        'today': timezone.now().date(),
    }
    
    return render(request, 'medical/appointment_create.html', context)
@login_required
def quick_actions_appointments(request):
    """Actions rapides sur les rendez-vous (accepter/refuser en lot)"""
    if request.user.role != 'doctor':
        return JsonResponse({'success': False, 'error': 'Accès non autorisé'}, status=403)
    
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            appointment_ids = data.get('appointment_ids', [])
            action = data.get('action')
            
            if not appointment_ids or not action:
                return JsonResponse({
                    'success': False,
                    'error': 'IDs de rendez-vous et action requis'
                }, status=400)
            
            # Récupérer les rendez-vous du médecin
            appointments = Appointment.objects.filter(
                id__in=appointment_ids,
                doctor=request.user
            )
            
            if len(appointments) != len(appointment_ids):
                return JsonResponse({
                    'success': False,
                    'error': 'Certains rendez-vous introuvables'
                }, status=400)
            
            # Appliquer l'action
            if action == 'confirm_all':
                appointments.update(status='confirmed')
                message = f"{len(appointments)} rendez-vous confirmés"
            elif action == 'cancel_all':
                appointments.update(status='cancelled')
                message = f"{len(appointments)} rendez-vous annulés"
            elif action == 'pending_all':
                appointments.update(status='pending')
                message = f"{len(appointments)} rendez-vous remis en attente"
            else:
                return JsonResponse({
                    'success': False,
                    'error': 'Action invalide'
                }, status=400)
            
            # Logger l'action
            log_access(
                request.user,
                f'bulk_appointment_{action}',
                details=f"Action en lot sur {len(appointments)} rendez-vous"
            )
            
            return JsonResponse({
                'success': True,
                'message': message,
                'updated_count': len(appointments)
            })
            
        except json.JSONDecodeError:
            return JsonResponse({
                'success': False,
                'error': 'Données JSON invalides'
            }, status=400)
        except Exception as e:
            return JsonResponse({
                'success': False,
                'error': str(e)
            }, status=500)
    
    return JsonResponse({'success': False, 'error': 'Méthode non autorisée'}, status=405)
@login_required
def check_availability(request):
    """API pour vérifier la disponibilité des créneaux"""
    if request.method == 'GET':
        date_str = request.GET.get('date')
        doctor_id = request.GET.get('doctor_id')
        duration = int(request.GET.get('duration', 30))
        
        if not date_str:
            return JsonResponse({'error': 'Date requise'}, status=400)
        
        try:
            date = datetime.strptime(date_str, '%Y-%m-%d').date()
        except ValueError:
            return JsonResponse({'error': 'Format de date invalide'}, status=400)
        
        # Si pas de médecin spécifié, utiliser l'utilisateur actuel
        if doctor_id and request.user.role == 'admin':
            doctor = get_object_or_404(UserProfile, pk=doctor_id, role='doctor')
        else:
            doctor = request.user
        
        if doctor.role != 'doctor':
            return JsonResponse({'error': 'Utilisateur non autorisé'}, status=403)
        
        # Utiliser le gestionnaire pour obtenir les créneaux disponibles
        available_slots = AppointmentManager.get_available_slots(doctor, date, duration)
        
        return JsonResponse({
            'available_slots': available_slots,
            'date': date_str,
            'doctor': doctor.get_full_name()
        })
    
    return JsonResponse({'error': 'Méthode non autorisée'}, status=405)