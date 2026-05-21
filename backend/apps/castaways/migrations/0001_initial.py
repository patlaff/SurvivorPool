import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = []

    operations = [
        migrations.CreateModel(
            name='Season',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False)),
                ('season_number', models.IntegerField(unique=True)),
                ('name', models.CharField(max_length=255)),
                ('version', models.CharField(default='US', max_length=10)),
                ('is_active', models.BooleanField(default=False)),
                ('draft_lock_date', models.DateField(blank=True, null=True)),
            ],
            options={'ordering': ['season_number']},
        ),
        migrations.CreateModel(
            name='Castaway',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False)),
                ('castaway_id', models.CharField(max_length=20, unique=True)),
                ('season', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='castaways', to='castaways.season')),
                ('name', models.CharField(max_length=255)),
                ('age', models.IntegerField(blank=True, null=True)),
                ('hometown', models.CharField(blank=True, max_length=255)),
                ('occupation', models.CharField(blank=True, max_length=255)),
                ('is_eliminated', models.BooleanField(default=False)),
                ('eliminated_episode', models.IntegerField(blank=True, null=True)),
            ],
            options={'ordering': ['name']},
        ),
        migrations.CreateModel(
            name='Episode',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False)),
                ('season', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='episodes', to='castaways.season')),
                ('episode_number', models.IntegerField()),
                ('air_date', models.DateField()),
                ('scored_at', models.DateTimeField(blank=True, null=True)),
            ],
            options={'ordering': ['episode_number']},
        ),
        migrations.AlterUniqueTogether(
            name='episode',
            unique_together={('season', 'episode_number')},
        ),
    ]
