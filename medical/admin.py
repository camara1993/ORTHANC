from django.contrib import admin
from .models import Prescription, PrescriptionItem, Appointment, DoctorAvailability

class PrescriptionItemInline(admin.TabularInline):
    model = PrescriptionItem
    extra = 1

@admin.register(Prescription)
class PrescriptionAdmin(admin.ModelAdmin):
    list_display = ['patient', 'doctor', 'created_at', 'valid_until', 'is_active']
    list_filter = ['is_active', 'created_at', 'doctor']
    search_fields = ['patient__name', 'doctor__username']
    inlines = [PrescriptionItemInline]
    date_hierarchy = 'created_at'

@admin.register(Appointment)
class AppointmentAdmin(admin.ModelAdmin):
    list_display = ['patient', 'doctor', 'appointment_date', 'appointment_time', 'status', 'appointment_type']
    list_filter = ['status', 'appointment_type', 'appointment_date', 'doctor']
    search_fields = ['patient__name', 'doctor__username', 'reason']
    date_hierarchy = 'appointment_date'

@admin.register(DoctorAvailability)
class DoctorAvailabilityAdmin(admin.ModelAdmin):
    list_display = ['doctor', 'weekday', 'start_time', 'end_time', 'is_active']
    list_filter = ['weekday', 'is_active', 'doctor']
    ordering = ['doctor', 'weekday', 'start_time']