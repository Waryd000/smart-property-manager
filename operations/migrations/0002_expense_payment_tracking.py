from decimal import Decimal

from django.conf import settings
from django.core.validators import MinValueValidator
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("operations", "0001_initial"),
    ]

    operations = [
        migrations.AlterField(
            model_name="expense",
            name="amount",
            field=models.DecimalField(
                decimal_places=2,
                max_digits=14,
                validators=[MinValueValidator(Decimal("0.01"))],
            ),
        ),
        migrations.AddField(
            model_name="expense",
            name="paid_at",
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="expense",
            name="paid_by",
            field=models.ForeignKey(
                blank=True, null=True, on_delete=django.db.models.deletion.PROTECT,
                related_name="paid_expenses", to=settings.AUTH_USER_MODEL,
            ),
        ),
        migrations.AddField(
            model_name="expense",
            name="payment_reference",
            field=models.CharField(blank=True, max_length=120),
        ),
    ]
