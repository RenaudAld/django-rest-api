# Generated by Django 2.1.7 on 2019-02-27 15:19

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('api', '0008_auto_20190227_1416'),
    ]

    operations = [
        migrations.AddField(
            model_name='kart',
            name='latitude',
            field=models.FloatField(default=0.0),
        ),
        migrations.AddField(
            model_name='kart',
            name='longitude',
            field=models.FloatField(default=0.0),
        ),
        migrations.AlterField(
            model_name='balance',
            name='balance',
            field=models.FloatField(default=0.0),
        ),
    ]
