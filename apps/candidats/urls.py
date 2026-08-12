from django.urls import path

from . import views

app_name = "candidats"

urlpatterns = [
    path("", views.orientation_create, name="orientation"),
    path("<int:pk>/resultats/", views.resultats, name="resultats"),
]
