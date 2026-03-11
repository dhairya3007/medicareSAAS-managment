from celery import shared_task
import time

@shared_task
def test_task():
    print("Task started")
    time.sleep(5)
    print("Task finished")