import logging
import time

import threadpool as tp
# Imports the Google Cloud client library
from google.cloud import logging as google_logging
from google.cloud.logging import DESCENDING


class LogAPI(logging.Handler):
    def __init__(self, logger, metrics):
        super().__init__()

        self.logger = logger
        self.logger.addHandler(self)

        self.metrics = metrics

        # Instantiates a client
        self.logging_client = google_logging.Client()

        # Selects the log to write to
        self.cloud_logger = self.logging_client.logger(self.__class__.__name__)

        self.threadpool = tp.ThreadPool(4)

    def emit(self, record):
        self.metrics['cloud_logger'] += 1
        self.threadpool.add_task(self.helper_thread, record)

    def helper_thread(self, record):
        start = time.time()

        self.cloud_logger.log_text(record)

        self.metrics['cloud_logger_total_time'] += (time.time() - start)

        return response  # TODO: can you really check this?

    def __del__(self):  # don't bail out before writing/calling API logs
        self.threadpool.wait_completion()

    def get_logs(self):
        logs = dict()
        logs[self.__class__.__name__] = []

        for entry in self.logging_client.list_entries(
                order_by=DESCENDING,
                filter_='resource.type:gae_app and resource.labels.module_id:default'):  # API call
            logs[self.__class__.__name__].append(dict(  # https://googleapis.dev/python/logging/latest/entries.html
                {
                    'log_name': entry.log_name,
                    'labels': entry.labels,
                    'insert_id': entry.insert_id,
                    'severity': entry.severity,
                    'http_request': entry.http_request,
                    'timestamp': entry.timestamp,
                    'resource': entry.resource,
                    'trace': entry.trace,
                    'span_id': entry.span_id,
                    'trace_sampled': entry.trace_sampled,
                    'source_location': entry.source_location,
                    'operation': entry.operation
                }
            ))

        return logs
