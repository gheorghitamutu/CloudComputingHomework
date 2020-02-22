import os
import json
import enum
import requests
import sys
import socket
import time
import uuid
import re


class LogLevel(enum.Enum):
    INFO = 'INFO'
    DEBUG = 'DEBUG'
    WARN = 'WARN'
    WARNING = 'WARNING'
    ERROR = 'ERROR'


class LogAPI:
    def __init__(self):
        # config
        module_path = os.path.dirname(__file__)
        config_abs_path = os.path.join(module_path, 'config')

        self.api_config = dict()
        with open(config_abs_path, 'r') as fp_config:
            self.api_config = json.load(fp_config)

        self.api_key = self.api_config['logdna_API_Key']

        self.logdna_api = 'https://logs.logdna.com/logs/ingest'

    def make_request(self, line, level):
        data = \
            {
                'lines':
                    [
                        {
                            'line': str(line),
                            'level': level,
                            'env': "development",
                            'app': 'Homework01'
                        }
                    ]
            }

        response = requests.post(
            url=self.logdna_api,
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

        return response
