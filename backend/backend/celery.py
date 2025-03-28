import os, sys, django, json
from celery import bootsteps, Celery
from kombu import Consumer

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'backend.settings')
django.setup()

from analytics.models import Token, GlobalKPIDaily
from analytics.services.QueueCollection import QueueCollection
from analytics.services.Utilities import send_update_to_group

app = Celery('backend')

app.config_from_object('django.conf:settings', namespace='CELERY')

def is_running_under_celery():
    return 'celery' in sys.argv[0] or any('celery' in arg for arg in sys.argv)

def is_running_under_uvicorn():
    return 'uvicorn' in sys.argv[0] or any('uvicorn' in arg for arg in sys.argv)


app.autodiscover_tasks()
if is_running_under_celery():
    queue_collection = QueueCollection()
    queues = queue_collection.queues
    print(queue_collection.queues)

def get_queue_name(fullname):
    return fullname.split('.')[2]

class StartSessionEvent(bootsteps.ConsumerStep):

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
            token_value = data['token']
            cid = data['cid']
            token = Token.objects.get(value=token_value)
            group_name = f"{token.value}.current_active_users"
            print(group_name)
            send_update_to_group(f"1", group_name)
            kpi_qs = GlobalKPIDaily.objects.filter(token=token)
            if kpi_qs.exists():
                latest_kpi = kpi_qs.latest('date')
                print(f"daily active users: {latest_kpi.daily_active_users}")
            else:
                print(f"No KPI data found for token: {token_value} Initializing one")
                latest_kpi = GlobalKPIDaily.objects.create(token=token, daily_active_users=0)
            latest_kpi.daily_active_users += 1
            latest_kpi.save()
            print(f"daily active users: {latest_kpi.daily_active_users}")
            message.ack()
        except Exception as e:
            print(f"error occured for message {body}: {e}")

class EndSessionEvent(bootsteps.ConsumerStep):

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
            token_value = data['token']
            cid = data['cid']
            token = Token.objects.get(value=token_value)
            kpi_qs = GlobalKPIDaily.objects.filter(token=token)
            if kpi_qs.exists():
                latest_kpi = kpi_qs.latest('date')
                print(f"daily active users: {latest_kpi.daily_active_users}")
            else:
                print(f"No KPI data found for token: {token_value} Initializing one")
                latest_kpi = GlobalKPIDaily.objects.create(token=token, daily_active_users=1)
            latest_kpi.daily_active_users -= 1
            latest_kpi.save()
            print(f"daily active users: {latest_kpi.daily_active_users}")
            message.ack()
        except Exception as e:
            print(f"error occured for message {body}: {e}")

app.steps['consumer'].add(StartSessionEvent)
app.steps['consumer'].add(EndSessionEvent)

@app.task(bind=True, ignore_result=True)
def debug_task(self):
    print(f'Request: {self.request!r}')
