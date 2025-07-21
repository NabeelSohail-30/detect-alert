from django.urls import path
from . import views

urlpatterns = [
    path('', views.dashboard, name='dashboard'),
    path('upload/', views.upload_video, name='upload'),
    path('insights/', views.insights, name='insights'),
]
