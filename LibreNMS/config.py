"""
Defines a suitable type to hold poller configuration parameters.
"""

import os, os.path
import subprocess
import logging
import socket
import json

BASE_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
logger = logging.getLogger(__name__)


class BaseConfig(object):
    """
    TBD
    """
    def __init__(self, data=None):
        self._d = {}
        if data is not None:
            self._d.update(data)

    def __getattr__(self, attr):
        if attr in self._d:
            return self._d.get(attr)
        return self.__getattribute__(attr)

    def __str__(self):
        return str(self._d)


class PollerConfig(object):
    """
    TBD
    """
    node_id = socket.gethostname()
    defaults = {
        'poller_workers': 4,
        'poller_interval': 300,
        'service_workers': 2,
        'service_interval': 300,
        'discovery_workers': 2,
        'discovery_interval': 21600,
        'billing_interval': 300,
        'billing_calculate_interval': 86400,
        'alert_interval': 300,
        'daily_interval': 86400,
        'heartbeat_interval': 300,
    }

    def __init__(self, *args, **kwargs):
        for key, val in self.defaults.items():
            env_key = 'LIBRENMS_DISTRIBUTED_{}'.format(key.upper())
            setattr(self, key, int(os.environ.get(env_key, val)))


class AppConfig(BaseConfig):
    """
    TBD
    """
    def __init__(self):
        super().__init__(data=self.load_config())

    def load_config(self):
        config_cmd = ['/usr/bin/env',
                      'php',
                      os.path.join(BASE_PATH, 'config_to_json.php'),
                      '2>&1']

        try:
            payload = subprocess.check_output(config_cmd).decode()
            return json.loads(payload)
        except subprocess.CalledProcessError as e:
            log_msg = "Could not load or parse configuration! {}: {}"
            logger.error(log_msg.format(subprocess.list2cmdline(e.cmd),
                                        e.output.decode()))


poller = PollerConfig()
app = AppConfig()
