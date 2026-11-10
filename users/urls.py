from django.urls import path

from .views import LoginAPIView, MeAPIView, RefreshAPIView, RegisterAPIView

urlpatterns = [
    path('auth/register', RegisterAPIView.as_view()),
    path('auth/login', LoginAPIView.as_view()),
    path('auth/refresh', RefreshAPIView.as_view()),
    path('users/me', MeAPIView.as_view()),
]