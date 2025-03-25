import os
from celery import bootsteps
from kombu import Consumer, Exchange, Queue

from celery import Celery

# Set the default Django settings module for the 'celery' program.
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'proj.settings')
import django
django.setup()
from analytics.models import Token
app = Celery('proj')

# Using a string here means the worker doesn't have to serialize
# the configuration object to child processes.
# - namespace='CELERY' means all celery-related configuration keys
#   should have a `CELERY_` prefix.
app.config_from_object('django.conf:settings', namespace='CELERY')

# Load task modules from all registered Django apps.
app.autodiscover_tasks()

my_queue1 = Queue('testQueue1', Exchange('testExchange1'), 'test1')
my_queue2 = Queue('testQueue2', Exchange('testExchange2'), 'test2')
print(my_queue1)
queues = [my_queue1, my_queue2]

class StartSessionEvent(bootsteps.ConsumerStep):

    def get_consumers(self, channel):
        return [Consumer(channel,
                         queues=queues,
                         callbacks=[self.handle_message],
                         accept=['json'])]

    def handle_message(self, body, message):
        Token.objects.get_or_create()
        print("successfully worked with database :)")
        print(f'Received message: {Token.objects.get_or_create()}')
        message.ack()

class EndSessionEvent(bootsteps.ConsumerStep):

    def get_consumers(self, channel):
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
