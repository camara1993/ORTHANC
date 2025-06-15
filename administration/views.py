from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages
from django.db.models import Count, Q, Avg
from django.utils import timezone
from django.http import JsonResponse
from django.core.paginator import Paginator
from django.conf import settings
from django.views.decorators.http import require_http_methods
from datetime import datetime, timedelta
from accounts.models import UserProfile
from dicom_viewer.models import Patient, Study, Series, Instance, AccessLog, DoctorPatientRelation
from dicom_viewer.orthanc_api import OrthancClient
from dicom_viewer.services import OrthancSyncService
import json
import requests
import psutil
def log_access(user, action, details=None, patient=None, study=None):
    """Helper function to log user actions"""
    AccessLog.objects.create(
        user=user,
        action=action,
        details=details,
        patient=patient,
        study=study
    )




def admin_required(view_func):
    """Décorateur pour restreindre l'accès aux administrateurs"""
    decorated_view_func = login_required(
        user_passes_test(
            lambda u: u.is_active and u.role == 'admin',
            login_url='/'
        )(view_func)
    )
    return decorated_view_func

@admin_required
def dashboard(request):
    """Dashboard principal de l'administration"""
    # Statistiques générales
    stats = {
        'total_users': UserProfile.objects.count(),
        'active_users': UserProfile.objects.filter(last_login__gte=timezone.now() - timedelta(days=30)).count(),
        'total_patients': Patient.objects.count(),
        'total_studies': Study.objects.count(),
        'total_series': Series.objects.count(),
        'total_instances': Instance.objects.count(),
    }
    
    # Répartition par rôle
    role_distribution = UserProfile.objects.values('role').annotate(count=Count('id'))
    
    # Activité récente (derniers 7 jours)
    seven_days_ago = timezone.now() - timedelta(days=7)
    daily_activity = AccessLog.objects.filter(
        timestamp__gte=seven_days_ago
    ).extra(
        select={'day': 'date(timestamp)'}
    ).values('day').annotate(count=Count('id')).order_by('day')
    
    # Études par modalité
    modality_stats = Series.objects.values('modality').annotate(
        count=Count('id')
    ).order_by('-count')[:10]
    
    # Derniers accès
    recent_accesses = AccessLog.objects.select_related('user', 'patient').order_by('-timestamp')[:10]
    
    # État du serveur Orthanc
    try:
        client = OrthancClient()
        orthanc_info = client.get_system_info()
        orthanc_stats = client.get_statistics()
        orthanc_status = {
            'connected': True,
            'version': orthanc_info.get('Version'),
            'name': orthanc_info.get('Name'),
            'stats': orthanc_stats
        }
    except Exception as e:
        orthanc_status = {
            'connected': False,
            'error': str(e)
        }
    
    context = {
        'stats': stats,
        'role_distribution': role_distribution,
        'daily_activity': list(daily_activity),
        'modality_stats': modality_stats,
        'recent_accesses': recent_accesses,
        'orthanc_status': orthanc_status,
    }
    
    return render(request, 'administration/dashboard.html', context)

@admin_required
def user_management(request):
    """Gestion des utilisateurs"""
    users = UserProfile.objects.all().order_by('-date_joined')
    
    # Filtres
    role_filter = request.GET.get('role')
    status_filter = request.GET.get('status')
    search_query = request.GET.get('search', '')
    
    if role_filter:
        users = users.filter(role=role_filter)
    
    if status_filter == 'active':
        users = users.filter(is_active=True)
    elif status_filter == 'inactive':
        users = users.filter(is_active=False)
    
    if search_query:
        users = users.filter(
            Q(username__icontains=search_query) |
            Q(email__icontains=search_query) |
            Q(first_name__icontains=search_query) |
            Q(last_name__icontains=search_query)
        )
    
    # Pagination
    paginator = Paginator(users, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'page_obj': page_obj,
        'total_users': paginator.count,
        'role_filter': role_filter,
        'status_filter': status_filter,
        'search_query': search_query,
    }
    
    return render(request, 'administration/user_management.html', context)

