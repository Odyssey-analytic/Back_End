import asyncio
from channels.generic.http import AsyncHttpConsumer
from channels.layers import get_channel_layer
from asgiref.sync import sync_to_async, async_to_sync
from analytics.models import Token, Session
import json
from urllib.parse import parse_qs
from datetime import datetime,timezone
import uuid
from datetime import timedelta


async def get_running_avg_sessions(token, bucket_seconds=3600):
    ended_sessions = Session.objects.filter(end_time__isnull=False, token=token).order_by('end_time')
    ended_sessions_exsists_task = sync_to_async(ended_sessions.exists)() 
    if not (await ended_sessions_exsists_task):
        return []

    start_time_task = sync_to_async(ended_sessions.first)()
    end_time_task = sync_to_async(ended_sessions.last)()
    start_time = (await start_time_task).start_time
    end_time = (await end_time_task).end_time

    list_sessions_task = sync_to_async(list)(ended_sessions)
    bucket = timedelta(seconds=bucket_seconds)
    current_time = start_time
    result = []
    cumulative_duration = timedelta()
    count = 0
    session_index = 0
    sessions = await list_sessions_task

    while current_time <= end_time:
        while session_index < len(sessions) and sessions[session_index].end_time <= current_time:
            session = sessions[session_index]
            cumulative_duration += session.duration
            count += 1
            session_index += 1

        avg_duration = cumulative_duration.total_seconds() / count if count else 0

        result.append({
            "timestamp": current_time.isoformat(),
            "value": avg_duration
        })

        current_time += bucket

    return result

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

        await self.channel_layer.group_add(group, self.channel_name)
        
        try:
            prev_value = None
            while True:
                # Check if client is still connected
                if self.disconnected:
                    break
                    
                await asyncio.sleep(5)
                
                # Get your KPI data
                kpi = await sync_to_async(GlobalKPIDaily.objects.get)(token=token_obj)
                now_utc = datetime.now(timezone.utc)
                formatted = now_utc.strftime("%Y-%m-%dT%H:%M:%SZ")
                current_value = kpi.daily_active_users
                
                payload = {
                    "timestamp": formatted,
                    "value": current_value
                }
                
                try:
                    await self.send_sse_message({"text": json.dumps(payload)})
                except (ConnectionError, OSError):
                    # Client disconnected
                    break
                    
        except asyncio.CancelledError:
            # Handle cancellation
            pass
        except Exception as e:
            print(f"Error in SSE stream: {e}")
        finally:
            # Clean up resources
            await self.channel_layer.group_discard(group, self.channel_name)
            await self.send_body(b"", more_body=False)  # Properly close connection

    async def send_sse_message(self, event):
        try:
            message = event["text"]
            await self.send_body(f"data: {message}\n\n".encode(), more_body=True)
        except (ConnectionResetError, OSError) as e:
            self.disconnected = True
            raise




class AverageSessionLength_Monitor(AsyncHttpConsumer):
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

        if not token_value or not kpi:
            await self.send_body(b"data: Invalid request\n\n", more_body=False)
            return

        try:
            token_obj = await sync_to_async(Token.objects.get)(value=token_value)
            
            # Send initial payload
            payload = await get_running_avg_sessions(token_obj)
            await self.send_sse_message({"text": json.dumps(payload)})
            print(payload)

            bucket_seconds = 30
            bucket = timedelta(seconds=bucket_seconds)

            sessions = await sync_to_async(list)(Session.objects.filter(end_time__isnull=False, token=token_obj).order_by('end_time'))
            if not sessions:
                await self.send_sse_message({"text": json.dumps({"error": "the token doesn't have any sessions"})})
                return

            cumulative_duration = timedelta()
            count = 0
            session_index = 0
            current_time = sessions[0].start_time
            end_time = sessions[-1].end_time
            
            # Add a disconnection condition - stop if we've reached the end time
            while True:
                # Check if the client is still connected
                if self.is_disconnected():
                    print(f"Client disconnected for token {token_value}")
                    break

                # Get fresh session data
                sessions = await sync_to_async(list)(Session.objects.filter(end_time__isnull=False, token=token_obj).order_by('end_time'))
                
                if not sessions:
                    break
                    
                end_time = sessions[-1].end_time

                while session_index < len(sessions) and sessions[session_index].end_time <= current_time:
                    session = sessions[session_index]
                    cumulative_duration += session.duration
                    count += 1
                    session_index += 1

                avg_duration = cumulative_duration.total_seconds() / count if count else 0
                update_payload = {
                    "timestamp": current_time.isoformat(),
                    "value": avg_duration
                }

                try:
                    await self.send_sse_message({"text": json.dumps(update_payload)})
                    print("Update sent:", update_payload)
                except Exception as e:
                    print(f"Error sending message, client likely disconnected: {e}")
                    break

                current_time += bucket
                
                # Add a small delay to prevent CPU overload
                await asyncio.sleep(0.1)

            print(f"Stream completed for token {token_value}")
            
        except asyncio.CancelledError:
            print(f"Connection cancelled for token {token_value}")
            # Clean up group subscription if you're using one
            if hasattr(self, 'channel_layer') and hasattr(self, 'channel_name'):
                await self.channel_layer.group_discard("sse_group", self.channel_name)
        except Exception as e:
            print(f"Error in consumer: {e}")
        finally:
            # Make sure to properly close the connection
            if not self.is_disconnected():
                await self.send_body(b"", more_body=False)
            print(f"Connection closed for token {token_value}")

    async def send_sse_message(self, event):
        message = event["text"]
        await self.send_body(f"data: {message}\n\n".encode(), more_body=True)
    
    def is_disconnected(self):
        """Check if the client has disconnected."""
        return self.scope.get('client', None) is None or 'client' not in self.scope
