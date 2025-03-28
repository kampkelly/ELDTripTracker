# Generated by Django 5.1.7 on 2025-03-21 20:59

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("api_v1", "0002_update_stop_model"),
    ]

    operations = [
        migrations.AddField(
            model_name="dutystatus",
            name="status_description",
            field=models.CharField(blank=True, max_length=250, null=True),
        ),
        migrations.AlterField(
            model_name="route",
            name="trip",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                related_name="route",
                to="api_v1.trip",
            ),
        ),
    ]
