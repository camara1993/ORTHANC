from rest_framework import serializers
from .models import Appointment, Prescription, PrescriptionItem, DoctorAvailability
from accounts.serializers import UserSerializer
from dicom_viewer.serializers import PatientSerializer

class PrescriptionItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = PrescriptionItem
        fields = ['medication_name', 'dosage', 'frequency', 'duration', 'quantity', 'instructions']

class PrescriptionSerializer(serializers.ModelSerializer):
    items = PrescriptionItemSerializer(many=True, read_only=True)
    doctor_name = serializers.CharField(source='doctor.get_full_name', read_only=True)
    patient_name = serializers.CharField(source='patient.name', read_only=True)
    
    class Meta:
        model = Prescription
        fields = ['id', 'doctor', 'doctor_name', 'patient', 'patient_name', 
                  'created_at', 'valid_until', 'is_active', 'notes', 'items']

class AppointmentSerializer(serializers.ModelSerializer):
    doctor_name = serializers.CharField(source='doctor.get_full_name', read_only=True)
    patient_name = serializers.CharField(source='patient.name', read_only=True)
    
    class Meta:
        model = Appointment
        fields = ['id', 'patient', 'patient_name', 'doctor', 'doctor_name',
                  'appointment_date', 'appointment_time', 'appointment_type',
                  'duration_minutes', 'status', 'reason', 'notes', 
                  'created_at', 'updated_at']

class DoctorAvailabilitySerializer(serializers.ModelSerializer):
    doctor_name = serializers.CharField(source='doctor.get_full_name', read_only=True)
    
    class Meta:
        model = DoctorAvailability
        fields = ['id', 'doctor', 'doctor_name', 'weekday', 'start_time', 
                  'end_time', 'is_active']