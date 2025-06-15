from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.http import HttpResponse
from django.shortcuts import get_object_or_404
from .models import Patient, Study, Series, Instance
from .serializers import PatientSerializer, StudySerializer, SeriesSerializer, InstanceSerializer
from .orthanc_api import OrthancClient
from .services import OrthancSyncService
import logging

logger = logging.getLogger(__name__)

class PatientViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = PatientSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        queryset = Patient.objects.all()
        
        # Filtrer selon le rôle de l'utilisateur
        if self.request.user.role == 'patient':
            # Les patients ne voient que leurs propres données
            queryset = queryset.filter(user=self.request.user)
        elif self.request.user.role == 'doctor':
            # Les médecins voient tous les patients
            pass
        elif self.request.user.role == 'admin':
            # Les admins voient tout
            pass
        
        return queryset.order_by('-created_at')
    
    @action(detail=True, methods=['post'])
    def sync(self, request, pk=None):
        """Synchronise un patient spécifique depuis Orthanc"""
        patient = self.get_object()
        
        try:
            service = OrthancSyncService()
            updated_patient = service.sync_patient(patient.orthanc_id)
            
            serializer = self.get_serializer(updated_patient)
            return Response(serializer.data)
        except Exception as e:
            logger.error(f"Erreur sync patient {patient.orthanc_id}: {e}")
            return Response(
                {'error': 'Erreur lors de la synchronisation'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

class StudyViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = StudySerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        queryset = Study.objects.all()
        
        # Filtrer selon le rôle
        if self.request.user.role == 'patient':
            queryset = queryset.filter(patient__user=self.request.user)
        
        # Filtrer par patient si spécifié
        patient_id = self.request.query_params.get('patient', None)
        if patient_id:
            queryset = queryset.filter(patient_id=patient_id)
        
        return queryset.order_by('-study_date', '-study_time')

class SeriesViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = SeriesSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        queryset = Series.objects.all()
        
        # Filtrer selon le rôle
        if self.request.user.role == 'patient':
            queryset = queryset.filter(study__patient__user=self.request.user)
        
        # Filtrer par étude si spécifié
        study_id = self.request.query_params.get('study', None)
        if study_id:
            queryset = queryset.filter(study_id=study_id)
        
        return queryset.order_by('series_number')

class InstanceViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = InstanceSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        queryset = Instance.objects.all()
        
        # Filtrer selon le rôle
        if self.request.user.role == 'patient':
            queryset = queryset.filter(
                series__study__patient__user=self.request.user
            )
        
        # Filtrer par série si spécifié
        series_id = self.request.query_params.get('series', None)
        if series_id:
            queryset = queryset.filter(series_id=series_id)
        
        return queryset.order_by('instance_number')
    
    @action(detail=True, methods=['get'])
    def preview(self, request, pk=None):
        """Récupère l'aperçu d'une instance"""
        instance = self.get_object()
        
        try:
            client = OrthancClient()
            image_data = client.get_instance_preview(instance.orthanc_id)
            
            return HttpResponse(image_data, content_type='image/png')
        except Exception as e:
            logger.error(f"Erreur récupération preview {instance.orthanc_id}: {e}")
            return Response(
                {'error': 'Erreur lors de la récupération de l\'image'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @action(detail=True, methods=['get'])
    def full_image(self, request, pk=None):
        """Récupère l'image complète d'une instance"""
        instance = self.get_object()
        frame = request.query_params.get('frame', 0)
        
        try:
            client = OrthancClient()
            image_data = client.get_instance_image(instance.orthanc_id, int(frame))
            
            return HttpResponse(image_data, content_type='image/png')
        except Exception as e:
            logger.error(f"Erreur récupération image {instance.orthanc_id}: {e}")
            return Response(
                {'error': 'Erreur lors de la récupération de l\'image'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @action(detail=True, methods=['get'])
    def tags(self, request, pk=None):
        """Récupère les tags DICOM d'une instance"""
        instance = self.get_object()
        
        try:
            client = OrthancClient()
            tags = client.get_instance_tags(instance.orthanc_id)
            
            return Response(tags)
        except Exception as e:
            logger.error(f"Erreur récupération tags {instance.orthanc_id}: {e}")
            return Response(
                {'error': 'Erreur lors de la récupération des tags'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )