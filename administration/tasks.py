from celery import shared_task
from django.utils import timezone
from datetime import timedelta
from dicom_viewer.models import AccessLog
from .models import SystemConfiguration
import logging

logger = logging.getLogger(__name__)

@shared_task
def cleanup_old_logs():
    """Nettoie les logs d'accès anciens"""
    retention_days = int(SystemConfiguration.get_value('log_retention_days', 90))
    cutoff_date = timezone.now() - timedelta(days=retention_days)
    
    deleted_count = AccessLog.objects.filter(timestamp__lt=cutoff_date).delete()[0]
    logger.info(f"Suppression de {deleted_count} logs d'accès anciens")
    
    return deleted_count

@shared_task
def generate_usage_report():
    """Génère un rapport d'utilisation mensuel"""
    # Implémenter la génération de rapport
    pass

@shared_task
def check_orthanc_health():
    """Vérifie l'état de santé du serveur Orthanc"""
    from dicom_viewer.orthanc_api import OrthancClient
    
    try:
        client = OrthancClient()
        stats = client.get_statistics()
        
        # Vérifier l'espace disque
        disk_usage = stats.get('TotalDiskSizeMB', 0)
        disk_limit = int(SystemConfiguration.get_value('disk_warning_threshold_mb', 50000))
        
        if disk_usage > disk_limit:
            logger.warning(f"Espace disque Orthanc élevé: {disk_usage} MB")
            # Envoyer une notification
        
        return True
    except Exception as e:
        logger.error(f"Erreur vérification Orthanc: {e}")
        return False