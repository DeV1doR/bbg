# -*- coding: utf-8 -*-
# Generated by Django 1.9.13 on 2017-04-25 21:59
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0004_auto_20170418_2113'),
    ]

    operations = [
        migrations.AlterField(
            model_name='stat',
            name='event',
            field=models.IntegerField(choices=[(0, 'Death'), (1, 'Kill'), (2, 'Shoot'), (3, 'Hit')]),
        ),
    ]
