from rest_framework import serializers
from django.contrib.auth import authenticate
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django.db import transaction
from .models import UserProfile
from dicom_viewer.models import Patient

class UserProfileSerializer(serializers.ModelSerializer):
    """Serializer pour le profil utilisateur"""
    full_name = serializers.CharField(source='get_full_name', read_only=True)
    patient_info = serializers.SerializerMethodField()
    password = serializers.CharField(write_only=True, required=False, style={'input_type': 'password'})
    
    class Meta:
        model = UserProfile
        fields = [
            'id', 'username', 'email', 'first_name', 'last_name', 'full_name',
            'role', 'phone_number', 'address', 'date_joined', 'last_login',
            'is_active', 'specialization', 'license_number', 'patient_info',
            'password'
        ]
        read_only_fields = ['id', 'date_joined', 'last_login', 'patient_info']
        extra_kwargs = {
            'password': {'write_only': True},
        }
    
    def get_patient_info(self, obj):
        """Récupère les informations du patient si l'utilisateur est un patient"""
        if obj.role == 'patient':
            try:
                patient = Patient.objects.get(user=obj)
                return {
                    'patient_id': patient.patient_id,
                    'name': patient.name,
                    'birth_date': patient.birth_date,
                    'sex': patient.sex,
                    'id': patient.id
                }
            except Patient.DoesNotExist:
                return None
        return None
    
    def validate_password(self, value):
        """Valide le mot de passe selon les règles Django"""
        if value:
            validate_password(value)
        return value
    
    def create(self, validated_data):
        """Crée un nouvel utilisateur"""
        password = validated_data.pop('password', None)
        user = UserProfile(**validated_data)
        if password:
            user.set_password(password)
        user.save()
        return user
    
    def update(self, instance, validated_data):
        """Met à jour un utilisateur existant"""
        password = validated_data.pop('password', None)
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        if password:
            instance.set_password(password)
        instance.save()
        return instance


class UserSerializer(serializers.ModelSerializer):
    """Serializer simplifié pour les références utilisateur"""
    class Meta:
        model = UserProfile
        fields = ['id', 'username', 'email', 'get_full_name', 'role']
        read_only_fields = fields


class LoginSerializer(serializers.Serializer):
    """Serializer pour la connexion"""
    username = serializers.CharField()
    password = serializers.CharField(style={'input_type': 'password'})
    
    def validate(self, attrs):
        username = attrs.get('username')
        password = attrs.get('password')
        
        if username and password:
            user = authenticate(username=username, password=password)
            
            if not user:
                raise serializers.ValidationError('Identifiants invalides.')
            
            if not user.is_active:
                raise serializers.ValidationError('Compte désactivé.')
            
            attrs['user'] = user
            return attrs
        else:
            raise serializers.ValidationError('Username et password requis.')


class RegisterSerializer(serializers.ModelSerializer):
    """Serializer pour l'inscription"""
    password = serializers.CharField(write_only=True, required=True, validators=[validate_password])
    password2 = serializers.CharField(write_only=True, required=True, label="Confirmer le mot de passe")
    email = serializers.EmailField(required=True)
    
    class Meta:
        model = UserProfile
        fields = [
            'username', 'email', 'password', 'password2',
            'first_name', 'last_name', 'role', 'phone_number', 'address'
        ]
        extra_kwargs = {
            'first_name': {'required': True},
            'last_name': {'required': True},
        }
    
    def validate(self, attrs):
        """Validation globale"""
        if attrs['password'] != attrs['password2']:
            raise serializers.ValidationError({
                "password": "Les mots de passe ne correspondent pas."
            })
        
        # Vérifier que l'email n'existe pas déjà
        if UserProfile.objects.filter(email=attrs['email']).exists():
            raise serializers.ValidationError({
                "email": "Un utilisateur avec cet email existe déjà."
            })
        
        return attrs
    
    def create(self, validated_data):
        """Crée un nouvel utilisateur lors de l'inscription"""
        validated_data.pop('password2')
        password = validated_data.pop('password')
        
        user = UserProfile.objects.create(**validated_data)
        user.set_password(password)
        user.save()
        
        return user


class ChangePasswordSerializer(serializers.Serializer):
    """Serializer pour changer le mot de passe"""
    old_password = serializers.CharField(required=True, style={'input_type': 'password'})
    new_password = serializers.CharField(required=True, validators=[validate_password], style={'input_type': 'password'})
    new_password2 = serializers.CharField(required=True, style={'input_type': 'password'}, label="Confirmer le nouveau mot de passe")
    
    def validate(self, attrs):
        if attrs['new_password'] != attrs['new_password2']:
            raise serializers.ValidationError({
                "new_password": "Les nouveaux mots de passe ne correspondent pas."
            })
        return attrs
    
    def validate_old_password(self, value):
        user = self.context['request'].user
        if not user.check_password(value):
            raise serializers.ValidationError("Mot de passe actuel incorrect.")
        return value


class ResetPasswordEmailSerializer(serializers.Serializer):
    """Serializer pour demander une réinitialisation de mot de passe"""
    email = serializers.EmailField(required=True)
    
    def validate_email(self, value):
        """Vérifie que l'email existe"""
        if not UserProfile.objects.filter(email=value).exists():
            raise serializers.ValidationError("Aucun utilisateur trouvé avec cet email.")
        return value


