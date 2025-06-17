import os
from channels.routing import ProtocolTypeRouter, URLRouter
from django.core.asgi import get_asgi_application
from channels.auth import AuthMiddlewareStack
import yolo_detection.routing

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'yolo_detection.settings')

application = ProtocolTypeRouter({
    "http": get_asgi_application(),
    "websocket": AuthMiddlewareStack(
        URLRouter(
            yolo_detection.routing.websocket_urlpatterns
        )
    ),
})
