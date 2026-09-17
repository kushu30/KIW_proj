from django.urls import path, include

urlpatterns = [
    path("", include("opportunities.urls")),
]
