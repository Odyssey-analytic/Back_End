import asyncio
from channels.generic.http import AsyncHttpConsumer

class SSEConsumer(AsyncHttpConsumer):
    async def handle(self, body):
        # Send HTTP headers for SSE
        await self.send_headers(headers=[
            (b"Content-Type", b"text/event-stream"),
            (b"Cache-Control", b"no-cache"),
            (b"Connection", b"keep-alive"),
        ])

        # Start sending events
        for i in range(10):  # Example: sending 10 messages
            await asyncio.sleep(1)  # Simulate server-side delay
            await self.send_body(f"data: Event {i}\n\n".encode("utf-8"), more_body=True)

        await self.send_body(b"", more_body=False)

    async def disconnect(self):
        print("Client disconnected")
