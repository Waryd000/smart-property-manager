from decimal import Decimal

import django.core.validators
from django.db import migrations, models
from django.db.models import Q


class Migration(migrations.Migration):

    dependencies = [
        ("payments", "0004_payment_reversal_metadata"),
    ]

    operations = [
        migrations.AlterField(
            model_name="banktransaction",
            name="amount",
            field=models.DecimalField(
                decimal_places=2,
                max_digits=14,
                validators=[django.core.validators.MinValueValidator(Decimal("0.01"))],
            ),
        ),
        migrations.AddConstraint(
            model_name="banktransaction",
            constraint=models.CheckConstraint(
                condition=Q(amount__gt=0),
                name="bank_transaction_amount_positive",
            ),
        ),
    ]
