from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("tenants", "0003_active_tenancy_requires_start_date"),
        ("tenants", "0003_tenant_created_by"),
    ]

    operations = []
