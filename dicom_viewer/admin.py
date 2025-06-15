from django.contrib import admin
from .models import Patient, Study, Series, Instance

@admin.register(Patient)
class PatientAdmin(admin.ModelAdmin):
    list_display = ['name', 'patient_id', 'birth_date', 'sex', 'created_at']
    search_fields = ['name', 'patient_id']
    list_filter = ['sex', 'created_at']
    readonly_fields = ['orthanc_id', 'created_at', 'updated_at']

@admin.register(Study)
class StudyAdmin(admin.ModelAdmin):
    list_display = ['patient', 'study_date', 'study_description', 'modality_list']
    search_fields = ['study_description', 'accession_number']
    list_filter = ['study_date', 'created_at']
    readonly_fields = ['orthanc_id', 'study_instance_uid', 'created_at']
    
    def modality_list(self, obj):
        modalities = obj.series.values_list('modality', flat=True).distinct()
        return ', '.join(modalities)
    modality_list.short_description = 'Modalités'

@admin.register(Series)
class SeriesAdmin(admin.ModelAdmin):
    list_display = ['study', 'modality', 'series_number', 'series_description']
    search_fields = ['series_description', 'body_part']
    list_filter = ['modality', 'created_at']
    readonly_fields = ['orthanc_id', 'series_instance_uid', 'created_at']

@admin.register(Instance)
class InstanceAdmin(admin.ModelAdmin):
    list_display = ['series', 'instance_number', 'created_at']
    list_filter = ['created_at']
    readonly_fields = ['orthanc_id', 'sop_instance_uid', 'created_at']