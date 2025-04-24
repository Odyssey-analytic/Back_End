from django.contrib import admin
from django.urls import path, include
from .views import *
urlpatterns = [
    path('user/', UserView.as_view(), name='account'),
    path('token/', TokenView.as_view(), name='token'),
    path('signup/', CustomUserSignUpView.as_view(), name='signup'),
    path('login/', LoginView.as_view(), name='login'),
    path('request-reset-password/', PasswordResetRequestView.as_view(), name='request_reset_password'),
    path('reset-password/<token>/', PasswordResetConfirmView.as_view(), name='reset_password_confirm'),
    path('sign_in/', SignInAPIView.as_view(), name='sign_in'),
    path('auth-receiver', AuthReceiverAPIView.as_view(), name='auth_receiver'),
]