@admin_required
def user_detail(request, user_id):
    """Détail et modification d'un utilisateur"""
    user = get_object_or_404(UserProfile, pk=user_id)
    
    if request.method == 'POST':
        action = request.POST.get('action')
        
        if action == 'toggle_active':
            user.is_active = not user.is_active
            user.save()
            messages.success(request, f"Utilisateur {'activé' if user.is_active else 'désactivé'} avec succès.")
        
        elif action == 'change_role':
            new_role = request.POST.get('role')
            if new_role in dict(UserProfile.ROLE_CHOICES):
                user.role = new_role
                user.save()
                messages.success(request, "Rôle modifié avec succès.")
        
        elif action == 'reset_password':
            # Implémenter la réinitialisation du mot de passe
            messages.info(request, "Un email de réinitialisation a été envoyé.")
        
        return redirect('administration:user_detail', user_id=user.id)
    
    # Statistiques d'utilisation
    user_stats = {
        'total_accesses': AccessLog.objects.filter(user=user).count(),
        'last_access': AccessLog.objects.filter(user=user).order_by('-timestamp').first(),
        'accessed_patients': AccessLog.objects.filter(user=user).values('patient').distinct().count(),
        'accessed_studies': AccessLog.objects.filter(user=user).values('study').distinct().count(),
    }
    
    # Historique d'accès récent
    recent_accesses = AccessLog.objects.filter(user=user).select_related('patient', 'study').order_by('-timestamp')[:20]
    
    # Ajouter ROLE_CHOICES au contexte
    context = {
        'user': user,
        'user_stats': user_stats,
        'recent_accesses': recent_accesses,
        'ROLE_CHOICES': UserProfile.ROLE_CHOICES,
    }
    
    return render(request, 'administration/user_detail.html', context)

@admin_required
def user_detail(request, user_id):
    """Vue détaillée d'un utilisateur"""
    user = get_object_or_404(UserProfile, pk=user_id)
    
    # Statistiques de l'utilisateur
    access_logs = AccessLog.objects.filter(user=user).order_by('-timestamp')[:20]
    
    # Pour les patients, récupérer les informations médicales
    patient_info = None
    if user.role == 'patient':
        try:
            patient = Patient.objects.get(user=user)
            patient_info = {
                'patient': patient,
                'studies_count': patient.studies.count(),
                'appointments_count': patient.appointments.filter(
                    appointment_date__gte=timezone.now().date()
                ).count() if hasattr(patient, 'appointments') else 0,
            }
        except Patient.DoesNotExist:
            pass
    
    # Pour les médecins
    doctor_info = None
    if user.role == 'doctor':
        doctor_info = {
            'patients_count': user.doctor_patients.filter(is_active=True).count() if hasattr(user, 'doctor_patients') else 0,
            'appointments_today': user.appointments.filter(
                appointment_date=timezone.now().date()
            ).count() if hasattr(user, 'appointments') else 0,
        }
    
    context = {
        'user_detail': user,
        'access_logs': access_logs,
        'patient_info': patient_info,
        'doctor_info': doctor_info,
    }
    
    return render(request, 'administration/user_detail.html', context)

