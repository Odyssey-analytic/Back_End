import asyncio
from channels.generic.http import AsyncHttpConsumer
from channels.layers import get_channel_layer
from asgiref.sync import sync_to_async
from analytics.models import GlobalKPIDaily, Token
import json
import uuid

class KPI_Monitor(AsyncHttpConsumer):
    async def handle(self, body):
        await self.send_headers(headers=[
            (b"Cache-Control", b"no-cache"),
            (b"Content-Type", b"text/event-stream"),
            (b"Transfer-Encoding", b"chunked"),
        ])
        data = json.loads(body)
        token_value = data['token']
        kpi = data['kpi']
        group = f"{token_value}.{kpi}"
        print(group)
        await self.channel_layer.group_add(group, self.channel_name)
        print(self.channel_layer)
        token_obj = await sync_to_async(Token.objects.get)(value=token_value)
        kpi = await sync_to_async(GlobalKPIDaily.objects.get)(token=token_obj)
        try:
            prev_value = None
            while True:
                await asyncio.sleep(10)
                kpi = await sync_to_async(GlobalKPIDaily.objects.get)(token=token_obj)
                #print(kpi)
                current_value = kpi.daily_active_users
                await self.send_sse_message({"text": json.dumps(current_value)})
                
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