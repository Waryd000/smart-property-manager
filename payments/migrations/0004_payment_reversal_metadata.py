from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("payments", "0003_payment_unallocated_amount"),
    ]

    operations = [
        migrations.AddField(
            model_name="payment",
            name="reversed_at",
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="payment",
            name="reversed_by",
            field=models.ForeignKey(
                blank=True, null=True, on_delete=django.db.models.deletion.PROTECT,
                related_name="reversed_payments", to=settings.AUTH_USER_MODEL,
            ),
        ),
        migrations.AddField(
            model_name="payment",
            name="reversal_reason",
            field=models.TextField(blank=True),
        ),
        migrations.AddField(
            model_name="paymentallocation",
            name="reversed_at",
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="paymentallocation",
            name="reversed_by",
            field=models.ForeignKey(
                blank=True, null=True, on_delete=django.db.models.deletion.PROTECT,
                related_name="reversed_payment_allocations", to=settings.AUTH_USER_MODEL,
            ),
        ),
        migrations.AddField(
            model_name="paymentallocation",
            name="reversal_reason",
            field=models.TextField(blank=True),
        ),
    ]