@admin_required
def access_logs(request):
    """Journal des accès"""
    logs = AccessLog.objects.select_related('user', 'patient', 'study').order_by('-timestamp')
    
    # Filtres
    user_filter = request.GET.get('user')
    action_filter = request.GET.get('action')
    date_from = request.GET.get('date_from')
    date_to = request.GET.get('date_to')
    
    if user_filter:
        logs = logs.filter(user_id=user_filter)
    
    if action_filter:
        logs = logs.filter(action=action_filter)
    
    if date_from:
        logs = logs.filter(timestamp__gte=date_from)
    
    if date_to:
        logs = logs.filter(timestamp__lte=date_to)
    
    # Actions disponibles
    actions = AccessLog.objects.values_list('action', flat=True).distinct()
    
    # Utilisateurs pour le filtre
    users_list = UserProfile.objects.all().order_by('username')
    
    # Pagination
    paginator = Paginator(logs, 50)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'page_obj': page_obj,
        'total_logs': paginator.count,
        'users_list': users_list,
        'actions': actions,
        'user_filter': user_filter,
        'action_filter': action_filter,
        'date_from': date_from,
        'date_to': date_to,
    }
    
    return render(request, 'administration/access_logs.html', context)

@admin_required
def system_settings(request):
    """Paramètres système"""
    if request.method == 'POST':
        # Sauvegarder les paramètres
        messages.success(request, "Paramètres enregistrés avec succès.")
        return redirect('administration:system_settings')
    
    # Charger les paramètres actuels
    from django.conf import settings
    settings_data = {
        'orthanc_url': settings.ORTHANC_CONFIG['URL'],
        'orthanc_username': settings.ORTHANC_CONFIG['USERNAME'],
        'session_timeout': settings.SESSION_COOKIE_AGE // 60,  # En minutes
        'max_upload_size': getattr(settings, 'FILE_UPLOAD_MAX_MEMORY_SIZE', 2621440) // (1024 * 1024),  # En MB
    }
    
    context = {
        'settings': settings_data,
    }
    
    return render(request, 'administration/system_settings.html', context)

@admin_required
@require_http_methods(["POST"])
def toggle_user_status(request, user_id):
    """Active/désactive un utilisateur"""
    try:
        user = get_object_or_404(UserProfile, pk=user_id)
        
        # Ne pas désactiver les superusers ou soi-même
        if user.is_superuser:
            return JsonResponse({
                'success': False,
                'error': 'Impossible de désactiver un super utilisateur.'
            }, status=403)
        
        if user.id == request.user.id:
            return JsonResponse({
                'success': False,
                'error': 'Vous ne pouvez pas désactiver votre propre compte.'
            }, status=403)
        
        # Basculer le statut
        user.is_active = not user.is_active
        user.save()
        
        # Logger l'action
        log_access(
            request.user,
            'toggle_user_status',
            details=f"{'Activé' if user.is_active else 'Désactivé'} l'utilisateur {user.username}"
        )
        
        messages.success(
            request,
            f"Utilisateur {user.username} {'activé' if user.is_active else 'désactivé'} avec succès."
        )
        
        return JsonResponse({
            'success': True,
            'is_active': user.is_active,
            'message': f"Utilisateur {'activé' if user.is_active else 'désactivé'}"
        })
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)

@admin_required
def orthanc_monitor(request):
    """Monitoring du serveur Orthanc"""
    try:
        client = OrthancClient()
        
        # Informations système
        system_info = client.get_system_info()
        statistics = client.get_statistics()
        
        # Calcul de l'espace disque
        disk_size = statistics.get('TotalDiskSizeMB', 0)
        disk_used = statistics.get('TotalUncompressedSizeMB', 0)
        disk_free = disk_size - disk_used if disk_size > 0 else 0
        disk_usage_percent = (disk_used / disk_size * 100) if disk_size > 0 else 0
        
        context = {
            'connected': True,
            'system_info': system_info,
            'statistics': statistics,
            'disk_usage': {
                'used': disk_used,
                'free': disk_free,
                'total': disk_size,
                'percent': disk_usage_percent
            }
        }
        
    except Exception as e:
        context = {
            'connected': False,
            'error': str(e)
        }
    
    return render(request, 'administration/orthanc_monitor.html', context)

