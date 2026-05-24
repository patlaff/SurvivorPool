import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('leagues', '0005_league_is_archived'),
    ]

    operations = [
        migrations.AddField(
            model_name='league',
            name='buy_in_amount',
            field=models.DecimalField(
                blank=True,
                decimal_places=2,
                help_text='Optional monetary buy-in amount for the league.',
                max_digits=8,
                null=True,
            ),
        ),
        migrations.AddField(
            model_name='league',
            name='venmo_handle',
            field=models.CharField(
                blank=True,
                help_text="Owner's Venmo handle for collecting buy-ins.",
                max_length=100,
                null=True,
            ),
        ),
        migrations.AddField(
            model_name='membership',
            name='bought_in',
            field=models.BooleanField(
                default=False,
                help_text='Whether this member has paid the league buy-in.',
            ),
        ),
    ]
