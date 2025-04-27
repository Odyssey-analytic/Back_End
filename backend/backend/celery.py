import os, sys, django
from celery import Celery, bootsteps
import inspect
from celery import shared_task

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'backend.settings')
django.setup()

app = Celery('celery')


app.config_from_object('django.conf:settings', namespace='CELERY')

def is_running_under_celery():
    return 'celery' in sys.argv[0] or any('celery' in arg for arg in sys.argv)

def is_running_under_uvicorn():
    return 'uvicorn' in sys.argv[0] or any('uvicorn' in arg for arg in sys.argv)


app.autodiscover_tasks()

@app.task(bind=True, ignore_result=True)
def debug_task(self):
    print(f'Request: {self.request!r}')

@shared_task
def add_queue(queue_name):
    # print(f"Adding queue {queue_name}")
    # app.control.add_consumer(queue_name, reply=True)
    # print(f"Added queue {queue_name}")
    pass


@shared_task
def delete_queue(queue_name):
    # print(f"deleting queue {queue_name}")
    # app.control.cancel_consumer(queue_name, reply=True)
    # print(f"deleted queue {queue_name}")
    pass
    
if is_running_under_celery():
    import analytics.celery_consumers  #
    from django.apps import apps
    apps.check_apps_ready() 
    for attr_name in dir(analytics.celery_consumers):
        attr = getattr(analytics.celery_consumers, attr_name)
        if (
            inspect.isclass(attr) 
            and issubclass(attr, bootsteps.Step)  # Only Celery steps
            and hasattr(attr, "name")  # Must have a name
        ):
            app.steps["consumer"].add(attr)