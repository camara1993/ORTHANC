from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required

def home(request):
    """Page d'accueil avec redirection selon le rôle"""
    if request.user.is_authenticated:
        # Rediriger selon le rôle de l'utilisateur
        if request.user.role == 'admin':
            return redirect('administration:dashboard')
        elif request.user.role == 'doctor':
            return redirect('dicom_viewer:patient_list')
        elif request.user.role == 'patient':
            # Rediriger vers le profil patient ou ses rendez-vous
            return redirect('medical:appointment_list')
        else:
            # Utilisateur sans rôle spécifique
            return redirect('dicom_viewer:patient_list')
    
    # Utilisateur non connecté - afficher la page d'accueil
    context = {
        'user_count': 0,
        'patient_count': 0,
        'study_count': 0,
    }
    
    # Ajouter quelques statistiques si disponibles
    try:
        from accounts.models import UserProfile
        from dicom_viewer.models import Patient, Study
        
        context['user_count'] = UserProfile.objects.count()
        context['patient_count'] = Patient.objects.count()
        context['study_count'] = Study.objects.count()
    except:
        pass
    
    return render(request, 'core/home.html', context)