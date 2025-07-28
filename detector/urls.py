from django.urls import path
from . import views

app_name = 'detector'

urlpatterns = [
    path('', views.home, name='home'),
    path('dashboard/', views.dashboard, name='dashboard'),
    path('upload/', views.upload_video, name='upload'),
    path('insights/', views.insights, name='insights'),
    
    path('live/', views.live_page, name='live_page'),
    path('live/feed/', views.live_feed, name='live_feed'),
    path('live/start/', views.start_live_detection, name='start_live_detection'),
    path('live/stop/', views.stop_live_detection, name='stop_live_detection'),
]
