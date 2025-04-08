import os, sys, django
from celery import Celery, bootsteps
import inspect

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'backend.settings')
django.setup()

app = Celery('celery')

app.config_from_object('django.conf:settings', namespace='CELERY')

def is_running_under_celery():
    return 'celery' in sys.argv[0] or any('celery' in arg for arg in sys.argv)

def is_running_under_uvicorn():
    return 'uvicorn' in sys.argv[0] or any('uvicorn' in arg for arg in sys.argv)


app.autodiscover_tasks()


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

@app.task(bind=True, ignore_result=True)
def debug_task(self):
    print(f'Request: {self.request!r}')
