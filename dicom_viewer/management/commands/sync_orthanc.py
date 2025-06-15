from django.core.management.base import BaseCommand
from django.utils import timezone
from dicom_viewer.services import OrthancSyncService

class Command(BaseCommand):
    help = 'Synchronise les données depuis le serveur Orthanc'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--patient',
            type=str,
            help='Synchroniser un patient spécifique par son ID Orthanc'
        )
        parser.add_argument(
            '--full',
            action='store_true',
            help='Synchronisation complète de tous les patients'
        )
    
    def handle(self, *args, **options):
        service = OrthancSyncService()
        
        self.stdout.write(f"Début de la synchronisation à {timezone.now()}")
        
        try:
            if options['patient']:
                # Synchroniser un patient spécifique
                patient_id = options['patient']
                self.stdout.write(f"Synchronisation du patient {patient_id}...")
                
                patient = service.sync_patient(patient_id)
                
                self.stdout.write(
                    self.style.SUCCESS(
                        f"Patient {patient.name} synchronisé avec succès"
                    )
                )
                
            elif options['full']:
                # Synchronisation complète
                self.stdout.write("Synchronisation complète en cours...")
                
                stats = service.sync_all_patients()
                
                self.stdout.write(
                    self.style.SUCCESS(
                        f"Synchronisation terminée:\n"
                        f"- Patients créés: {stats['created']}\n"
                        f"- Patients mis à jour: {stats['updated']}\n"
                        f"- Erreurs: {stats['errors']}"
                    )
                )
            else:
                self.stdout.write(
                    self.style.WARNING(
                        "Veuillez spécifier --patient ID ou --full"
                    )
                )
                
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f"Erreur lors de la synchronisation: {e}")
            )