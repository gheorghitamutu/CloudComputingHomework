# https://www.virustotal.com
# https://testmail.app
# https://app.scrapinghub.com
# https://logdna.com | https://github.com/logdna/python
# https://httpstatuses.com | status codes explained
# https://github.com/pallets/flask/issues/2998 | logging behaviour explained

import logging
from flask import Flask, request
from flask.logging import default_handler

from .logdna import LogAPI
from .aws_storage import AWS3Storage
from .mail_sender import GmailSender
from .vt_report import VTReport


class App(Flask):
    app_logger = None

    def __init__(self, import_name):
        super().__init__(import_name)
        # self.logger.removeHandler(default_handler)  # customize your log handler to also send messages to API
        self.logger.setLevel(logging.DEBUG)

        App.app_logger = self.logger  # used from static decorators

        formatter = logging.Formatter("%(asctime)s [%(threadName)-12.12s] [%(levelname)-5.5s]  %(message)s")
        fileHandler = logging.FileHandler("{}.log".format(self.__class__.__name__))
        fileHandler.setFormatter(formatter)
        self.logger.addHandler(fileHandler)
        fileHandler.close()

        # logging - DNA
        self.log_api = LogAPI(self.logger)

        #  bind routes callbacks
        self.add_url_rule('/', view_func=self.root_view, methods=['GET', 'POST'])

        # bind request events decorators
        self.before_request(self.log_before_request)
        self.after_request(self.log_after_request)

        # constant str members
        self.hello_message = 'Hello World!'

        # Virus Total hash report
        self.vt_report = VTReport(self.logger)
        # self.vt_report.hash_report('13bc6e477d248677a8f435bef7965fb6')

        # mail sender
        self.mail_sender = GmailSender(self.logger)
        # self.mail_sender.send_email("This is a test email!")

        # AWS3 Storage
        self.storage = AWS3Storage(self.logger)
        # self.storage.upload_to_aws(r'D:\01\test', 'test')

        self.logger.debug('{} initialization finished!'.format(self.__class__.__name__))

    def root_view(self):
        if request.method == 'POST':
            pass
        elif request.method == 'GET':  # TODO: this should actually be POST!
            try:
                b = self.vt_report.hash_report('13bc6e477d248677a8f435bef7965fb6')
                return b
            except Exception as e:
                self.logger.error(e)

        return 'Failure!'

    @staticmethod
    def log_before_request():
        App.app_logger.debug('Headers: {}'.format(request.headers))
        App.app_logger.debug('Body: {}'.format(request.get_data()))

    @staticmethod
    def log_after_request(response):
        App.app_logger.debug('Response: {}'.format(response))
        return response
