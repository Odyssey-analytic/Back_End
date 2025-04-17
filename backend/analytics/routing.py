from django.urls import re_path
from .consumers import KPI_Monitor, AverageSessionLength_Monitor

sse_urlpatterns = [
    re_path(r"^kpi/sse/SessionLengthAvr$", AverageSessionLength_Monitor.as_asgi()),
    re_path(r"^kpi/sse/$", KPI_Monitor.as_asgi()),
]