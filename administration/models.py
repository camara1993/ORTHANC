from django.db import models
from django.core.cache import cache
from django.conf import settings

class SystemConfiguration(models.Model):
    """Configuration système globale"""
    key = models.CharField(max_length=100, unique=True)
    value = models.TextField()
    description = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'system_configuration'
        verbose_name = 'Configuration système'
        verbose_name_plural = 'Configurations système'
    
    def __str__(self):
        return self.key
    
    @classmethod
    def get_value(cls, key, default=None):
        """Récupère une valeur de configuration avec cache"""
        cache_key = f'system_config_{key}'
        value = cache.get(cache_key)
        
        if value is None:
            try:
                config = cls.objects.get(key=key)
                value = config.value
                cache.set(cache_key, value, 3600)  # Cache pour 1 heure
            except cls.DoesNotExist:
                value = default
        
        return value
    
    @classmethod
    def set_value(cls, key, value, description=''):
        """Définit une valeur de configuration"""
        config, created = cls.objects.update_or_create(
            key=key,
            defaults={
                'value': str(value),
                'description': description
            }
        )
        
        # Invalider le cache
        cache_key = f'system_config_{key}'
        cache.delete(cache_key)
        
        return config

class AuditLog(models.Model):
    """Journal d'audit pour les actions administratives"""
    ACTION_CHOICES = [
        ('user_created', 'Utilisateur créé'),
        ('user_modified', 'Utilisateur modifié'),
        ('user_deleted', 'Utilisateur supprimé'),
        ('config_changed', 'Configuration modifiée'),
        ('sync_started', 'Synchronisation démarrée'),
        ('sync_completed', 'Synchronisation terminée'),
    ]
    
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='audit_logs'
    )
    action = models.CharField(max_length=50, choices=ACTION_CHOICES)
    target_model = models.CharField(max_length=100, blank=True)
    target_id = models.IntegerField(null=True, blank=True)
    details = models.JSONField(default=dict)
    ip_address = models.GenericIPAddressField()
    timestamp = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'audit_logs'
        ordering = ['-timestamp']
        verbose_name = 'Journal d\'audit'
        verbose_name_plural = 'Journaux d\'audit'