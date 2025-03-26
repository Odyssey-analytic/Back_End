from django.urls import re_path
from .consumers import KPI_Monitor

sse_urlpatterns = [
    re_path(r"^kpi/sse/$", KPI_Monitor.as_asgi()),
]