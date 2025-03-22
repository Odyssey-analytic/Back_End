# app_name/tasks.py

from celery import shared_task

@shared_task
def my_task(arg1, arg2):
    # Your task logic here
    print(f"Task executed with {arg1} and {arg2}")
