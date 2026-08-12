from django.urls import path

from . import views

app_name = "core"

urlpatterns = [
    path("", views.home, name="home"),
    path("models", views.models_catalog, name="models_catalog"),
    path("v1/models", views.models_catalog, name="models_catalog_v1"),
    path("etablissements/", views.etablissements, name="etablissements"),
]
