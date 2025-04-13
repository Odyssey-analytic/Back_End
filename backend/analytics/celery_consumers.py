from celery import Celery
from celery import bootsteps
from kombu import Consumer, Exchange, Queue
import sys, json

from analytics.models import Token, Client, Session
from analytics.serializers import SessionStartEventSerializer, SessionEndEventSerializer
from analytics.services.QueueCollection import QueueCollection
from analytics.services.Utilities import send_update_to_group

def get_queue_name(fullname):
    return fullname.split('.')[2]

def is_running_under_celery():
    return 'celery' in sys.argv[0] or any('celery' in arg for arg in sys.argv)

def is_running_under_uvicorn():
    return 'uvicorn' in sys.argv[0] or any('uvicorn' in arg for arg in sys.argv)

# Do not change!
if is_running_under_celery():
    queue_collection = QueueCollection()
    queues = queue_collection.queues
    print(queue_collection.queues)

# You can add event listeners here
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

            serializer = SessionEndEventSerializer(data=data)
            if serializer.is_valid():
                serializer.save()

            print(f"End Session Event: {body} digested")
            message.ack()
        except Exception as e:
            print(f"error occured for message {body}: {e}")
