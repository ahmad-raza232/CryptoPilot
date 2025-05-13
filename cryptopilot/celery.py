import os
from celery import Celery
from celery.schedules import crontab

# Set the default Django settings module
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'cryptopilot.settings')

# Create the Celery app
app = Celery('cryptopilot')

# Load task modules from all registered Django app configs
app.config_from_object('django.conf:settings', namespace='CELERY')

# Auto-discover tasks in all installed apps
app.autodiscover_tasks()

# Configure periodic tasks
app.conf.beat_schedule = {
    'run-trading-bot': {
        'task': 'trading.tasks.run_trading_bot',
        'schedule': 60.0,  # Run every minute
    },
    'send-daily-summary': {
        'task': 'trading.tasks.send_daily_summary',
        'schedule': crontab(hour=0, minute=0),  # Run at midnight
    },
} 