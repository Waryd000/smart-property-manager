from celery import shared_task
from .services import generate_monthly_charges

@shared_task
def generate_current_month_rent():
    return len(generate_monthly_charges())
