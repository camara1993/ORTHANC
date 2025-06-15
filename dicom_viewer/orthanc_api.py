import requests
from requests.auth import HTTPBasicAuth
from django.conf import settings
from typing import List, Dict, Optional
import json
from datetime import datetime

class OrthancClient:
    """Client pour interagir avec l'API REST d'Orthanc"""
    
    def __init__(self):
        self.base_url = settings.ORTHANC_CONFIG['URL']
        self.auth = HTTPBasicAuth(
            settings.ORTHANC_CONFIG['USERNAME'],
            settings.ORTHANC_CONFIG['PASSWORD']
        )
        self.session = requests.Session()
        self.session.auth = self.auth
    
    def _make_request(self, method: str, endpoint: str, **kwargs) -> requests.Response:
        """Effectue une requête HTTP vers l'API Orthanc"""
        url = f"{self.base_url}/{endpoint}"
        try:
            response = self.session.request(method, url, **kwargs)
            response.raise_for_status()
            return response
        except requests.RequestException as e:
            print(f"Erreur API Orthanc: {e}")
            raise
    
    def get_system_info(self) -> Dict:
        """Récupère les informations système d'Orthanc"""
        response = self._make_request('GET', 'system')
        return response.json()
    
    # === Patients ===
    
    def get_patients(self) -> List[str]:
        """Récupère la liste des IDs des patients"""
        response = self._make_request('GET', 'patients')
        return response.json()
    
    def get_patient(self, patient_id: str) -> Dict:
        """Récupère les détails d'un patient"""
        response = self._make_request('GET', f'patients/{patient_id}')
        return response.json()
    
    def get_patient_studies(self, patient_id: str) -> List[str]:
        """Récupère les études d'un patient"""
        patient_data = self.get_patient(patient_id)
        return patient_data.get('Studies', [])
    
    def search_patients(self, query: Dict) -> List[Dict]:
        """Recherche des patients selon des critères"""
        response = self._make_request('POST', 'tools/find', json={
            'Level': 'Patient',
            'Query': query,
            'Expand': True
        })
        return response.json()
    
    # === Studies (Études) ===
    
    def get_studies(self) -> List[str]:
        """Récupère la liste des IDs des études"""
        response = self._make_request('GET', 'studies')
        return response.json()
    
    def get_study(self, study_id: str) -> Dict:
        """Récupère les détails d'une étude"""
        response = self._make_request('GET', f'studies/{study_id}')
        return response.json()
    
    def get_study_series(self, study_id: str) -> List[str]:
        """Récupère les séries d'une étude"""
        study_data = self.get_study(study_id)
        return study_data.get('Series', [])
    
    # === Series ===
    
    def get_series(self, series_id: str) -> Dict:
        """Récupère les détails d'une série"""
        response = self._make_request('GET', f'series/{series_id}')
        return response.json()
    
    def get_series_instances(self, series_id: str) -> List[str]:
        """Récupère les instances d'une série"""
        series_data = self.get_series(series_id)
        return series_data.get('Instances', [])
    
    # === Instances ===
    
    def get_instance(self, instance_id: str) -> Dict:
        """Récupère les détails d'une instance"""
        response = self._make_request('GET', f'instances/{instance_id}')
        return response.json()
    
    def get_instance_tags(self, instance_id: str) -> Dict:
        """Récupère les tags DICOM d'une instance"""
        response = self._make_request('GET', f'instances/{instance_id}/tags')
        return response.json()
    
    def get_instance_preview(self, instance_id: str) -> bytes:
        """Récupère l'aperçu PNG d'une instance"""
        response = self._make_request('GET', f'instances/{instance_id}/preview')
        return response.content
    
    def get_instance_image(self, instance_id: str, frame: int = 0) -> bytes:
        """Récupère l'image PNG d'une instance"""
        response = self._make_request('GET', f'instances/{instance_id}/frames/{frame}/preview')
        return response.content
    
    # === Statistiques ===
    
    def get_statistics(self) -> Dict:
        """Récupère les statistiques globales"""
        response = self._make_request('GET', 'statistics')
        return response.json()
    
    # === Utilitaires ===
    
    def parse_dicom_date(self, date_str: str) -> Optional[str]:
        """Convertit une date DICOM au format ISO"""
        if not date_str:
            return None
        try:
            # Format DICOM: YYYYMMDD
            if len(date_str) == 8:
                return datetime.strptime(date_str, '%Y%m%d').date().isoformat()
            return date_str
        except:
            return None
    
    def parse_dicom_time(self, time_str: str) -> Optional[str]:
        """Convertit une heure DICOM au format ISO"""
        if not time_str:
            return None
        try:
            # Format DICOM: HHMMSS.FFFFFF
            if len(time_str) >= 6:
                hour = time_str[0:2]
                minute = time_str[2:4]
                second = time_str[4:6]
                return f"{hour}:{minute}:{second}"
            return time_str
        except:
            return None
    
    def format_patient_name(self, name: str) -> str:
        """Formate le nom du patient depuis le format DICOM"""
        if not name:
            return "Inconnu"
        # Format DICOM: LastName^FirstName^MiddleName
        parts = name.split('^')
        if len(parts) >= 2:
            return f"{parts[1]} {parts[0]}"
        return name.replace('^', ' ')