import apps.leagues.models
import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('castaways', '0001_initial'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='League',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False)),
                ('name', models.CharField(max_length=255)),
                ('slug', models.SlugField(blank=True, max_length=300, unique=True)),
                ('season', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='leagues', to='castaways.season')),
                ('owner', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='owned_leagues', to=settings.AUTH_USER_MODEL)),
                ('invite_code', models.CharField(blank=True, max_length=8, unique=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
            ],
        ),
        migrations.CreateModel(
            name='Membership',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False)),
                ('league', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='memberships', to='leagues.league')),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='memberships', to=settings.AUTH_USER_MODEL)),
                ('joined_at', models.DateTimeField(auto_now_add=True)),
            ],
        ),
        migrations.AlterUniqueTogether(name='membership', unique_together={('league', 'user')}),
        migrations.CreateModel(
            name='Roster',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False)),
                ('league', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='rosters', to='leagues.league')),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='rosters', to=settings.AUTH_USER_MODEL)),
            ],
        ),
        migrations.AlterUniqueTogether(name='roster', unique_together={('league', 'user')}),
        migrations.CreateModel(
            name='RosterSlot',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False)),
                ('roster', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='slots', to='leagues.roster')),
                ('castaway', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='roster_slots', to='castaways.castaway')),
                ('slot_number', models.IntegerField()),
                ('added_at', models.DateTimeField(auto_now_add=True)),
            ],
        ),
        migrations.AlterUniqueTogether(name='rosterslot', unique_together={('roster', 'slot_number')}),
        migrations.AddConstraint(
            model_name='rosterslot',
            constraint=models.UniqueConstraint(fields=['roster', 'castaway'], name='unique_castaway_per_roster'),
        ),
        migrations.CreateModel(
            name='Perk',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False)),
                ('roster', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='perks', to='leagues.roster')),
                ('perk_type', models.CharField(choices=[('swap', 'Swap'), ('boost', 'Boost')], max_length=10)),
                ('used', models.BooleanField(default=False)),
                ('used_at', models.DateTimeField(blank=True, null=True)),
                ('boost_target_episode', models.IntegerField(blank=True, null=True)),
                ('swapped_out_castaway', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='swapped_out_perks', to='castaways.castaway')),
                ('swapped_in_castaway', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='swapped_in_perks', to='castaways.castaway')),
            ],
        ),
        migrations.AlterUniqueTogether(name='perk', unique_together={('roster', 'perk_type')}),
    ]
