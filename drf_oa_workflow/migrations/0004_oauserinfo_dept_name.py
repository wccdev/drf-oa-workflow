# Generated by Django 4.2.2 on 2024-01-12 15:05

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('drf_oa_workflow', '0003_alter_oauserinfo_staff_code'),
    ]

    operations = [
        migrations.AddField(
            model_name='oauserinfo',
            name='dept_name',
            field=models.CharField(blank=True, default='', max_length=480, verbose_name='OA用户部门'),
        ),
    ]
