import django.core.validators
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("payments", "0002_payment_property"),
    ]

    operations = [
        migrations.AddField(
            model_name="payment",
            name="unallocated_amount",
            field=models.DecimalField(
                decimal_places=2,
                default=0,
                help_text="Verified payment funds not yet allocated to rent charges.",
                max_digits=14,
                validators=[django.core.validators.MinValueValidator(0)],
            ),
        ),
    ]
