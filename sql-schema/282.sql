-- CREATE TABLE `distributed_poller` (
--   `id` int(11) NOT NULL AUTO_INCREMENT,
--   `cluster_name` varchar(255) NOT NULL,
--   `node_id` varchar(255) NOT NULL,
--   `poller_version` varchar(255) NOT NULL DEFAULT '',
--   `poller_groups` varchar(255) NOT NULL DEFAULT '',
--   `last_report` datetime NOT NULL,
--   UNIQUE KEY (`cluster_name`, `node_id`),
--   PRIMARY KEY `id` (`id`)
-- );

CREATE TABLE `distributed_poller_stats` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `cluster_name` varchar(255) NOT NULL,
  `poller_type` varchar(64) NOT NULL,
  `workers` int(11) unsigned NOT NULL DEFAULT 0,
  `frequency` int(11) unsigned NOT NULL DEFAULT 0,
  `depth` int(11) unsigned  NOT NULL DEFAULT 0,
  `devices` int(11) unsigned NOT NULL DEFAULT 0,
  `worker_seconds` decimal(5,2) unsigned NOT NULL DEFAULT 0.0,
  `last_report` datetime NOT NULL,
  UNIQUE KEY (`cluster_name`, `poller_type`),
  PRIMARY KEY `id` (`id`)
);
