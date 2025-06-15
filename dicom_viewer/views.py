from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db.models import Q, Count
from django.contrib import messages
from django.http import JsonResponse
from django.utils import timezone
from .models import Patient, Study, Series, Instance, AccessLog
from .services import OrthancSyncService
from .orthanc_api import OrthancClient
import logging
import json

logger = logging.getLogger(__name__)

@login_required
def patient_list(request):
    """Liste des patients avec recherche et pagination"""
    # Vérifier les permissions
    if request.user.role not in ['admin', 'doctor']:
        messages.error(request, "Accès non autorisé")
        return redirect('core:home')
    
    # Récupération des patients
    patients = Patient.objects.all()
    
    # Pour les médecins, on peut filtrer selon les relations médecin-patient
    if request.user.role == 'doctor':
        # Optionnel : filtrer seulement les patients assignés au médecin
        # patients = patients.filter(patient_doctors__doctor=request.user, patient_doctors__is_active=True)
        pass
    
    # Recherche
    search_query = request.GET.get('search', '')
    if search_query:
        patients = patients.filter(
            Q(name__icontains=search_query) |
            Q(patient_id__icontains=search_query)
        )
    
    # Annotations pour les compteurs
    patients = patients.annotate(
        study_count=Count('studies'),
        total_instances=Count('studies__series__instances')
    )
    
    # Tri
    sort_by = request.GET.get('sort', '-created_at')
    patients = patients.order_by(sort_by)
    
    # Pagination
    paginator = Paginator(patients, 18)  # 18 patients par page (3x6 grid)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    # Log d'accès
    AccessLog.objects.create(
        user=request.user,
        action='view_patient_list',
        ip_address=request.META.get('REMOTE_ADDR', '127.0.0.1')
    )
    
    # Statistiques pour les médecins
    stats = {}
    if request.user.role == 'doctor':
        try:
            from medical.models import Appointment
            today = timezone.now().date()
            
            stats = {
                'appointments_today': request.user.appointments.filter(
                    appointment_date=today
                ).count(),
                'appointments_pending': request.user.appointments.filter(
                    status='pending'
                ).count(),
                'appointments_this_week': request.user.appointments.filter(
                    appointment_date__gte=today,
                    appointment_date__lte=today + timezone.timedelta(days=7)
                ).count(),
            }
        except ImportError:
            # Module medical pas encore installé
            pass
    
    context = {
        'page_obj': page_obj,
        'search_query': search_query,
        'total_patients': paginator.count,
        'stats': stats,
    }
    
    return render(request, 'dicom_viewer/patient_list.html', context)

# Le reste des vues reste identique...
@login_required
def patient_detail(request, patient_id):
    """Détail d'un patient avec ses études"""
    patient = get_object_or_404(Patient, pk=patient_id)
    
    # Vérifier les permissions
    if request.user.role == 'patient' and patient.user != request.user:
        messages.error(request, "Accès non autorisé")
        return redirect('core:home')
    
    # Récupérer les études avec annotations
    studies = patient.studies.annotate(
        series_count=Count('series'),
        instance_count=Count('series__instances')
    ).order_by('-study_date', '-study_time')
    
    # Log d'accès
    AccessLog.objects.create(
        user=request.user,
        patient=patient,
        action='view_patient_detail',
        ip_address=request.META.get('REMOTE_ADDR', '127.0.0.1')
    )
    
    context = {
        'patient': patient,
        'studies': studies,
    }
    
    return render(request, 'dicom_viewer/patient_detail.html', context)

@login_required
def study_detail(request, study_id):
    """Détail d'une étude avec ses séries"""
    study = get_object_or_404(Study.objects.select_related('patient'), pk=study_id)
    
    # Vérifier les permissions
    if request.user.role == 'patient' and study.patient.user != request.user:
        messages.error(request, "Accès non autorisé")
        return redirect('core:home')
    
    # Récupérer les séries avec annotations
    series_list = study.series.annotate(
        instance_count=Count('instances')
    ).order_by('series_number')
    
    # Log d'accès
    AccessLog.objects.create(
        user=request.user,
        patient=study.patient,
        study=study,
        action='view_study_detail',
        ip_address=request.META.get('REMOTE_ADDR', '127.0.0.1')
    )
    
    context = {
        'study': study,
        'patient': study.patient,
        'series_list': series_list,
    }
    
    return render(request, 'dicom_viewer/study_detail.html', context)

@login_required
def dicom_viewer(request, series_id):
    """Visualiseur DICOM pour une série"""
    series = get_object_or_404(
        Series.objects.select_related('study__patient'),
        pk=series_id
    )
    
    # Vérifier les permissions
    if request.user.role == 'patient' and series.study.patient.user != request.user:
        messages.error(request, "Accès non autorisé")
        return redirect('core:home')
    
    # Récupérer toutes les instances de la série
    instances = series.instances.order_by('instance_number')
    
    # Log d'accès
    AccessLog.objects.create(
        user=request.user,
        patient=series.study.patient,
        study=series.study,
        action='view_dicom_images',
        ip_address=request.META.get('REMOTE_ADDR', '127.0.0.1')
    )
    
    # Préparer les IDs pour JavaScript
    instance_ids = list(instances.values_list('id', flat=True))
    
    context = {
        'series': series,
        'study': series.study,
        'patient': series.study.patient,
        'instances': instances,
        'instance_count': instances.count(),
        'instance_ids': json.dumps(instance_ids),
    }
    
    return render(request, 'dicom_viewer/viewer.html', context)

@login_required
def sync_patient_ajax(request, patient_id):
    """Synchronisation AJAX d'un patient"""
    if request.method == 'POST' and request.user.role in ['admin', 'doctor']:
        try:
            patient = get_object_or_404(Patient, pk=patient_id)
            service = OrthancSyncService()
            service.sync_patient(patient.orthanc_id)
            
            return JsonResponse({
                'status': 'success',
                'message': 'Patient synchronisé avec succès'
            })
        except Exception as e:
            logger.error(f"Erreur sync patient {patient_id}: {e}")
            return JsonResponse({
                'status': 'error',
                'message': str(e)
            }, status=500)
    
    return JsonResponse({'status': 'error', 'message': 'Méthode non autorisée'}, status=405)