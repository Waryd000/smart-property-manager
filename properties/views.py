from django.contrib.auth.decorators import login_required, user_passes_test
from django.shortcuts import render,redirect
from django import forms
from core.access import is_manager, visible_properties
from .models import Property,Unit
from .forms import PropertyForm,UnitForm

@login_required
def property_list(request):
    properties=visible_properties(request.user).prefetch_related("units")
    return render(request,"properties/list.html",{"properties":properties,"can_manage":is_manager(request.user)})

@login_required
@user_passes_test(is_manager)
def property_create(request):
    form=PropertyForm(request.POST or None)
    if form.is_valid(): form.save(); return redirect("property-list")
    return render(request,"properties/form.html",{"form":form,"title":"Add property"})

@login_required
def unit_create(request):
    form=UnitForm(request.POST or None)
    form.fields["property"].queryset=visible_properties(request.user)
    if form.is_valid(): form.save(); return redirect("property-list")
    return render(request,"properties/form.html",{"form":form,"title":"Add rental unit"})
