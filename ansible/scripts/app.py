from celery import Celery

app = Celery(
    'worker',
    broker='redis://mgmtnode:6379/0',
    backend='redis://mgmtnode:6379/1'
)
