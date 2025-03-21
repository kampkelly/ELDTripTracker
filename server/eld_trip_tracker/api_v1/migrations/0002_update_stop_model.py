# Generated by Django 5.1.7 on 2025-03-21 14:41

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("api_v1", "0001_add_initial_models"),
    ]

    operations = [
        migrations.AlterField(
            model_name="stop",
            name="stop_type",
            field=models.CharField(
                choices=[
                    ("fuel", "Fuel Stop"),
                    ("rest_break", "30-Minute Break"),
                    ("mandatory_rest", "10-Hour Rest"),
                    ("pickup", "Pickup"),
                    ("dropoff", "Dropoff"),
                ],
                max_length=20,
            ),
        ),
    ]
