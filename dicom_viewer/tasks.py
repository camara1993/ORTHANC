from celery import shared_task
from .services import OrthancSyncService
import logging

logger = logging.getLogger(__name__)

@shared_task
def sync_orthanc_data():
    """Tâche de synchronisation périodique"""
    try:
        service = OrthancSyncService()
        stats = service.sync_all_patients()
        logger.info(f"Sync terminée: {stats}")
        return stats
    except Exception as e:
        logger.error(f"Erreur sync Celery: {e}")
        raise

# Configuration dans settings.py


