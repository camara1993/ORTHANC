from rest_framework import viewsets, permissions, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django.utils import timezone
from .models import Appointment, Prescription, DoctorAvailability
from .serializers import (
    AppointmentSerializer, 
    PrescriptionSerializer, 
    DoctorAvailabilitySerializer
)

class IsOwnerOrDoctor(permissions.BasePermission):
    """Permission pour accéder aux données médicales"""
    
    def has_object_permission(self, request, view, obj):
        if hasattr(obj, 'patient'):
            return (obj.patient.user == request.user or 
                    obj.doctor == request.user or
                    request.user.role == 'admin')
        return False

class AppointmentViewSet(viewsets.ModelViewSet):
    serializer_class = AppointmentSerializer
    permission_classes = [permissions.IsAuthenticated, IsOwnerOrDoctor]
    
    def get_queryset(self):
        user = self.request.user
        if user.role == 'patient':
            return Appointment.objects.filter(patient__user=user)
        elif user.role == 'doctor':
            return Appointment.objects.filter(doctor=user)
        elif user.role == 'admin':
            return Appointment.objects.all()
        return Appointment.objects.none()
    
    @action(detail=True, methods=['post'])
    def confirm(self, request, pk=None):
        """Confirmer un rendez-vous"""
        appointment = self.get_object()
        if request.user != appointment.doctor:
            return Response(
                {'error': 'Seul le médecin peut confirmer le rendez-vous'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        appointment.status = 'confirmed'
        appointment.save()
        return Response({'status': 'confirmed'})
    
    @action(detail=True, methods=['post'])
    def cancel(self, request, pk=None):
        """Annuler un rendez-vous"""
        appointment = self.get_object()
        appointment.status = 'cancelled'
        appointment.save()
        return Response({'status': 'cancelled'})

class PrescriptionViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = PrescriptionSerializer
    permission_classes = [permissions.IsAuthenticated, IsOwnerOrDoctor]
    
    def get_queryset(self):
        user = self.request.user
        if user.role == 'patient':
            return Prescription.objects.filter(patient__user=user)
        elif user.role == 'doctor':
            return Prescription.objects.filter(doctor=user)
        elif user.role == 'admin':
            return Prescription.objects.all()
        return Prescription.objects.none()