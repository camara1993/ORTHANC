from django.apps import AppConfig

class MedicalConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'medical'
    
    # Commentez cette ligne pour l'instant
    # def ready(self):
    #     import medical.signals