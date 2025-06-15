from django.core.management.base import BaseCommand
from dicom_viewer.models import Patient

class Command(BaseCommand):
    help = 'Normalise les valeurs du champ sexe des patients'
    
    def handle(self, *args, **options):
        self.stdout.write('Normalisation des données de sexe des patients...')
        
        # Mapping des valeurs possibles
        sex_mapping = {
            'm': 'M',
            'male': 'M',
            'homme': 'M',
            'masculin': 'M',
            'f': 'F',
            'female': 'F',
            'femme': 'F',
            'feminin': 'F',
            'féminin': 'F',
            'o': 'O',
            'other': 'O',
            'autre': 'O',
        }
        
        updated_count = 0
        
        for patient in Patient.objects.all():
            if patient.sex:
                normalized_sex = sex_mapping.get(patient.sex.lower(), patient.sex.upper())
                
                # Si la valeur n'est pas M, F ou O, on la met à vide
                if normalized_sex not in ['M', 'F', 'O']:
                    normalized_sex = ''
                
                if patient.sex != normalized_sex:
                    patient.sex = normalized_sex
                    patient.save()
                    updated_count += 1
                    self.stdout.write(
                        self.style.SUCCESS(
                            f'Patient {patient.name}: {patient.sex} -> {normalized_sex}'
                        )
                    )
        
        self.stdout.write(
            self.style.SUCCESS(
                f'\nNormalisation terminée. {updated_count} patients mis à jour.'
            )
        )