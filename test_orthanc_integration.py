import os
import sys
import django

# Configuration Django
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'orthanc_client.settings')
django.setup()

from dicom_viewer.orthanc_api import OrthancClient
from dicom_viewer.services import OrthancSyncService

def test_connection():
    """Test de connexion à Orthanc"""
    print("Test de connexion à Orthanc...")
    client = OrthancClient()
    
    try:
        info = client.get_system_info()
        print(f"✓ Connexion réussie!")
        print(f"  Version: {info.get('Version')}")
        print(f"  Nom: {info.get('Name')}")
        
        stats = client.get_statistics()
        print(f"\nStatistiques:")
        print(f"  Patients: {stats.get('CountPatients', 0)}")
        print(f"  Études: {stats.get('CountStudies', 0)}")
        print(f"  Séries: {stats.get('CountSeries', 0)}")
        print(f"  Instances: {stats.get('CountInstances', 0)}")
        
        return True
    except Exception as e:
        print(f"✗ Erreur de connexion: {e}")
        return False

def test_sync():
    """Test de synchronisation"""
    print("\nTest de synchronisation...")
    service = OrthancSyncService()
    
    try:
        # Synchroniser le premier patient trouvé
        client = OrthancClient()
        patients = client.get_patients()
        
        if patients:
            print(f"Synchronisation du patient {patients[0]}...")
            patient = service.sync_patient(patients[0])
            print(f"✓ Patient synchronisé: {patient.name}")
            print(f"  Études: {patient.studies.count()}")
        else:
            print("Aucun patient trouvé dans Orthanc")
            
    except Exception as e:
        print(f"✗ Erreur de synchronisation: {e}")

if __name__ == "__main__":
    if test_connection():
        test_sync()