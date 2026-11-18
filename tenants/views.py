from django.contrib.auth.decorators import login_required
from django.shortcuts import render,redirect
from django import forms
from core.access import visible_properties
from .models import Tenant,Tenancy
from .forms import TenantForm,TenancyForm

@login_required
def tenant_list(request):
    allowed=visible_properties(request.user)
    tenants=Tenant.objects.filter(tenancies__unit__property__in=allowed).distinct()
    return render(request,"tenants/list.html",{"tenants":tenants})

@login_required
def tenant_create(request):
    form=TenantForm(request.POST or None)
    if form.is_valid(): form.save(); return redirect("tenant-list")
    return render(request,"properties/form.html",{"form":form,"title":"Add tenant"})

@login_required
def tenancy_create(request):
    form=TenancyForm(request.POST or None,request.FILES or None)
    form.fields["unit"].queryset=__import__("properties.models",fromlist=["Unit"]).Unit.objects.filter(property__in=visible_properties(request.user))
    if form.is_valid(): form.save(); return redirect("tenant-list")
    return render(request,"properties/form.html",{"form":form,"title":"Create tenancy"})