@admin_required
def sync_orthanc(request):
    """Lance la synchronisation avec Orthanc"""
    if request.method == 'POST':
        try:
            from dicom_viewer.services import OrthancSyncService
            service = OrthancSyncService()
            stats = service.sync_all()
            
            messages.success(
                request,
                f"Synchronisation terminée : {stats['patients_synced']} patients, "
                f"{stats['studies_synced']} études synchronisés."
            )
            
            # Logger l'action
            log_access(request.user, 'sync_orthanc', details=json.dumps(stats))
            
        except Exception as e:
            messages.error(request, f"Erreur lors de la synchronisation : {str(e)}")
            
    return redirect('administration:orthanc_monitor')

@admin_required
def api_dashboard_stats(request):
    """API pour les statistiques du dashboard"""
    try:
        stats = {
            'users': {
                'total': UserProfile.objects.count(),
                'active': UserProfile.objects.filter(is_active=True).count(),
                'by_role': {
                    'admin': UserProfile.objects.filter(role='admin').count(),
                    'doctor': UserProfile.objects.filter(role='doctor').count(),
                    'patient': UserProfile.objects.filter(role='patient').count(),
                    'user': UserProfile.objects.filter(role='user').count(),
                }
            },
            'patients': {
                'total': Patient.objects.count(),
                'with_studies': Patient.objects.filter(studies__isnull=False).distinct().count(),
            },
            'studies': {
                'total': Study.objects.count(),
                'this_month': Study.objects.filter(
                    created_at__gte=timezone.now().replace(day=1)
                ).count(),
            },
            'access_logs': {
                'today': AccessLog.objects.filter(
                    timestamp__date=timezone.now().date()
                ).count(),
                'this_week': AccessLog.objects.filter(
                    timestamp__gte=timezone.now() - timedelta(days=7)
                ).count(),
            }
        }
        
        # Ajouter les statistiques médicales si l'app existe
        try:
            from medical.models import Appointment, Prescription
            stats['medical'] = {
                'appointments_today': Appointment.objects.filter(
                    appointment_date=timezone.now().date()
                ).count(),
                'active_prescriptions': Prescription.objects.filter(
                    is_active=True,
                    valid_until__gte=timezone.now().date()
                ).count(),
            }
        except ImportError:
            pass
        
        return JsonResponse(stats)
        
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)

