from celery import Celery
from celery import bootsteps
from kombu import Consumer, Exchange, Queue
import sys, json

from analytics.models import Token, Client, Session
from analytics.serializers import SessionStartEventSerializer, SessionEndEventSerializer
from analytics.services.QueueCollection import QueueCollection
from analytics.services.Utilities import send_update_to_group
from django.utils.dateparse import parse_datetime

def get_queue_name(fullname):
    return fullname.split('.')[2]

def is_running_under_celery():
    return 'celery' in sys.argv[0] or any('celery' in arg for arg in sys.argv)

def is_running_under_uvicorn():
    return 'uvicorn' in sys.argv[0] or any('uvicorn' in arg for arg in sys.argv)

if is_running_under_celery():
    queue_collection = QueueCollection()
    queues = queue_collection.queues
    print(queue_collection.queues)

class StartSessionEvent(bootsteps.ConsumerStep):
    name = 'StartSessionEvent' 
    def get_consumers(self, channel):
        filtered_queues = queue_collection.get_queues(lambda q: get_queue_name(q.name) == 'start_session')
        return [Consumer(channel,
                         queues=filtered_queues,
                         callbacks=[self.handle_message],
                         accept=['json'])]

    def handle_message(self, body, message):
        try:
            print(f'Received Start Session message: {body}')
            data = json.loads(body)

            session_id = data.get('session')
            if not session_id:
                print("Session ID not provided in message.")
                message.ack()
                return

            client_obj = Client.objects.get(id=data["client"])
            token_obj = client_obj.token


            session_obj = Session.objects.create(
                id=session_id,
                token=token_obj,
                client=client_obj,
                start_time=data["time"],
                platform=data["platform"],
            )

            print(f"Session created with ID: {session_obj.id}")


            data['session'] = session_obj.id

            serializer = SessionStartEventSerializer(data=data)
            if serializer.is_valid():
                serializer.save()
                print(f"Start Session Event: {body} digested")
            else:
                print("serializer is not valid")
                print(serializer.errors)

            message.ack()
        except Exception as e:
            print(f"error occurred for message {body}: {e}")

class EndSessionEvent(bootsteps.ConsumerStep):
    name = 'EndSessionEvent'
    def get_consumers(self, channel):
        filtered_queues = queue_collection.get_queues(lambda q: get_queue_name(q.name) == 'end_session')
        return [Consumer(channel,
                         queues=filtered_queues,
                         callbacks=[self.handle_message],
                         accept=['json'])]

    def handle_message(self, body, message):
        try:
            print(f'Received End Session message: {body}')
            data = json.loads(body)

            session_id = data["session"]
            end_time = parse_datetime(data["time"])

            if not session_id or not end_time:
                raise ValueError("Missing required fields: 'session_id' or 'end_time'.")

            try:
                session = Session.objects.get(id=session_id)
            except Session.DoesNotExist:
                raise ValueError(f"Session with id '{session_id}' not found.")

            session.end_time = end_time
            session.save()
            print(f"Session {session_id} end_time updated to {end_time}")

            serializer = SessionEndEventSerializer(data=data)
            if serializer.is_valid():
                serializer.save()
            else:
                print("serializer is not valid")
                print(serializer.errors)

            print(f"End Session Event: {body} digested")
            message.ack()

        except Exception as e:
            print(f"Error occurred for message {body}: {e}")