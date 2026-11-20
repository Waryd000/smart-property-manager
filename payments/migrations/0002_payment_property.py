import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("payments", "0001_initial"),
        ("properties", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="payment",
            name="property",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.PROTECT,
                related_name="payments",
                to="properties.property",
            ),
        ),
    ]
