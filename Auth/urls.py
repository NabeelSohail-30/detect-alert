from django.urls import path
from .views import custom_login, custom_logout

urlpatterns = [
    path('', custom_login, name='login'),
    path('logout/', custom_logout, name='logout'),
]
