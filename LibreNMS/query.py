"""
Defines activity-based handlers to interact with the LibreNMS database.
"""

import logging

from LibreNMS.utils import DB
from LibreNMS import config

_db = DB(config.app, auto_connect=False)
logger = logging.getLogger(__name__)


def get_connection(autocommit=None):
    conn = _db.db_conn()
    if autocommit is not None:
        conn.autocommit(autocommit)
    return conn


class Query(object):
    sql = None
    result = False
    many = False

    @classmethod
    def run(cls, *args, **kwargs):
        conn = get_connection()
        with conn.cursor() as cursor:
            cursor.execute(cls.sql, args)
            if not cls.result:
                return
            if not cls.many:
                return cursor.fetchone()
            return cursor.fetchall()


class SelectPollerId(Query):
    sql = """
SELECT `id` FROM `distributed_poller` WHERE 
`cluster_name`=%s AND `node_id`=%s
"""
    result = True


class InsertPollerNode(Query):
    sql = """
INSERT INTO `distributed_poller` (`cluster_name`, `node_id`, `poller_version`, 
                                  `poller_groups`, `last_report`) 
VALUES (%s, %s, %s, %s, '0000-00-00')
"""


class UpdatePollerNode(Query):
    sql = """
UPDATE `distributed_poller` SET `last_report`=NOW() 
WHERE `id`=%s
"""


class SelectPollerStatsId(Query):
    sql = """
SELECT `id` FROM `distributed_poller_stats` 
WHERE `cluster_name`=%s AND `poller_type`=%s
"""
    result = True


class InsertPollerStats(Query):
    sql = """
INSERT INTO `distributed_poller_stats` (`cluster_name`, `poller_type`, `workers`, `frequency`, 
                                        `depth`, `devices`, `worker_seconds`, `last_report`) 
VALUES (%s, %s, %s, %s, %s, %s, %s, '0000-00-00')
"""


class UpdatePollerStats(Query):
    sql = """
UPDATE `distributed_poller_stats` SET `depth`=%s, `devices`=%s, `worker_seconds`=%s, `last_report`=NOW()
WHERE `id`=%s
"""


class SelectDevices(Query):
    sql="""
SELECT `device_id`, `poller_group` FROM `devices` 
WHERE `disabled`=0
"""
    result = True
    many = True


class SelectServiceDevices(Query):
    sql="""
SELECT DISTINCT(`device_id`), `poller_group` FROM `services` 
LEFT JOIN `devices` USING (`device_id`) 
WHERE `disabled`=0
"""
    result = True
    many = True


class SelectNodes(Query):
    sql="""
SELECT DISTINCT(`node_id`) from distributed_poller
"""
    result = True
    many = True
