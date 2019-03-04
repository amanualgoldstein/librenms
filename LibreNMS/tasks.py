import subprocess
import datetime
import decimal
import logging
import os.path
import time

from celery import chord

from LibreNMS.celery import app
from LibreNMS.utils import RedisLock
from LibreNMS import query, config

TIMESTAMP_FMT = '%Y-%m-%dT%H:%M:%S.%f%z'
logger = logging.getLogger(__name__)


_lm = RedisLock(namespace='librenms.lock',
                host=config.app.redis_host,
                port=config.app.redis_port,
                db=config.app.redis_db,
                password=config.app.redis_pass,
                unix_socket_path=config.app.redis_socket if config.app.redis_socket else None)


class TaskLocked(Exception):
    def __init__(self, obj_type, obj_id):
        self.obj_type = obj_type
        self.obj_id = obj_id

    def __repr__(self):
        _repr = super().__repr__()
        return '{}: {} ({})'.format(_repr, self.obj_type, self.obj_id)


def call_script(script, args=()):
    base_path = os.path.abspath(os.environ['LIBRENMS_PATH'])
    cmd = (os.path.join(base_path, script),) + args
    return subprocess.check_output(cmd,
                                   stderr=subprocess.STDOUT,
                                   close_fds=True)


@app.task
def poll_device(device_id):
    """
    TBD
    """
    lock_name = '{}:{}'.format('poll', device_id)
    if _lm.check_lock(lock_name):
        raise TaskLocked('poll', device_id)

    try:
        _lm.lock(lock_name,
                 config.app.distributed_poller_name,
                 expiration=config.poller.poller_interval)
        logger.info("Polling device '{}'".format(device_id))
        call_script('poller.php', ('-h', str(device_id)))
        return 1
    except subprocess.CalledProcessError as e:
        logger.error("Polling device {} failed! {}".format(device_id, str(e)))
        if e.returncode == 6:
            logger.warning("Device {} is unreachable.".format(device_id))
        return 0
    finally:
        _lm.unlock(lock_name, config.app.distributed_poller_name)


@app.task
def poll_service(device_id):
    """
    TBD
    """
    lock_name = '{}:{}'.format('services', device_id)
    if _lm.check_lock(lock_name):
        raise TaskLocked('services', device_id)

    try:
        _lm.lock(lock_name,
                 config.app.distributed_poller_name,
                 expiration=config.poller.service_interval)
        logger.info("Polling services for device '{}'".format(device_id))
        call_script('check-services.php', ('-h', str(device_id)))
        return 1
    except subprocess.CalledProcessError as e:
        logger.error("Checking services of device {} failed! {}".format(device_id, str(e)))
        if e.returncode == 5:
            logger.warning("Device {} is down.".format(device_id))
        return 0
    finally:
        _lm.unlock(lock_name, config.app.distributed_poller_name)


@app.task
def discover_device(device_id):
    """
    TBD
    """
    lock_name = '{}:{}'.format('discovery', device_id)
    if _lm.check_lock(lock_name):
        raise TaskLocked('discovery', device_id)

    try:
        _lm.lock(lock_name,
                 config.app.distributed_poller_name,
                 expiration=config.poller.discovery_interval)
        logger.info("Discoverying device '{}'".format(device_id))
        call_script('discovery.php', ('-h', str(device_id)))
        return 1
    except subprocess.CalledProcessError as e:
        logger.error("Discovering device {} failed! {}".format(device_id, str(e)))
        if e.returncode == 5:
            logger.warning("Device {} is down.".format(device_id))
        return 0
    finally:
        _lm.unlock(lock_name, config.app.distributed_poller_name)


@app.task
def poll_billing():
    lock_name = 'billing'
    if _lm.check_lock(lock_name):
        raise TaskLocked('billing')

    try:
        _lm.lock(lock_name,
                 config.app.distributed_poller_name,
                 expiration=config.poller.billing_interval)
        logger.info("Polling billing...")
        call_script('poll-billing.php')
    except subprocess.CalledProcessError as e:
        logger.error("Billing failed! {}".format(str(e)))
        raise
    finally:
        _lm.unlock(lock_name, config.app.distributed_poller_name)


@app.task
def calculate_billing():
    lock_name = 'billing-calculate'
    if _lm.check_lock(lock_name):
        raise TaskLocked('billing-calculate')

    try:
        _lm.lock(lock_name,
                 config.app.distributed_poller_name,
                 expiration=config.poller.billing_calculate_interval)
        logger.info("Calculating billing...")
        call_script('billing-calculate.php')
    except subprocess.CalledProcessError as e:
        logger.error("Billing calculation failed! {}".format(str(e)))
        raise
    finally:
        _lm.unlock(lock_name, config.app.distributed_poller_name)


