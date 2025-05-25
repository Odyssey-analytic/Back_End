from celery import Celery
from celery import bootsteps
from kombu import Consumer, Exchange, Queue
import sys, json

from analytics.models import Token, Client, Session
from analytics.serializers import SessionStartEventSerializer, SessionEndEventSerializer, BussinessEventSerializer, ErrorEventSerializer, ProgeressionEventSerializer, QualityEventSerializer, ResourceEventSerializer
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
            product_obj = token_obj.Product

            session_obj = Session.objects.create(
                id=session_id,
                token=token_obj,
                client=client_obj,
                start_time=data["time"],
                platform=data["platform"],
            )

            print(f"Session created with ID: {session_obj.id}")


            data['session'] = session_obj.id

            data['product'] = product_obj.id

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


class BussinessEventAction(bootsteps.ConsumerStep):
    name = 'BussinessEventAction' 
    def get_consumers(self, channel):
        filtered_queues = queue_collection.get_queues(lambda q: get_queue_name(q.name) == 'bussiness')
        return [Consumer(channel,
                         queues=filtered_queues,
                         callbacks=[self.handle_message],
                         accept=['json'])]

    def handle_message(self, body, message):
        try:
            print(f'Received Bussiness Event message: {body}')
            data = json.loads(body)

            session_id = data["session"]

            if not session_id:
                raise ValueError("Missing required field: 'session_id'.")

            session = None
            try:
                session = Session.objects.get(id=session_id)
            except Session.DoesNotExist:
                raise ValueError(f"Session with id '{session_id}' not found.")

            serializer = BussinessEventSerializer(data=data)
            if serializer.is_valid():
                serializer.save()
            else:
                print("serializer is not valid")
                print(serializer.errors)

            print(f"Bussiness Event: {body} digested")
            message.ack()
        except Exception as e:
            print(f"error occurred for message {body}: {e}")


class ErrorEventAction(bootsteps.ConsumerStep):
    name = 'ErrorEventAction' 
    def get_consumers(self, channel):
        filtered_queues = queue_collection.get_queues(lambda q: get_queue_name(q.name) == 'error')
        return [Consumer(channel,
                         queues=filtered_queues,
                         callbacks=[self.handle_message],
                         accept=['json'])]

    def handle_message(self, body, message):
        try:
            print(f'Received Error Event message: {body}')
            data = json.loads(body)

            session_id = data["session"]

            if not session_id:
                raise ValueError("Missing required field: 'session_id'.")

            session = None
            try:
                session = Session.objects.get(id=session_id)
            except Session.DoesNotExist:
                raise ValueError(f"Session with id '{session_id}' not found.")

            serializer = ErrorEventSerializer(data=data)
            if serializer.is_valid():
                serializer.save()
            else:
                print("serializer is not valid")
                print(serializer.errors)

            print(f"Error Event: {body} digested")
            message.ack()
        except Exception as e:
            print(f"error occurred for message {body}: {e}")


class ProgeressionEventAction(bootsteps.ConsumerStep):
    name = 'ProgeressionEventAction' 
    def get_consumers(self, channel):
        filtered_queues = queue_collection.get_queues(lambda q: get_queue_name(q.name) == 'progeression')
        return [Consumer(channel,
                         queues=filtered_queues,
                         callbacks=[self.handle_message],
                         accept=['json'])]

    def handle_message(self, body, message):
        try:
            print(f'Received Progeression Event message: {body}')
            data = json.loads(body)

            session_id = data["session"]

            if not session_id:
                raise ValueError("Missing required field: 'session_id'.")

            session = None
            try:
                session = Session.objects.get(id=session_id)
            except Session.DoesNotExist:
                raise ValueError(f"Session with id '{session_id}' not found.")

            serializer = ProgeressionEventSerializer(data=data)
            if serializer.is_valid():
                serializer.save()
            else:
                print("serializer is not valid")
                print(serializer.errors)

            print(f"Progeression Event: {body} digested")
            message.ack()
        except Exception as e:
            print(f"error occurred for message {body}: {e}")


class QualityEventAction(bootsteps.ConsumerStep):
    name = 'QualityEventAction' 
    def get_consumers(self, channel):
        filtered_queues = queue_collection.get_queues(lambda q: get_queue_name(q.name) == 'quality')
        return [Consumer(channel,
                         queues=filtered_queues,
                         callbacks=[self.handle_message],
                         accept=['json'])]

    def handle_message(self, body, message):
        try:
            print(f'Received Quality Event message: {body}')
            data = json.loads(body)

            session_id = data["session"]

            if not session_id:
                raise ValueError("Missing required field: 'session_id'.")

            session = None
            try:
                session = Session.objects.get(id=session_id)
            except Session.DoesNotExist:
                raise ValueError(f"Session with id '{session_id}' not found.")

            serializer = QualityEventSerializer(data=data)
            if serializer.is_valid():
                serializer.save()
            else:
                print("serializer is not valid")
                print(serializer.errors)

            print(f"Quality Event: {body} digested")
            message.ack()
        except Exception as e:
            print(f"error occurred for message {body}: {e}")


class ResourceEventAction(bootsteps.ConsumerStep):
    name = 'ResourceEventAction' 
    def get_consumers(self, channel):
        filtered_queues = queue_collection.get_queues(lambda q: get_queue_name(q.name) == 'resource')
        return [Consumer(channel,
                         queues=filtered_queues,
                         callbacks=[self.handle_message],
                         accept=['json'])]

    def handle_message(self, body, message):
        try:
            print(f'Received Resource Event message: {body}')
            data = json.loads(body)

            session_id = data["session"]

            if not session_id:
                raise ValueError("Missing required field: 'session_id'.")

            session = None
            try:
                session = Session.objects.get(id=session_id)
            except Session.DoesNotExist:
                raise ValueError(f"Session with id '{session_id}' not found.")

            serializer = ResourceEventSerializer(data=data)
            if serializer.is_valid():
                serializer.save()
            else:
                print("serializer is not valid")
                print(serializer.errors)

            print(f"Resource Event: {body} digested")
            message.ack()
        except Exception as e:
            print(f"error occurred for message {body}: {e}")