@admin_required
def api_server_status(request):
    """API pour le statut du serveur"""
    try:
        from dicom_viewer.orthanc_api import OrthancClient
        client = OrthancClient()
        
        # Statut Orthanc
        orthanc_status = {
            'connected': False,
            'version': None,
            'patients_count': 0,
            'studies_count': 0,
            'disk_usage': {}
        }
        
        try:
            system_info = client.get_system_info()
            statistics = client.get_statistics()
            
            orthanc_status.update({
                'connected': True,
                'version': system_info.get('Version'),
                'patients_count': statistics.get('CountPatients', 0),
                'studies_count': statistics.get('CountStudies', 0),
                'disk_usage': {
                    'used_mb': statistics.get('TotalUncompressedSizeMB', 0),
                    'total_mb': statistics.get('TotalDiskSizeMB', 0),
                }
            })
        except:
            pass
        
        # Statut Django
        django_status = {
            'cpu_percent': psutil.cpu_percent(interval=1),
            'memory': {
                'percent': psutil.virtual_memory().percent,
                'used_gb': round(psutil.virtual_memory().used / (1024**3), 2),
                'total_gb': round(psutil.virtual_memory().total / (1024**3), 2),
            },
            'uptime': str(timezone.now() - timezone.now().replace(
                hour=0, minute=0, second=0, microsecond=0
            ))
        }
        
        return JsonResponse({
            'orthanc': orthanc_status,
            'django': django_status,
            'timestamp': timezone.now().isoformat()
        })
        
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)
@admin_required
def patient_create(request):
    """Créer un nouveau patient dans Orthanc"""
    # Définir context en dehors du if pour qu'il soit toujours disponible
    context = {
        'today': timezone.now().date(),
    }
    
    if request.method == 'POST':
        try:
            # Récupérer les données du formulaire
            patient_data = {
                'patient_id': request.POST.get('patient_id'),
                'name': request.POST.get('name'),
                'birth_date': request.POST.get('birth_date'),
                'sex': request.POST.get('sex'),
                'email': request.POST.get('email'),
            }
            
            # Valider les données requises
            if not patient_data['patient_id'] or not patient_data['name']:
                messages.error(request, "L'ID patient et le nom sont obligatoires.")
                return render(request, 'administration/patient_create.html', context)
            
            # Vérifier si l'ID patient existe déjà
            if Patient.objects.filter(patient_id=patient_data['patient_id']).exists():
                messages.error(request, f"Un patient avec l'ID {patient_data['patient_id']} existe déjà.")
                return render(request, 'administration/patient_create.html', context)
            
            # Créer un utilisateur si email fourni
            user = None
            if patient_data['email']:
                from accounts.models import UserProfile
                username = patient_data['email'].split('@')[0]
                
                # Vérifier si l'utilisateur existe déjà
                if UserProfile.objects.filter(username=username).exists():
                    username = f"{username}_{patient_data['patient_id']}"
                
                user = UserProfile.objects.create_user(
                    username=username,
                    email=patient_data['email'],
                    first_name=patient_data['name'].split()[0] if patient_data['name'] else '',
                    last_name=' '.join(patient_data['name'].split()[1:]) if len(patient_data['name'].split()) > 1 else '',
                    role='patient'
                )
                
                # Générer un mot de passe temporaire
                temp_password = UserProfile.objects.make_random_password()
                user.set_password(temp_password)
                user.save()
                
                messages.info(request, f"Compte utilisateur créé. Nom d'utilisateur: {username}, Mot de passe temporaire: {temp_password}")
            
            # Approche alternative : Créer uniquement le patient dans la base locale
            # Si Orthanc reçoit des études DICOM pour ce patient, il créera automatiquement l'entrée
            
            # Générer un ID Orthanc temporaire (sera remplacé lors de la première étude)
            import uuid
            temp_orthanc_id = str(uuid.uuid4())
            
            # Créer le patient dans la base locale
            patient = Patient.objects.create(
                orthanc_id=temp_orthanc_id,  # ID temporaire
                patient_id=patient_data['patient_id'],
                name=patient_data['name'],
                birth_date=patient_data['birth_date'] if patient_data['birth_date'] else None,
                sex=patient_data['sex'] or '',
                user=user
            )
            
            # Alternative : essayer de créer via l'API REST d'Orthanc si disponible
            try:
                client = OrthancClient()
                
                # Créer un JSON minimal pour Orthanc
                import base64
                import io
                from PIL import Image
                
                # Créer une image minimale
                img = Image.new('L', (64, 64), color=0)
                img_buffer = io.BytesIO()
                img.save(img_buffer, format='PNG')
                img_data = base64.b64encode(img_buffer.getvalue()).decode()
                
                # Utiliser une structure DICOM plus simple
                dicom_json = {
                    "Tags": {
                        "PatientID": patient_data['patient_id'],
                        "PatientName": patient_data['name'],
                        "PatientBirthDate": patient_data['birth_date'].replace('-', '') if patient_data['birth_date'] else "",
                        "PatientSex": patient_data['sex'] or "",
                        "StudyDescription": "Initial Patient Creation",
                        "SeriesDescription": "Placeholder Series",
                        "Modality": "OT",
                        "SpecificCharacterSet": "ISO_IR 100"
                    },
                    "Content": f"data:image/png;base64,{img_data}"
                }
                
                # Envoyer à Orthanc
                response = requests.post(
                    f"{settings.ORTHANC_CONFIG['URL']}/tools/create-dicom",
                    json=dicom_json,
                    auth=(settings.ORTHANC_CONFIG['USERNAME'], settings.ORTHANC_CONFIG['PASSWORD']),
                    timeout=30
                )
                
                if response.status_code == 200:
                    result = response.json()
                    orthanc_patient_id = result.get('ParentPatient')
                    
                    if orthanc_patient_id:
                        # Mettre à jour avec le vrai ID Orthanc
                        patient.orthanc_id = orthanc_patient_id
                        patient.save()
                        
                        # Optionnel : supprimer l'instance créée pour ne garder que le patient
                        instance_id = result.get('ID')
                        if instance_id:
                            requests.delete(
                                f"{settings.ORTHANC_CONFIG['URL']}/instances/{instance_id}",
                                auth=(settings.ORTHANC_CONFIG['USERNAME'], settings.ORTHANC_CONFIG['PASSWORD']),
                                timeout=10
                            )
                
            except Exception as orthanc_error:
                # Si Orthanc échoue, on garde quand même le patient local
                messages.warning(request, f"Patient créé localement. Orthanc sera synchronisé lors du premier upload DICOM.")
                print(f"Orthanc error (non-fatal): {orthanc_error}")
            
            messages.success(request, f"Patient {patient.name} créé avec succès.")
            return redirect('dicom_viewer:patient_detail', patient_id=patient.id)
                
        except Exception as e:
            messages.error(request, f"Erreur lors de la création du patient: {str(e)}")
    
    return render(request, 'administration/patient_create.html', context)
