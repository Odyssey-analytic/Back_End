from django.contrib import admin
from django.urls import path, include
from .views import CreateAccount
urlpatterns = [
    path('account/', CreateAccount.as_view(), name='create-account'),
]