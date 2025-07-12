from celery import Celery
from dotenv import load_dotenv
from backendcode.data_models import EnvironmentVariablesConfig

# Configuration for Celery

config = EnvironmentVariablesConfig()
origin_address = config.origin_address
redis_address = config.redis_address
redis_port = config.redis_port

celery_app = Celery(
    "app",
    broker=f"redis://{redis_address}:{redis_port}/0",  # Redis as broker
    backend=f"redis://{redis_address}:{redis_port}/0",  # Redis as backend
    include=["backendcode.tasks"]  # Import tasks automatically
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_expires=3600,  # Task results expire after 1 hour
)
