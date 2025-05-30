# Generated by Django 4.2.18 on 2025-03-06 02:27

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('budget', '0007_budget_sort_no1_budget_sort_no2_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='daterange',
            name='end_day',
            field=models.PositiveSmallIntegerField(default=1, verbose_name='終了日'),
        ),
        migrations.AddField(
            model_name='daterange',
            name='start_day',
            field=models.PositiveSmallIntegerField(default=1, verbose_name='開始日'),
        ),
        migrations.AddField(
            model_name='usersettings',
            name='selected_daterange',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to='budget.daterange', verbose_name='選択中の期間'),
        ),
        migrations.AlterField(
            model_name='usersettings',
            name='selected_account_code',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to='budget.accountcode', verbose_name='選択口座コード'),
        ),
        migrations.AlterField(
            model_name='usersettings',
            name='year_month',
            field=models.CharField(default='', max_length=6, verbose_name='選択中の年月'),
        ),
    ]
