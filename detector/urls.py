# Create this file
from django.urls import path
from . import views

urlpatterns = [
    path('', views.upload_video, name='upload'),
    path('results/<int:video_id>/', views.video_results, name='results'),
]
