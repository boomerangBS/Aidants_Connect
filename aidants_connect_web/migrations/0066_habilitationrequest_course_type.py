# Generated by Django 4.2.13 on 2024-05-28 09:11

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('aidants_connect_web', '0065_alter_coreferentnonaidantrequest_status_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='habilitationrequest',
            name='course_type',
            field=models.IntegerField(choices=[(1, 'Parcours classique'), (2, 'Parcours pair-à-pair')], default=1, editable=False, verbose_name='Type de parcours'),
        ),
    ]