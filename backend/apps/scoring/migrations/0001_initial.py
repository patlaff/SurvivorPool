import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('castaways', '0001_initial'),
        ('leagues', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='ScoringEvent',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False)),
                ('castaway', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='scoring_events', to='castaways.castaway')),
                ('episode', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='scoring_events', to='castaways.episode')),
                ('event_name', models.CharField(max_length=50)),
                ('points', models.IntegerField()),
            ],
            options={'ordering': ['episode__episode_number', 'castaway__name']},
        ),
        migrations.AlterUniqueTogether(
            name='scoringevent',
            unique_together={('castaway', 'episode', 'event_name')},
        ),
        migrations.CreateModel(
            name='PlayerEpisodeScore',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False)),
                ('roster', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='episode_scores', to='leagues.roster')),
                ('episode', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='player_scores', to='castaways.episode')),
                ('raw_points', models.IntegerField(default=0)),
                ('multiplier', models.DecimalField(decimal_places=1, default='1.0', max_digits=3)),
                ('final_points', models.IntegerField(default=0)),
            ],
            options={'ordering': ['-final_points']},
        ),
        migrations.AlterUniqueTogether(
            name='playerepisodescore',
            unique_together={('roster', 'episode')},
        ),
    ]
