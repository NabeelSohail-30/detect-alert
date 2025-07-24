from django.urls import path
from . import views

app_name = 'detector'

urlpatterns = [
    path('', views.home, name='home'),
    path('dashboard/', views.dashboard, name='dashboard'),
    path('upload/', views.upload_video, name='upload'),
    path('insights/', views.insights, name='insights'),
]
