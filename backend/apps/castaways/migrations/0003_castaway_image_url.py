from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('castaways', '0002_episode_perk_flags'),
    ]

    operations = [
        migrations.AddField(
            model_name='castaway',
            name='image_url',
            field=models.URLField(blank=True, max_length=500),
        ),
    ]
