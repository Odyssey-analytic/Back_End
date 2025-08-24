from django.urls import re_path
from .consumers import KPI_Monitor, GameEventSSEConsumer, DailyActiveUsersConsumer, AverageFPSConsumer, AverageMemoryUsageConsumer, AverageSessionDurationConsumer, TotalRevenuePerCurrencyConsumer, ARPPUConsumer, CrashRateConsumer

sse_urlpatterns = [
    re_path(r"^kpi/sse/$", KPI_Monitor.as_asgi()),
    re_path(r"^kpi/sse/EventCount$", GameEventSSEConsumer.as_asgi()),
    re_path(r"^kpi/sse/DailyActiveUsers$", DailyActiveUsersConsumer.as_asgi()),
    re_path(r"^kpi/sse/AverageFPS$", AverageFPSConsumer.as_asgi()),
    re_path(r"^kpi/sse/AverageMemoryUsage$", AverageMemoryUsageConsumer.as_asgi()),
    re_path(r"^kpi/sse/AverageSessionDuration$", AverageSessionDurationConsumer.as_asgi()),
    re_path(r"^kpi/sse/TotalRevenuePerCurrency$", TotalRevenuePerCurrencyConsumer.as_asgi()),
    re_path(r"^kpi/sse/ARPPU$", ARPPUConsumer.as_asgi()),#d
    #re_path(r"^kpi/sse/LevelCompletionRate$", LevelCompletionRateConsumer.as_asgi()),
    #re_path(r"^kpi/sse/AverageTriesPerLevel$", AverageTriesPerLevelConsumer.as_asgi()),
    #re_path(r"^kpi/sse/NetResourceFlow$", NetResourceFlowConsumer.as_asgi()),
    re_path(r"^kpi/sse/CrashRate$", CrashRateConsumer.as_asgi()),
    #re_path(r"^kpi/sse/ResourceSinkRatio$", ResourceSinkRatioConsumer.as_asgi()),
    #re_path(r"^kpi/sse/TopErrorTypes$", TopErrorTypesConsumer.as_asgi()),
]