from django.db import migrations, models

class Migration(migrations.Migration):
    dependencies = [
        ('dicom_viewer', '0002_doctorpatientrelation'),  # Ajuster selon votre dernière migration
    ]

    operations = [
        migrations.AddField(
            model_name='accesslog',
            name='details',
            field=models.TextField(blank=True, null=True),
        ),
    ]