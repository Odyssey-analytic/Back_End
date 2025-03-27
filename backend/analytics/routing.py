from django.urls import path
from .consumers import SSEConsumer

sse_urlpatterns = [
    path('sse/events/', SSEConsumer.as_asgi()),  # URL for SSE
]
