import asyncio
from channels.generic.http import AsyncHttpConsumer
from channels.layers import get_channel_layer
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
        unique_id = uuid.uuid4().hex[:8]
        self.channel_name = f"{token_value}.{kpi}.{unique_id}"
        group = f"{token_value}.{kpi}"
        await self.channel_layer.group_add(group, self.channel_name)

        try:
            while True:
                await asyncio.sleep(15)
                await self.send_body(b": keepalive\n\n", more_body=True)
        except asyncio.CancelledError:
            await self.channel_layer.group_discard("sse_group", self.channel_name)

    async def send_sse_message(self, event):
        message = event["text"]
        await self.send_body(f"data: {message}\n\n".encode(), more_body=True)