# -*- coding: utf-8 -*-
# Generated by Django 1.9.13 on 2017-04-17 00:04
from __future__ import unicode_literals

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0002_tank_tkey'),
    ]

    operations = [
        migrations.CreateModel(
            name='Stat',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('event', models.IntegerField(choices=[(1, 'Death'), (2, 'Kill'), (3, 'Resurect')])),
                ('created_at', models.DateTimeField(auto_now_add=True)),
            ],
        ),
        migrations.RemoveField(
            model_name='tank',
            name='kill_count',
        ),
        migrations.RemoveField(
            model_name='tank',
            name='total_steps',
        ),
        migrations.AddField(
            model_name='stat',
            name='tank',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='stats', to='core.Tank'),
        ),
    ]
