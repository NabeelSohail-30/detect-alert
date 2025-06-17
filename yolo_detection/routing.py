from django.urls import re_path
from . import consumers

websocket_urlpatterns = [
    re_path(r'ws/detect/(?P<video_id>\d+)/$', consumers.VideoAlertConsumer.as_asgi()),
]