class ResetPasswordSerializer(serializers.Serializer):
    """Serializer pour réinitialiser le mot de passe avec un token"""
    token = serializers.CharField(required=True)
    new_password = serializers.CharField(required=True, validators=[validate_password], style={'input_type': 'password'})
    new_password2 = serializers.CharField(required=True, style={'input_type': 'password'})
    
    def validate(self, attrs):
        if attrs['new_password'] != attrs['new_password2']:
            raise serializers.ValidationError({
                "new_password": "Les mots de passe ne correspondent pas."
            })
        return attrs


class DoctorProfileSerializer(UserProfileSerializer):
    """Serializer spécifique pour les profils de médecins"""
    patient_count = serializers.SerializerMethodField()
    appointment_count = serializers.SerializerMethodField()
    
    class Meta(UserProfileSerializer.Meta):
        fields = UserProfileSerializer.Meta.fields + ['patient_count', 'appointment_count']
    
    def get_patient_count(self, obj):
        """Nombre de patients assignés au médecin"""
        if obj.role == 'doctor':
            return obj.doctor_patients.filter(is_active=True).count()
        return 0
    
    def get_appointment_count(self, obj):
        """Nombre de rendez-vous à venir"""
        if obj.role == 'doctor':
            from django.utils import timezone
            return obj.appointments.filter(
                appointment_date__gte=timezone.now().date(),
                status__in=['pending', 'confirmed']
            ).count()
        return 0


class PatientProfileSerializer(UserProfileSerializer):
    """Serializer spécifique pour les profils de patients"""
    upcoming_appointments = serializers.SerializerMethodField()
    active_prescriptions = serializers.SerializerMethodField()
    assigned_doctors = serializers.SerializerMethodField()
    
    class Meta(UserProfileSerializer.Meta):
        fields = UserProfileSerializer.Meta.fields + [
            'upcoming_appointments', 'active_prescriptions', 'assigned_doctors'
        ]
    
    def get_upcoming_appointments(self, obj):
        """Rendez-vous à venir du patient"""
        if obj.role == 'patient':
            try:
                from django.utils import timezone
                patient = Patient.objects.get(user=obj)
                return patient.appointments.filter(
                    appointment_date__gte=timezone.now().date(),
                    status__in=['pending', 'confirmed']
                ).count()
            except Patient.DoesNotExist:
                return 0
        return 0
    
    def get_active_prescriptions(self, obj):
        """Prescriptions actives du patient"""
        if obj.role == 'patient':
            try:
                from django.utils import timezone
                patient = Patient.objects.get(user=obj)
                return patient.prescriptions.filter(
                    is_active=True,
                    valid_until__gte=timezone.now().date()
                ).count()
            except Patient.DoesNotExist:
                return 0
        return 0
    
    def get_assigned_doctors(self, obj):
        """Médecins assignés au patient"""
        if obj.role == 'patient':
            try:
                patient = Patient.objects.get(user=obj)
                doctors = []
                for relation in patient.patient_doctors.filter(is_active=True).select_related('doctor'):
                    doctors.append({
                        'id': relation.doctor.id,
                        'name': relation.doctor.get_full_name(),
                        'specialization': relation.doctor.specialization,
                        'since': relation.created_at
                    })
                return doctors
            except Patient.DoesNotExist:
                return []
        return []


class AdminUserSerializer(UserProfileSerializer):
    """Serializer pour l'administration des utilisateurs"""
    last_access = serializers.SerializerMethodField()
    total_accesses = serializers.SerializerMethodField()
    can_delete = serializers.SerializerMethodField()
    
    class Meta(UserProfileSerializer.Meta):
        fields = UserProfileSerializer.Meta.fields + [
            'last_access', 'total_accesses', 'can_delete',
            'is_staff', 'is_superuser', 'groups', 'user_permissions'
        ]
    
    def get_last_access(self, obj):
        """Dernier accès de l'utilisateur"""
        from dicom_viewer.models import AccessLog
        last_log = AccessLog.objects.filter(user=obj).order_by('-timestamp').first()
        if last_log:
            return {
                'timestamp': last_log.timestamp,
                'action': last_log.action,
                'ip_address': last_log.ip_address
            }
        return None
    
    def get_total_accesses(self, obj):
        """Nombre total d'accès"""
        from dicom_viewer.models import AccessLog
        return AccessLog.objects.filter(user=obj).count()
    
    def get_can_delete(self, obj):
        """Vérifie si l'utilisateur peut être supprimé"""
        # Ne pas supprimer les superusers ou soi-même
        request = self.context.get('request')
        if request:
            return not obj.is_superuser and obj.id != request.user.id
        return not obj.is_superuser


class UserActivitySerializer(serializers.Serializer):
    """Serializer pour l'activité des utilisateurs"""
    user_id = serializers.IntegerField()
    username = serializers.CharField()
    full_name = serializers.CharField()
    role = serializers.CharField()
    last_login = serializers.DateTimeField()
    access_count = serializers.IntegerField()
    last_action = serializers.CharField()
    is_online = serializers.BooleanField()


class BulkUserActionSerializer(serializers.Serializer):
    """Serializer pour les actions en masse sur les utilisateurs"""
    user_ids = serializers.ListField(
        child=serializers.IntegerField(),
        required=True,
        min_length=1
    )
    action = serializers.ChoiceField(
        choices=['activate', 'deactivate', 'delete', 'reset_password'],
        required=True
    )
    
    def validate_user_ids(self, value):
        """Vérifie que les utilisateurs existent"""
        existing_ids = UserProfile.objects.filter(id__in=value).values_list('id', flat=True)
        invalid_ids = set(value) - set(existing_ids)
        
        if invalid_ids:
            raise serializers.ValidationError(
                f"Les IDs suivants n'existent pas : {', '.join(map(str, invalid_ids))}"
            )
        
        return value