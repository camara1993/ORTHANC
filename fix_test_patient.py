#!/usr/bin/env python
import os
import sys
import django
import requests
from datetime import datetime

# Configuration Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'orthanc_client.settings')
django.setup()

from django.conf import settings
from dicom_viewer.models import Patient
from dicom_viewer.orthanc_api import OrthancClient

def create_real_patient_in_orthanc():
    """Crée un vrai patient dans Orthanc et met à jour la base de données"""
    
    # Récupérer le patient de test
    try:
        patient = Patient.objects.get(patient_id='PAT001')
        print(f"Patient trouvé : {patient.name}")
    except Patient.DoesNotExist:
        print("❌ Patient PAT001 non trouvé")
        return
    
    # Créer le client Orthanc
    client = OrthancClient()
    
    # Créer une instance DICOM minimale
    dicom_data = {
        'Tags': {
            '0010,0010': patient.name,                    # Patient Name
            '0010,0020': patient.patient_id,              # Patient ID
            '0010,0030': patient.birth_date.strftime('%Y%m%d') if patient.birth_date else '',  # Birth Date
            '0010,0040': patient.sex or '',              # Sex
            '0008,0005': 'ISO_IR 100',                    # Character Set
            '0008,0016': '1.2.840.10008.5.1.4.1.1.7',   # SOP Class UID (Secondary Capture)
            '0008,0018': f'2.25.{datetime.now().timestamp()}',  # SOP Instance UID
            '0008,0020': datetime.now().strftime('%Y%m%d'),     # Study Date
            '0008,0030': datetime.now().strftime('%H%M%S'),     # Study Time
            '0008,0050': '',                              # Accession Number
            '0008,0060': 'OT',                            # Modality (Other)
            '0008,0090': '',                              # Referring Physician
            '0020,000D': f'2.25.{datetime.now().timestamp()}.1',  # Study Instance UID
            '0020,000E': f'2.25.{datetime.now().timestamp()}.2',  # Series Instance UID
            '0020,0010': '1',                             # Study ID
            '0020,0011': '1',                             # Series Number
            '0020,0013': '1',                             # Instance Number
            '0028,0002': '1',                             # Samples per Pixel
            '0028,0004': 'MONOCHROME2',                   # Photometric Interpretation
            '0028,0010': '128',                           # Rows
            '0028,0011': '128',                           # Columns
            '0028,0100': '8',                             # Bits Allocated
            '0028,0101': '8',                             # Bits Stored
            '0028,0102': '7',                             # High Bit
            '0028,0103': '0',                             # Pixel Representation
        },
        'Content': 'data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNkYPhfDwAChwGA60e6kgAAAABJRU5ErkJggg=='  # Image 1x1 pixel
    }
    
    try:
        # Créer l'instance DICOM dans Orthanc
        response = requests.post(
            f"{settings.ORTHANC_CONFIG['URL']}/tools/create-dicom",
            json=dicom_data,
            auth=(settings.ORTHANC_CONFIG['USERNAME'], settings.ORTHANC_CONFIG['PASSWORD'])
        )
        
        if response.status_code == 200:
            result = response.json()
            orthanc_patient_id = result.get('ParentPatient')
            
            if orthanc_patient_id:
                # Mettre à jour le patient avec le vrai ID Orthanc
                patient.orthanc_id = orthanc_patient_id
                patient.save()
                print(f"✅ Patient créé dans Orthanc avec ID : {orthanc_patient_id}")
                return orthanc_patient_id
            else:
                print("❌ Impossible de récupérer l'ID patient depuis Orthanc")
        else:
            print(f"❌ Erreur Orthanc : {response.status_code} - {response.text}")
            
    except Exception as e:
        print(f"❌ Erreur : {e}")
    
    return None

if __name__ == '__main__':
    print("🔧 Correction du patient de test...")
    orthanc_id = create_real_patient_in_orthanc()
    if orthanc_id:
        print(f"\n✅ Patient corrigé ! Nouvel ID Orthanc : {orthanc_id}")
        print("Vous pouvez maintenant accéder au patient sans erreur.")
    else:
        print("\n❌ Échec de la correction")