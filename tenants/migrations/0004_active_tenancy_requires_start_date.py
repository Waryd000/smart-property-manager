from django.db import migrations, models
from django.db.models import Q


class Migration(migrations.Migration):

    dependencies = [
        ("tenants", "0003_tenant_created_by"),
    ]

    operations = [
        migrations.AddConstraint(
            model_name="tenancy",
            constraint=models.CheckConstraint(
                condition=~(Q(status="ACTIVE") & Q(start_date__isnull=True)),
                name="active_tenancy_requires_start_date",
            ),
        ),
    ]