@app.task
def check_alerts():
    lock_name = 'alerts'
    if _lm.check_lock(lock_name):
        raise TaskLocked('alerts')

    try:
        _lm.lock(lock_name,
                 config.app.distributed_poller_name,
                 expiration=config.poller.alert_interval)
        logger.info("Checking alerts...")
        call_script('alerts.php')
    except subprocess.CalledProcessError as e:
        if e.returncode == 1:
            logger.warning("There was an error issuing alerts: {}".format(e.output))
        else:
            raise
    finally:
        _lm.unlock(lock_name, config.app.distributed_poller_name)


@app.task
def run_maintenance():
    lock_name = 'maintenance'
    if _lm.check_lock(lock_name):
        raise TaskLocked('maintenance')

    try:
        _lm.lock(lock_name,
                 config.app.distributed_poller_name,
                 expiration=config.poller.daily_interval)
        logger.info("Running maintenance tasks...")
        output = call_script('daily.sh')
        logger.info("Maintenance tasks complete\n{}".format(output))
    except subprocess.CalledProcessError as e:
        logger.warning("There was an error running maintenance: {}".format(str(e)))
    finally:
        _lm.unlock(lock_name, config.app.distributed_poller_name)


@app.task
def send_heartbeat():
    """
    Orchestrates heartbeat to all known nodes.

    In order to support the Celery Redis backend, we avoid using
    broadcast queues and instead define a node-local queue for all
    participating nodes and use this task in order 
    """
    nodes = query.SelectNodes.run()
    if (config.poller.node_id,) not in nodes:
        nodes += ((config.poller.node_id,),)
    for node in nodes:
        local_queue = 'node_{}'.format(node[0])
        log_node_heartbeat.apply_async(queue=local_queue)


@app.task
def log_node_heartbeat():
    """
    TBD
    """
    select_poller_args = (config.app.distributed_poller_name,
                          config.poller.node_id)
    result = query.SelectPollerId.run(*select_poller_args)
    if result is None:
        query.InsertPollerNode.run(config.app.distributed_poller_name,
                                   config.poller.node_id,
                                   'librenms-distributed-poller',
                                   config.app.distributed_poller_group)
        result = query.SelectPollerId.run(*select_poller_args)

    query.UpdatePollerNode.run(result[0])


@app.task
def log_cluster_stats(results, worker_type, num_targets, running_since):
    """
    TBD
    """
    activity_began_on = datetime.datetime.strptime(running_since, TIMESTAMP_FMT)
    delta = datetime.datetime.now(datetime.timezone.utc) - activity_began_on

    if worker_type not in ['poller', 'services', 'discovery']:
        raise RuntimeError("Worker type '{}' unknown.".format(worker_type))

    if worker_type == 'poller':
        num_workers = config.poller.poller_workers
        poller_interval = config.poller.poller_interval
    elif worker_type == 'services':
        num_workers = config.poller.service_workers
        poller_interval = config.poller.service_interval
    elif worker_type == 'discovery':
        num_workers = config.poller.discovery_workers
        poller_interval = config.poller.discovery_interval

    worker_completed = sum(results)
    worker_pending = num_targets - worker_completed
    worker_seconds = decimal.Decimal(sum([
        delta.days * 86400,
        delta.seconds,
        delta.microseconds / 1000000.
    ]))

    try:
        conn = query.get_connection(autocommit=False)
        conn.begin()

        # get or create distributed_poller_stats row
        select_poller_stats_args = (config.app.distributed_poller_name, worker_type)
        result = query.SelectPollerStatsId.run(*select_poller_stats_args)
        if result is None:
            query.InsertPollerStats.run(config.app.distributed_poller_name, worker_type,
                                        num_workers, poller_interval, 0, 0, 0)
            result = query.SelectPollerStatsId.run(*select_poller_stats_args)

        # update distributed_poller_stats row
        poller_stats_id = result[0]
        logger.info("Logging node performance statistics...")
        query.UpdatePollerStats.run(worker_pending,
                                    worker_completed,
                                    worker_seconds,
                                    poller_stats_id)
        conn.commit()
    except Exception as e:
        import traceback; traceback.print_exc()
        logger.error("Exception in 'log_cluster_stats': {}".format(str(e)))
        conn.rollback()
    finally:
        conn.close()


@app.task
def poll_devices():
    """
    TBD
    """
    devices = query.SelectDevices.run()
    began_on = datetime.datetime.now(datetime.timezone.utc).strftime(TIMESTAMP_FMT)
    chord((poll_device.s(device[0]) for device in devices),
          log_cluster_stats.s('poller', len(devices), began_on))()


@app.task
def poll_services():
    """
    TBD
    """
    devices = query.SelectServiceDevices.run()
    began_on = datetime.datetime.now(datetime.timezone.utc).strftime(TIMESTAMP_FMT)
    chord((poll_service.s(device[0]) for device in devices),
          log_cluster_stats.s('services', len(devices), began_on))()


@app.task
def discover_devices():
    """
    TBD
    """
    devices = query.SelectDevices.run()
    began_on = datetime.datetime.now(datetime.timezone.utc).strftime(TIMESTAMP_FMT)
    chord((discover_device.s(device[0]) for device in devices),
          log_cluster_stats.s('discovery', len(devices), began_on))()
