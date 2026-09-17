from django.urls import path

from opportunities import views

urlpatterns = [
    path("opportunities/search/", views.search, name="search"),
    path("health/", views.health, name="health"),
    path("validation-report/", views.validation_report, name="validation-report"),
]
