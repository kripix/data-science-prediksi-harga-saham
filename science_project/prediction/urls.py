# from django.contrib import admin
from django.urls import path
from prediction import views


urlpatterns = [
    path("", views.PredictionView.as_view(), name="prediction"),
]
