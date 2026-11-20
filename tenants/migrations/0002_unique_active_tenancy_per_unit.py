from django.db import migrations, models
from django.db.models import Q


class Migration(migrations.Migration):

    dependencies = [
        ("tenants", "0001_initial"),
    ]

    operations = [
        migrations.AddConstraint(
            model_name="tenancy",
            constraint=models.UniqueConstraint(
                fields=("unit",),
                condition=Q(status="ACTIVE"),
                name="one_active_tenancy_per_unit",
            ),
        ),
    ]
