from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('leagues', '0006_league_buyin_venmo_membership_boughtin'),
    ]

    operations = [
        migrations.AddField(
            model_name='league',
            name='payout_first',
            field=models.PositiveSmallIntegerField(
                blank=True,
                help_text='Percentage of the pot awarded to 1st place (must sum to 100 with 2nd and 3rd).',
                null=True,
            ),
        ),
        migrations.AddField(
            model_name='league',
            name='payout_second',
            field=models.PositiveSmallIntegerField(
                blank=True,
                help_text='Percentage of the pot awarded to 2nd place.',
                null=True,
            ),
        ),
        migrations.AddField(
            model_name='league',
            name='payout_third',
            field=models.PositiveSmallIntegerField(
                blank=True,
                help_text='Percentage of the pot awarded to 3rd place.',
                null=True,
            ),
        ),
    ]
