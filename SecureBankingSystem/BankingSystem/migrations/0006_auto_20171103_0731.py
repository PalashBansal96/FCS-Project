# -*- coding: utf-8 -*-
# Generated by Django 1.11.6 on 2017-11-03 02:01
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('BankingSystem', '0005_auto_20171103_0540'),
    ]

    operations = [
        migrations.AddField(
            model_name='transactions',
            name='verification_otp',
            field=models.IntegerField(default=0),
            preserve_default=False,
        ),
        migrations.AlterField(
            model_name='transactions',
            name='status',
            field=models.CharField(choices=[('C', 'Created'), ('A', 'Under Approval'), ('P', 'Processed'), ('I', 'Insufficient Funds'), ('E', 'Unknown Error')], max_length=1),
        ),
    ]
