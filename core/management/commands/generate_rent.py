from django.core.management.base import BaseCommand
from rent.services import generate_monthly_charges
class Command(BaseCommand):
 help="Generate rent charges for active tenancies for the current month."
 def handle(self,*args,**options):
  created=generate_monthly_charges()
  self.stdout.write(self.style.SUCCESS(f"Created {len(created)} rent charge(s)."))
