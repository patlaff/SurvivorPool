from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('castaways', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='episode',
            name='is_merge',
            field=models.BooleanField(
                default=False,
                help_text='True on the first episode where the merged tribe appears.',
            ),
        ),
        migrations.AddField(
            model_name='episode',
            name='is_finale',
            field=models.BooleanField(
                default=False,
                help_text='True if this episode is the season finale.',
            ),
        ),
    ]
