from django.contrib import admin
from django.urls import path, include
from .views import UserView, TokenView
urlpatterns = [
    path('user/', UserView.as_view(), name='account'),
    path('token/', TokenView.as_view(), name='token')
]