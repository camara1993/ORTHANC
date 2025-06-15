from typing import List, Dict, Optional
from django.db import transaction
from django.utils import timezone
from .models import Patient, Study, Series, Instance
from .orthanc_api import OrthancClient
import logging

logger = logging.getLogger(__name__)

class OrthancSyncService:
    """Service pour synchroniser les données entre Orthanc et la base Django"""
    
    def __init__(self):
        self.client = OrthancClient()
    
    @transaction.atomic
    def sync_all_patients(self) -> Dict[str, int]:
        """Synchronise tous les patients depuis Orthanc"""
        stats = {'created': 0, 'updated': 0, 'errors': 0}
        
        try:
            patient_ids = self.client.get_patients()
            
            for patient_id in patient_ids:
                try:
                    self.sync_patient(patient_id, stats)
                except Exception as e:
                    logger.error(f"Erreur sync patient {patient_id}: {e}")
                    stats['errors'] += 1
            
            return stats
        except Exception as e:
            logger.error(f"Erreur sync globale: {e}")
            raise
    
    def sync_patient(self, orthanc_patient_id: str, stats: Optional[Dict] = None) -> Patient:
        """Synchronise un patient spécifique"""
        patient_data = self.client.get_patient(orthanc_patient_id)
        main_dicom_tags = patient_data.get('MainDicomTags', {})
        
        # Extraction des données patient
        patient_id = main_dicom_tags.get('PatientID', '')
        patient_name = self.client.format_patient_name(
            main_dicom_tags.get('PatientName', 'Inconnu')
        )
        birth_date = self.client.parse_dicom_date(
            main_dicom_tags.get('PatientBirthDate', '')
        )
        sex = main_dicom_tags.get('PatientSex', '')
        
        # Créer ou mettre à jour le patient
        patient, created = Patient.objects.update_or_create(
            orthanc_id=orthanc_patient_id,
            defaults={
                'patient_id': patient_id,
                'name': patient_name,
                'birth_date': birth_date,
                'sex': sex,
            }
        )
        
        if stats:
            if created:
                stats['created'] += 1
            else:
                stats['updated'] += 1
        
        # Synchroniser les études du patient
        for study_id in patient_data.get('Studies', []):
            self.sync_study(study_id, patient)
        
        return patient
    
    def sync_study(self, orthanc_study_id: str, patient: Patient) -> Study:
        """Synchronise une étude spécifique"""
        study_data = self.client.get_study(orthanc_study_id)
        main_dicom_tags = study_data.get('MainDicomTags', {})
        
        # Extraction des données de l'étude
        study_instance_uid = main_dicom_tags.get('StudyInstanceUID', '')
        study_date = self.client.parse_dicom_date(
            main_dicom_tags.get('StudyDate', '')
        )
        study_time = self.client.parse_dicom_time(
            main_dicom_tags.get('StudyTime', '')
        )
        study_description = main_dicom_tags.get('StudyDescription', '')
        accession_number = main_dicom_tags.get('AccessionNumber', '')
        referring_physician = main_dicom_tags.get('ReferringPhysicianName', '')
        
        # Créer ou mettre à jour l'étude
        study, created = Study.objects.update_or_create(
            orthanc_id=orthanc_study_id,
            defaults={
                'patient': patient,
                'study_instance_uid': study_instance_uid,
                'study_date': study_date,
                'study_time': study_time,
                'study_description': study_description,
                'accession_number': accession_number,
                'referring_physician': referring_physician,
            }
        )
        
        # Synchroniser les séries de l'étude
        for series_id in study_data.get('Series', []):
            self.sync_series(series_id, study)
        
        return study
    
    def sync_series(self, orthanc_series_id: str, study: Study) -> Series:
        """Synchronise une série spécifique"""
        series_data = self.client.get_series(orthanc_series_id)
        main_dicom_tags = series_data.get('MainDicomTags', {})
        
        # Extraction des données de la série
        series_instance_uid = main_dicom_tags.get('SeriesInstanceUID', '')
        modality = main_dicom_tags.get('Modality', '')
        series_number = main_dicom_tags.get('SeriesNumber', '')
        series_description = main_dicom_tags.get('SeriesDescription', '')
        body_part = main_dicom_tags.get('BodyPartExamined', '')
        
        # Convertir series_number en entier
        try:
            series_number = int(series_number) if series_number else None
        except:
            series_number = None
        
        # Créer ou mettre à jour la série
        series, created = Series.objects.update_or_create(
            orthanc_id=orthanc_series_id,
            defaults={
                'study': study,
                'series_instance_uid': series_instance_uid,
                'modality': modality,
                'series_number': series_number,
                'series_description': series_description,
                'body_part': body_part,
            }
        )
        
        # Synchroniser les instances de la série
        for instance_id in series_data.get('Instances', []):
            self.sync_instance(instance_id, series)
        
        return series
    
    def sync_instance(self, orthanc_instance_id: str, series: Series) -> Instance:
        """Synchronise une instance spécifique"""
        instance_data = self.client.get_instance(orthanc_instance_id)
        main_dicom_tags = instance_data.get('MainDicomTags', {})
        
        # Extraction des données de l'instance
        sop_instance_uid = main_dicom_tags.get('SOPInstanceUID', '')
        instance_number = main_dicom_tags.get('InstanceNumber', '')
        
        # Convertir instance_number en entier
        try:
            instance_number = int(instance_number) if instance_number else None
        except:
            instance_number = None
        
        # Créer ou mettre à jour l'instance
        instance, created = Instance.objects.update_or_create(
            orthanc_id=orthanc_instance_id,
            defaults={
                'series': series,
                'sop_instance_uid': sop_instance_uid,
                'instance_number': instance_number,
            }
        )
        
        return instance
    
    def get_patient_with_full_hierarchy(self, patient_id: str) -> Optional[Patient]:
        """Récupère un patient avec toute sa hiérarchie depuis Orthanc"""
        try:
            patient = self.sync_patient(patient_id)
            return patient
        except Exception as e:
            logger.error(f"Erreur récupération patient {patient_id}: {e}")
            return None