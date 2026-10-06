# views.py
from django.shortcuts import render
from .models import ServiceCategory  # Or Service depending on model location


def services_view(request):
    categories = ServiceCategory.objects.prefetch_related("services").all()
    return render(request, "pages/services.html", {"categories": categories})