# Generated by Django 4.2.18 on 2025-02-27 01:17

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    initial = True

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='DateRange',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=50)),
            ],
        ),
        migrations.CreateModel(
            name='ItemType',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=50)),
            ],
        ),
        migrations.CreateModel(
            name='Budget',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('item_name', models.CharField(max_length=100)),
                ('expected_amount', models.IntegerField(default=0)),
                ('actual_amount', models.IntegerField(default=0)),
                ('daterange', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='budget.daterange')),
                ('itemtype', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='budget.itemtype')),
            ],
        ),
    ]
