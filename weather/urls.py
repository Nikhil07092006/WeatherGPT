from django.urls import path
from . import views

urlpatterns = [
    path('', views.weather_home, name='weather_home'),
    path("forecast/", views.weather_forecast, name="weather_forecast"),
    path(
        "hourly/",
        views.hourly_weather,
        name="hourly-weather"
    ),
    path("chat/", views.chat_view, name="weather_chat"),
]