# Generated by Django 4.1.7 on 2023-04-03 09:33

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('aidants_connect_web', '0023_remove_journal_infos_set_remote_mandate_by_sms_and_more'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='aidantstatistiques',
            options={'verbose_name': 'Statistiques aidants', 'verbose_name_plural': 'Statistiques aidants'},
        ),
    ]