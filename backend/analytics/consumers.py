import asyncio
from channels.generic.http import AsyncHttpConsumer
from channels.layers import get_channel_layer
from asgiref.sync import sync_to_async
from analytics.models import GlobalKPIDaily, Token
import json
from urllib.parse import parse_qs
from datetime import datetime,timezone
import uuid

class KPI_Monitor(AsyncHttpConsumer):
    async def handle(self, body):
        await self.send_headers(headers=[
            (b"Cache-Control", b"no-cache"),
            (b"Content-Type", b"text/event-stream"),
            (b"Transfer-Encoding", b"chunked"),
            (b'Access-Control-Allow-Origin', b'http://localhost:5173'),
            (b'Access-Control-Allow-Credentials', b'true')
        ])
        query = parse_qs(self.scope["query_string"].decode())
        token_value = query.get("token", [None])[0]
        kpi = query.get("kpi", [None])[0]
        group = f"{token_value}.{kpi}"

        if not token_value or not kpi:
            await self.send_body(b"data: Invalid request\n\n", more_body=False)
            return
        
        print(group)
        await self.channel_layer.group_add(group, self.channel_name)
        print(self.channel_layer)
        try:
            prev_value = None
            while True:
                await asyncio.sleep(5)
                kpi = await sync_to_async(GlobalKPIDaily.objects.get)(token=token_obj)
                #print(kpi)
                now_utc = datetime.now(timezone.utc)
                formatted = now_utc.strftime("%Y-%m-%dT%H:%M:%SZ")
                current_value = kpi.daily_active_users
                payload = {
                    "timestamp": formatted,
                    "value": current_value
                }
                await self.send_sse_message({"text": json.dumps(payload)})
                
                # if prev_value == current_value:
                #     continue
                # else:
                #     if(current_value == "null"):
                #         current_value = 0
                #     prev_value = current_value
                #     await self.send_sse_message({"text": json.dumps(current_value)})
        except asyncio.CancelledError:
            await self.channel_layer.group_discard("sse_group", self.channel_name)

    async def send_sse_message(self, event):
        message = event["text"]
        print(event)
        await self.send_body(f"data: {message}\n\n".encode(), more_body=True)