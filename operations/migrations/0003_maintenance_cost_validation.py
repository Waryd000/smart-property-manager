from django.core.validators import MinValueValidator
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("operations", "0002_expense_payment_tracking"),
    ]

    operations = [
        migrations.AlterField(
            model_name="maintenancerequest",
            name="actual_cost",
            field=models.DecimalField(
                blank=True,
                decimal_places=2,
                max_digits=14,
                null=True,
                validators=[MinValueValidator(0)],
            ),
        ),
        migrations.AlterField(
            model_name="maintenancerequest",
            name="estimated_cost",
            field=models.DecimalField(
                blank=True,
                decimal_places=2,
                max_digits=14,
                null=True,
                validators=[MinValueValidator(0)],
            ),
        ),
    ]
