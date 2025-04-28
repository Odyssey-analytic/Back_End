import asyncio
import json
import uuid
from asgiref.sync import sync_to_async, async_to_sync
from channels.generic.http import AsyncHttpConsumer
from channels.layers import get_channel_layer
from datetime import datetime, timezone
from datetime import timedelta
from urllib.parse import parse_qs

from analytics.models import Token, Session


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

        print(group)
        await self.channel_layer.group_add(group, self.channel_name)
        print(self.channel_layer)
        try:
            prev_value = None
            while True:
                await asyncio.sleep(5)
                kpi = await sync_to_async(GlobalKPIDaily.objects.get)(token=token_obj)
                # print(kpi)
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

        token_obj = await sync_to_async(Token.objects.get)(value=token_value)

        try:
            payload = await get_running_avg_sessions(token_obj)
            await self.send_sse_message({"text": json.dumps(payload)})
            print(payload)

            bucket_seconds = 30
            bucket = timedelta(seconds=bucket_seconds)

            sessions = await sync_to_async(list)(Session.objects.filter(end_time__isnull=False, token=token_obj).order_by('end_time'))
            if not sessions:
                await self.send_sse_message({"text": json.dumps({"error": "the token dosent have any sessions"})})
                return

            cumulative_duration = timedelta()
            count = 0
            session_index = 0
            current_time = sessions[0].start_time
            end_time = sessions[-1].end_time

            while True:
                sessions = await sync_to_async(list)(Session.objects.filter(end_time__isnull=False, token=token_obj).order_by('end_time'))

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

                await self.send_sse_message({"text": json.dumps(update_payload)})
                print("Update sent:", update_payload)

                current_time += bucket

        except asyncio.CancelledError:
            await self.channel_layer.group_discard("sse_group", self.channel_name)
        except Exception as e:
            print(e)

    async def send_sse_message(self, event):
        message = event["text"]
        await self.send_body(f"data: {message}\n\n".encode(), more_body=True)

