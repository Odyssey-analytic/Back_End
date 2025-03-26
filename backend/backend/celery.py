import os
from celery import bootsteps
from kombu import Consumer, Exchange, Queue
from celery import Celery
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'backend.settings')
import django
django.setup()
from analytics.models import Queue as db_queue
from analytics.services.QueueCollection import QueueCollection
app = Celery('backend')

app.config_from_object('django.conf:settings', namespace='CELERY')

app.autodiscover_tasks()

queue_collection = QueueCollection()
queues = queue_collection.queues
print(queue_collection.queues)

def get_queue_name(fullname):
    return fullname.split('.')[1]

class StartSessionEvent(bootsteps.ConsumerStep):

    def get_consumers(self, channel):
        filtered_queues = queue_collection.get_queues(lambda q: get_queue_name(q.name) == 'start_session')
        return [Consumer(channel,
                         queues=queues,
                         callbacks=[self.handle_message],
                         accept=['json'])]

    def handle_message(self, body, message):
        print("successfully worked with database :)")
        print(f'Received message: {body}')
        message.ack()

class EndSessionEvent(bootsteps.ConsumerStep):

    def get_consumers(self, channel):
        filtered_queues = queue_collection.get_queues(lambda q: get_queue_name(q.name) == 'end_session')
        return [Consumer(channel,
                         queues=queues,
                         callbacks=[self.handle_message],
                         accept=['json'])]

    def handle_message(self, body, message):
        print('Received message: {0!r}'.format(body))
        message.ack()


app.steps['consumer'].add(StartSessionEvent)
app.steps['consumer'].add(EndSessionEvent)

@app.task(bind=True, ignore_result=True)
def debug_task(self):
    print(f'Request: {self.request!r}')
