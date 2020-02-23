import os
import json
from urllib.parse import urljoin
import requests
import logging


class VTReport:
    def __init__(self, logger):
        self.logger = logger

        # config
        module_path = os.path.dirname(__file__)
        config_abs_path = os.path.join(module_path, 'config')

        self.api_config = dict()
        with open(config_abs_path, 'r') as fp_config:
            self.api_config = json.load(fp_config)

        self.api = 'https://www.virustotal.com/vtapi/v2/'
        self.api_key = self.api_config['VT_API_Key']

    def hash_report(self, md5):
        params = \
            {
                'apikey': self.api_key,
                'resource': md5
            }

        file_scan_url = urljoin(self.api, 'file/report')

        json_response = dict()
        log_level = None

        logger_info = \
            {
                'md5': md5,  # replace this with the actual computed md5
                'det_percentage': '{0:.2f}%'.format(0),
                'VT_call_succeeded': False,
                'VT_found': False
            }

        response = requests.get(file_scan_url, params=params)

        if response.status_code == 200:
            json_response = response.json()

            if json_response['response_code'] == 1:  # hash found on VT
                logger_info['det_percentage'] = '{0:.2f}%'.format(
                    json_response['positives'] / json_response['total'] * 100)

                logger_info['VT_call_succeeded'] = True
                logger_info['VT_found'] = True

                log_level = logging.INFO
            else:
                logger_info['VT_call_succeeded'] = True

                log_level = logging.WARNING
        else:
            log_level = logging.ERROR

        self.logger.log(log_level, str(logger_info))

        return json_response
