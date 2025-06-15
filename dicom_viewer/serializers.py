from rest_framework import serializers
from .models import Patient, Study, Series, Instance

class InstanceSerializer(serializers.ModelSerializer):
    preview_url = serializers.SerializerMethodField()
    
    class Meta:
        model = Instance
        fields = ['id', 'orthanc_id', 'sop_instance_uid', 
                  'instance_number', 'preview_url']
    
    def get_preview_url(self, obj):
        return f"/api/instances/{obj.orthanc_id}/preview/"

class SeriesSerializer(serializers.ModelSerializer):
    instances = InstanceSerializer(many=True, read_only=True)
    instance_count = serializers.SerializerMethodField()
    
    class Meta:
        model = Series
        fields = ['id', 'orthanc_id', 'series_instance_uid', 'modality',
                  'series_number', 'series_description', 'body_part',
                  'instances', 'instance_count']
    
    def get_instance_count(self, obj):
        return obj.instances.count()

class StudySerializer(serializers.ModelSerializer):
    series = SeriesSerializer(many=True, read_only=True)
    series_count = serializers.SerializerMethodField()
    instance_count = serializers.SerializerMethodField()
    
    class Meta:
        model = Study
        fields = ['id', 'orthanc_id', 'study_instance_uid', 'study_date',
                  'study_time', 'study_description', 'accession_number',
                  'referring_physician', 'series', 'series_count', 
                  'instance_count']
    
    def get_series_count(self, obj):
        return obj.series.count()
    
    def get_instance_count(self, obj):
        return sum(series.instances.count() for series in obj.series.all())

class PatientSerializer(serializers.ModelSerializer):
    studies = StudySerializer(many=True, read_only=True)
    study_count = serializers.SerializerMethodField()
    age = serializers.SerializerMethodField()
    
    class Meta:
        model = Patient
        fields = ['id', 'orthanc_id', 'patient_id', 'name', 'birth_date',
                  'sex', 'studies', 'study_count', 'age']
    
    def get_study_count(self, obj):
        return obj.studies.count()
    
    def get_age(self, obj):
        if obj.birth_date:
            from datetime import date
            today = date.today()
            return today.year - obj.birth_date.year - (
                (today.month, today.day) < (obj.birth_date.month, obj.birth_date.day)
            )
        return None