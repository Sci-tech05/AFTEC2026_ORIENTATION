from django.urls import path

from . import views

app_name = "rapports"

urlpatterns = [
    path("<int:candidat_id>/pdf/", views.rapport_pdf, name="rapport_pdf"),
]
