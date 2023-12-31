# Generated by Django 4.2.4 on 2023-09-11 16:20

import django.core.validators
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    initial = True

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='Analyst',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=100, verbose_name='Name of the analyst')),
                ('company', models.CharField(max_length=100, verbose_name='Company name')),
                ('hit_rate', models.FloatField(null=True, validators=[django.core.validators.MinValueValidator(0.0), django.core.validators.MaxValueValidator(1.0)], verbose_name='Hit rate as a percentage (0-1)')),
                ('avg_days_hit', models.FloatField(null=True, verbose_name='Average days hit')),
                ('avg_days_missed', models.FloatField(null=True, verbose_name='Average days missed')),
                ('avg_days_to_first_hit', models.FloatField(null=True, verbose_name='Average days to first hit')),
                ('avg_days_to_first_miss', models.FloatField(null=True, verbose_name='Average days to first miss')),
            ],
        ),
        migrations.CreateModel(
            name='Currency',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('code', models.CharField(max_length=3, verbose_name='3 letter representation of a currency(USD)')),
                ('name', models.CharField(max_length=50, verbose_name='Name of currency(dollar)')),
            ],
        ),
        migrations.CreateModel(
            name='Report',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('title', models.CharField(max_length=200, verbose_name='Title of the report')),
                ('url', models.URLField(verbose_name='URL where report is published')),
                ('target_price', models.DecimalField(decimal_places=2, max_digits=10, verbose_name='Target price for related stock')),
                ('price_on_publish', models.DecimalField(decimal_places=2, max_digits=10, verbose_name='Price of related stock when published')),
                ('publish_date', models.DateField(verbose_name='Date when the report was published')),
                ('is_newest', models.BooleanField(default=False)),
                ('next_publish_date', models.DateField(null=True, verbose_name='The date of next publication if known')),
                ('written_sentiment', models.CharField(choices=[('BUY', 'Buy'), ('HOLD', 'Hold'), ('SELL', 'Sell')], default='HOLD', max_length=4, verbose_name='Sentiment written in the report (Buy/Hold/Sell)')),
                ('hidden_sentiment', models.CharField(choices=[('BUY', 'Buy'), ('SELL', 'Sell')], max_length=4, verbose_name='Hidden sentiment (not explicitly mentioned but implied)')),
                ('hit_rate', models.FloatField(null=True, validators=[django.core.validators.MinValueValidator(0.0), django.core.validators.MaxValueValidator(1.0)], verbose_name='Hit rate as a percentage (0-1)')),
                ('days_hit', models.IntegerField(null=True, verbose_name='Number of days the sentiment has hit')),
                ('days_missed', models.IntegerField(null=True, verbose_name='Number of days it missed target after publication')),
                ('days_to_first_hit', models.IntegerField(null=True, verbose_name='Number of days it took to first hit target after publication')),
                ('days_to_first_miss', models.IntegerField(null=True, verbose_name='Number of days it took to first miss target after publication')),
            ],
        ),
        migrations.CreateModel(
            name='Writes',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('analyst', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='reports.analyst', verbose_name='Related analyst')),
                ('report', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='reports.report', verbose_name='Related report')),
            ],
        ),
        migrations.CreateModel(
            name='Stock',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=100, verbose_name='Name of the stock')),
                ('code', models.CharField(max_length=50, verbose_name='Code of the stock')),
                ('currency', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='reports.currency', verbose_name='Currency for this stock')),
            ],
        ),
        migrations.AddField(
            model_name='report',
            name='stock',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='reports.stock', verbose_name='Related stock'),
        ),
        migrations.CreateModel(
            name='Point',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('content', models.TextField(verbose_name='Content of the point')),
                ('is_positive', models.BooleanField(default=True, verbose_name='Is this a positive point?')),
                ('report', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='reports.report', verbose_name='Related report')),
            ],
        ),
        migrations.AddConstraint(
            model_name='currency',
            constraint=models.CheckConstraint(check=models.Q(('code__regex', '^[A-Z]+$')), name='code_all_uppercase', violation_error_message='Code must be all uppercase'),
        ),
        migrations.AddConstraint(
            model_name='currency',
            constraint=models.CheckConstraint(check=models.Q(('name__regex', '^[a-z]+$')), name='name_all_lowercase', violation_error_message='Name must be all lowercase'),
        ),
        migrations.AddConstraint(
            model_name='analyst',
            constraint=models.CheckConstraint(check=models.Q(('hit_rate__gte', 0.0), ('hit_rate__lte', 1.0)), name='analyst_hitrate_range'),
        ),
        migrations.AddConstraint(
            model_name='writes',
            constraint=models.UniqueConstraint(fields=('analyst', 'report'), name='unique_analyst_report'),
        ),
        migrations.AddConstraint(
            model_name='report',
            constraint=models.CheckConstraint(check=models.Q(('hit_rate__gte', 0.0), ('hit_rate__lte', 1.0)), name='report_hitrate_range'),
        ),
    ]
