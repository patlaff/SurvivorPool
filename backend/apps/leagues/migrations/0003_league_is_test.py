from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('leagues', '0002_league_draft_window'),
    ]

    operations = [
        migrations.AddField(
            model_name='league',
            name='is_test',
            field=models.BooleanField(
                default=False,
                help_text='When True, all draft and perk restrictions are relaxed for testing purposes.',
            ),
        ),
    ]
