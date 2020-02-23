import os
import json
import requests
import sys
import socket
import time
import uuid
import re
import logging


class LogAPI(logging.Handler):
    def __init__(self, logger=None):
        super().__init__()

        self.logger = logger
        self.logger.addHandler(self)

        # config
        module_path = os.path.dirname(__file__)
        config_abs_path = os.path.join(module_path, 'config')

        self.api_config = dict()
        with open(config_abs_path, 'r') as fp_config:
            self.api_config = json.load(fp_config)

        self.api_key = self.api_config['logdna_API_Key']
        self.api = 'https://logs.logdna.com/logs/ingest'

    def emit(self, record):
        data = \
            {
                'lines':
                    [
                        {
                            'line': str(record),
                            'level': logging._levelToName[record.levelno],  # explicit level name for logDNA
                            'env': "development",
                            'app': 'Homework01'
                        }
                    ]
            }

        response = requests.post(
            url=self.api,
            json=data,
            auth=('user', self.api_key),
            params={
                'hostname': socket.gethostname(),
                'ip': socket.gethostbyname(socket.gethostname()),
                'now': int(time.time()),
                'mac': ':'.join(re.findall('..', '%012X' % uuid.getnode())),
                'tags': 'Homework01'
            },
            stream=True,
            timeout=5,
            headers={'user-agent': '{}'.format(sys.version)}
        )

        return response  # TODO: can you really check this?