@admin_required
def patient_edit(request, patient_id):
    """Modifier un patient dans Orthanc"""
    patient = get_object_or_404(Patient, pk=patient_id)
    
    if request.method == 'POST':
        try:
            # Récupérer les données du formulaire
            updated_data = {
                'name': request.POST.get('name'),
                'birth_date': request.POST.get('birth_date'),
                'sex': request.POST.get('sex'),
            }
            
            # Valider les données
            if not updated_data['name']:
                messages.error(request, "Le nom est obligatoire.")
                return render(request, 'administration/patient_edit.html', {'patient': patient})
            
            # Mettre à jour dans Orthanc si le patient a un ID Orthanc valide
            if patient.orthanc_id and patient.orthanc_id != 'test-orthanc-id':
                from dicom_viewer.orthanc_api import OrthancClient
                client = OrthancClient()
                
                # Préparer les données pour Orthanc
                orthanc_data = {
                    'Replace': {
                        'PatientName': updated_data['name'],
                        'PatientBirthDate': updated_data['birth_date'].replace('-', '') if updated_data['birth_date'] else '',
                        'PatientSex': updated_data['sex'] or '',
                    }
                }
                
                # Envoyer la modification à Orthanc
                response = requests.post(
                    f"{settings.ORTHANC_CONFIG['URL']}/patients/{patient.orthanc_id}/modify",
                    json=orthanc_data,
                    auth=(settings.ORTHANC_CONFIG['USERNAME'], settings.ORTHANC_CONFIG['PASSWORD'])
                )
                
                if response.status_code != 200:
                    messages.warning(request, "Mise à jour locale uniquement (erreur Orthanc)")
            
            # Mettre à jour localement
            patient.name = updated_data['name']
            if updated_data['birth_date']:
                patient.birth_date = updated_data['birth_date']
            patient.sex = updated_data['sex'] or ''
            patient.save()
            
            messages.success(request, "Patient mis à jour avec succès.")
            return redirect('dicom_viewer:patient_detail', patient_id=patient.id)
            
        except Exception as e:
            messages.error(request, f"Erreur lors de la mise à jour: {str(e)}")
    
    context = {
        'patient': patient,
    }
    return render(request, 'administration/patient_edit.html', context)


