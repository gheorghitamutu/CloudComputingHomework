import json
import logging
import os
import time
from urllib.parse import urljoin

import requests


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
        self.file_report_url = urljoin(self.api, 'file/report')
        self.file_scan_url = urljoin(self.api, 'file/scan')

    def hash_report(self, md5, buffer=None):
        response = self.report(md5)

        log_level = logging.DEBUG
        logger_info = \
            {
                'md5': md5,  # replace this with the actual computed md5
                'det_percentage': '{0:.2f}%'.format(0),
                'VT_call_succeeded': False,
                'VT_found': False,
                'detpecentageint': 0
            }

        if response.status_code != 200:
            log_level = logging.ERROR
            self.logger.log(log_level, str(logger_info))
            return logger_info

        logger_info['VT_call_succeeded'] = True
        json_response = response.json()
        if json_response['response_code'] == 1:  # hash found on VT
            logger_info['det_percentage'] = '{0:.2f}%'.format(
                json_response['positives'] / json_response['total'] * 100)
            logger_info['VT_found'] = True
            logger_info['detpecentageint'] = json_response['positives'] / json_response['total'] * 100
            log_level = logging.INFO

            self.logger.log(log_level, str(logger_info))
            return logger_info

        if buffer is not None:
            response = self.scan(md5, buffer)
            if response.status_code == 200:
                json_response = response.json()

                if json_response['response_code'] == 1:  # all good

                    response = self.report(md5)
                    json_response = response.json()

                    # TODO: add timeout?!
                    while json_response['response_code'] == -2:
                        time.sleep(30)
                        response = self.report(md5)
                        json_response = response.json()

                    if json_response['response_code'] == 1:  # hash found on VT
                        logger_info['det_percentage'] = '{0:.2f}%'.format(
                            json_response['positives'] / json_response['total'] * 100)
                        logger_info['VT_found'] = True
                        logger_info['detpecentageint'] = json_response['positives'] / json_response['total'] * 100
                        log_level = logging.INFO

                        self.logger.log(log_level, str(logger_info))
                        return logger_info

        self.logger.log(log_level, str(logger_info))
        return logger_info

    def report(self, md5):
        params = \
            {
                'apikey': self.api_key,
                'resource': md5
            }

        response = requests.get(self.file_report_url, params=params)

        return response

    def scan(self, md5, buffer):
        files = {'file': (md5, buffer)}
        params = {'apikey': self.api_key}
        response = requests.post(self.file_scan_url, files=files, params=params)

        return response
