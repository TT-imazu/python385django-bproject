# Generated by Django 4.2.18 on 2025-03-14 03:57

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('budget', '0014_basebudget_daterange_basebudget_sort_no1_and_more'),
    ]

    operations = [
        migrations.AlterField(
            model_name='budget',
            name='itemtype',
            field=models.CharField(choices=[('工事金入金', '工事金入金'), ('その他入金', 'その他入金'), ('自動引落', '自動引落'), ('個別支払', '個別支払'), ('預金振替', '預金振替')], default='工事金入金', max_length=10),
        ),
    ]