@admin_required
def doctor_patient_assign(request):
    """Assigner des patients aux médecins"""
    if request.method == 'POST':
        doctor_id = request.POST.get('doctor_id')
        patient_id = request.POST.get('patient_id')
        
        try:
            from dicom_viewer.models import DoctorPatientRelation
            
            # Valider les IDs
            doctor = get_object_or_404(UserProfile, pk=doctor_id, role='doctor')
            patient = get_object_or_404(Patient, pk=patient_id)
            
            # Créer ou récupérer la relation
            relation, created = DoctorPatientRelation.objects.get_or_create(
                doctor=doctor,
                patient=patient,
                defaults={'is_active': True}
            )
            
            if created:
                messages.success(request, f"Patient {patient.name} assigné à Dr. {doctor.get_full_name()}")
            else:
                if not relation.is_active:
                    relation.is_active = True
                    relation.save()
                    messages.success(request, f"Relation réactivée entre {patient.name} et Dr. {doctor.get_full_name()}")
                else:
                    messages.info(request, "Cette relation existe déjà.")
            
            # Logger l'action
            log_access(
                request.user, 
                'assign_patient',
                details=f"Assigné {patient.name} à Dr. {doctor.get_full_name()}"
            )
                
        except Exception as e:
            messages.error(request, f"Erreur: {str(e)}")
    
    # Récupérer les données pour l'affichage
    doctors = UserProfile.objects.filter(role='doctor', is_active=True).order_by('last_name', 'first_name')
    patients = Patient.objects.all().order_by('name')
    
    # Relations existantes
    from dicom_viewer.models import DoctorPatientRelation
    relations = DoctorPatientRelation.objects.filter(is_active=True).select_related('doctor', 'patient')
    
    context = {
        'doctors': doctors,
        'patients': patients,
        'relations': relations,
    }
    return render(request, 'administration/doctor_patient_assign.html', context)

def sync_patient_with_orthanc(patient):
    """
    Synchronise un patient local avec Orthanc.
    Cherche le patient dans Orthanc par son ID et met à jour l'orthanc_id si trouvé.
    """
    try:
        from dicom_viewer.orthanc_api import OrthancClient
        client = OrthancClient()
        
        # Rechercher le patient dans Orthanc
        response = requests.get(
            f"{settings.ORTHANC_CONFIG['URL']}/tools/find",
            json={
                "Level": "Patient",
                "Query": {
                    "PatientID": patient.patient_id
                }
            },
            auth=(settings.ORTHANC_CONFIG['USERNAME'], settings.ORTHANC_CONFIG['PASSWORD']),
            timeout=10
        )
        
        if response.status_code == 200:
            results = response.json()
            if results:
                # Patient trouvé dans Orthanc
                orthanc_patient_id = results[0]
                
                # Récupérer les détails du patient
                patient_details = requests.get(
                    f"{settings.ORTHANC_CONFIG['URL']}/patients/{orthanc_patient_id}",
                    auth=(settings.ORTHANC_CONFIG['USERNAME'], settings.ORTHANC_CONFIG['PASSWORD']),
                    timeout=10
                ).json()
                
                # Mettre à jour l'ID Orthanc
                patient.orthanc_id = orthanc_patient_id
                patient.save()
                
                return True, f"Patient synchronisé avec Orthanc (ID: {orthanc_patient_id})"
        
        return False, "Patient non trouvé dans Orthanc"
        
    except Exception as e:
        return False, f"Erreur lors de la synchronisation: {str(e)}"


# Ajouter cette fonction à votre service de synchronisation ou l'appeler lors de l'upload d'images
def check_and_sync_patient(patient_id_dicom):
    """
    Vérifie si un patient existe localement lors de l'upload DICOM et le crée si nécessaire.
    """
    try:
        # Chercher le patient local
        patient = Patient.objects.filter(patient_id=patient_id_dicom).first()
        
        if patient and not patient.orthanc_id:
            # Patient existe mais pas encore lié à Orthanc
            success, message = sync_patient_with_orthanc(patient)
            if success:
                print(f"Patient {patient.name} synchronisé avec Orthanc")
        
        return patient
        
    except Exception as e:
        print(f"Erreur check_and_sync_patient: {str(e)}")
        return None
