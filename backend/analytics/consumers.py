import asyncio
from channels.generic.http import AsyncHttpConsumer
from channels.layers import get_channel_layer

class KPI_Monitor(AsyncHttpConsumer):
    async def handle(self, body):
        self.channel_layer = get_channel_layer()
        print(self.channel_layer)
        await self.send_headers(headers=[
            (b"Cache-Control", b"no-cache"),
            (b"Content-Type", b"text/event-stream"),
            (b"Transfer-Encoding", b"chunked"),
        ])
        print("salam")
        self.channel_name = "channel_test"
        await self.channel_layer.group_add("sse_group", self.channel_name)

        try:
            while True:
                await asyncio.sleep(15)
                await self.send_body(b": keepalive\n\n", more_body=True)
        except asyncio.CancelledError:
            await self.channel_layer.group_discard("sse_group", self.channel_name)

    async def send_sse_message(self, event):
        message = event["text"]
        await self.send_body(f"data: {message}\n\n".encode(), more_body=True)