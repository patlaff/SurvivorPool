from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('leagues', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='league',
            name='draft_close_at',
            field=models.DateTimeField(
                blank=True,
                null=True,
                help_text='If set, the draft closes at this datetime (overrides season lock date).',
            ),
        ),
        migrations.AddField(
            model_name='league',
            name='draft_force_open',
            field=models.BooleanField(
                default=False,
                help_text='When True, the draft is open regardless of draft_close_at or season lock date.',
            ),
        ),
    ]
