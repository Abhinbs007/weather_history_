from django.urls import path
from . import views

urlpatterns = [
    path('', views.weather_archive, name='get_emissions_sources'),
]
