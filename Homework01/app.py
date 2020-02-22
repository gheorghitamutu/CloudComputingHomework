# https://www.virustotal.com
# https://testmail.app
# https://app.scrapinghub.com
# https://logdna.com | https://github.com/logdna/python
# https://httpstatuses.com | status codes explained

from flask import Flask, request
import json
import os
import requests
from urllib.parse import urljoin
from .logdna import LogAPI, LogLevel


class App(Flask):
    def __init__(self, import_name):
        super().__init__(import_name)

        #  bind routes callbacks
        self.add_url_rule('/', view_func=self.root_handler, methods=['GET', 'POST'])

        # config
        module_path = os.path.dirname(__file__)
        config_abs_path = os.path.join(module_path, 'config')

        self.api_config = dict()
        with open(config_abs_path, 'r') as fp_config:
            self.api_config = json.load(fp_config)

        # constant str members
        self.hello_message = 'Hello World!'

        self.VT_API_v3 = 'https://www.virustotal.com/vtapi/v2/'

        # logging - DNA
        self.logdna = LogAPI()

    def vt_file(self, file_option, scan_option, params):
        file_url = urljoin(self.VT_API_v3, 'file/')
        option_url = ''
        required_params = list()

        if file_option == 'report':
            option_url = urljoin(file_url, 'report')
            required_params = ['apikey', 'resource']
        elif file_option == 'scan':
            option_url = urljoin(file_url, 'scan')
            if scan_option == '':
                pass
            elif scan_option == 'upload_url':
                option_url = urljoin(option_url, 'scan/upload_url')
        elif file_option == 'rescan':
            option_url = urljoin(file_url, 'rescan')
        elif file_option == 'download':
            option_url = urljoin(file_url, 'download')
        elif file_option == 'behaviour':
            option_url = urljoin(file_url, 'behaviour')
        elif file_option == 'network-traffic':
            option_url = urljoin(file_url, 'network-traffic')
        elif file_option == 'feed':
            option_url = urljoin(file_url, 'feed')
        elif file_option == 'clusters':
            option_url = urljoin(file_url, 'clusters')
        elif file_option == 'search':
            option_url = urljoin(file_url, 'search')

        invalid = len(set(params.keys()).intersection(required_params)) != len(required_params)

        if invalid:
            raise 'Invalid params!'

        det_percentage = 0

        response = requests.get(option_url, params=params)

        if response.status_code == 200:
            json_reponse = response.json()

            if json_reponse['response_code'] == 1:  # hash found on VT
                det_percentage = json_reponse['positives'] / json_reponse['total'] * 100

                logdna_response = self.logdna.make_request(
                    dict({
                        'md5': json_reponse['md5'],  # replace this with the actual computed md5
                        'det_percentage': '{0:.2f}%'.format(det_percentage),
                        'VT_call_succeeded': True,
                        'VT_found': True
                    }),
                    LogLevel.DEBUG.value)
            else:
                logdna_response = self.logdna.make_request(
                    dict({
                        'md5': 'placeholder',  # replace this with the actual computed md5
                        'det_percentage': '0%',
                        'VT_call_succeeded': True,
                        'VT_found': False
                    }),
                    LogLevel.WARNING.value)
        else:
            logdna_response = self.logdna.make_request(
                dict({
                    'md5': 'placeholder',  # replace this with the actual computed md5
                    'det_percentage': '0%',
                    'VT_call_succeeded': False,
                    'VT_found': False
                }),
                LogLevel.ERROR.value)

        return json_reponse

    def root_handler(self):
        if request.method == 'POST':
            pass
        elif request.method == 'GET':
            pass

        a = '13bc6e477d248677a8f435bef7965fb6'
        params = {'apikey': self.api_config['VT_API_Key'], 'resource': a}
        b = self.vt_file('report', '', params)
        return b
