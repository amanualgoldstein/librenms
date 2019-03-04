"""
Application definition of the distributed LibreNMS poller.
"""
import os

from celery.schedules import crontab
from celery import Celery

from LibreNMS import config


def get_interval(seconds):
    kwargs = {}

    if seconds < 3600:
        kwargs = {'minute': '*/{}'.format(seconds / 60)}
    elif seconds >= 3600 and seconds < 86400:
        kwargs = {'hour': '*/{}'.format(seconds / 3600),
                  'minute': seconds % 3600}
    elif seconds == 86400:
        kwargs = {'hour': 0, 'minute': 0}
    else:
        raise RuntimeError("Intervals greater than 24h are not supported")

    return kwargs


def get_expiry(seconds):
    return seconds - 5


app = Celery('LibreNMS')
app.conf.timezone = os.environ['TZ']
app.conf.broker_url = 'redis://{}:{}/{}'.format(config.app.redis_host,
                                                config.app.redis_port,
                                                config.app.redis_db)
app.conf.result_backend = 'redis://{}:{}/{}'.format(config.app.redis_host,
                                                    config.app.redis_port,
                                                    config.app.redis_result_db)
app.conf.worker_prefetch_multiplier = 1
app.conf.task_routes = {
    'LibreNMS.tasks.log_cluster_stats': 'stats',
    'LibreNMS.tasks.poll_device': 'poller',
    'LibreNMS.tasks.poll_service': 'services',
    'LibreNMS.tasks.discover_device': 'discovery',
}
app.conf.beat_schedule = {
    'hearbeat.update': {
        'task': 'LibreNMS.tasks.send_heartbeat',
        'schedule': crontab(**get_interval(config.poller.heartbeat_interval)),
        'options': {'queue': 'stats',
                    'expires': get_expiry(config.poller.heartbeat_interval)}
    },
    'poller.update': {
        'task': 'LibreNMS.tasks.poll_devices',
        'schedule': crontab(**get_interval(config.poller.poller_interval)),
        'options': {'queue': 'poller',
                    'expires': get_expiry(config.poller.poller_interval)}
    },
    'services.update': {
        'task': 'LibreNMS.tasks.poll_services',
        'schedule': crontab(**get_interval(config.poller.service_interval)),
        'options': {'queue': 'services',
                    'expires': get_expiry(config.poller.service_interval)}
    },
    'discovery.update': {
        'task': 'LibreNMS.tasks.discover_devices',
        'schedule': crontab(**get_interval(config.poller.discovery_interval)),
        'options': {'queue': 'discovery',
                    'expires': get_expiry(config.poller.discovery_interval)}
    },
    'billing.update': {
        'task': 'LibreNMS.tasks.poll_billing',
        'schedule': crontab(**get_interval(config.poller.billing_interval)),
        'options': {'queue': 'billing',
                    'expires': get_expiry(config.poller.billing_interval)}
    },
    'calculate_billing.update': {
        'task': 'LibreNMS.tasks.calculate_billing',
        'schedule': crontab(**get_interval(config.poller.billing_calculate_interval)),
        'options': {'queue': 'billing',
                    'expires': get_expiry(config.poller.billing_calculate_interval)}
    },
    'alerts.update': {
        'task': 'LibreNMS.tasks.check_alerts',
        'schedule': crontab(**get_interval(config.poller.alert_interval)),
        'options': {'queue': 'alerts',
                    'expires': get_expiry(config.poller.alert_interval)}
    },
    'daily.update': {
        'task': 'LibreNMS.tasks.run_maintenance',
        'schedule': crontab(**get_interval(config.poller.daily_interval)),
        'options': {'queue': 'daily',
                    'expires': get_expiry(config.poller.daily_interval)}
    }
}
