# https://www.virustotal.com
# https://testmail.app
# https://app.scrapinghub.com
# https://logdna.com | https://github.com/logdna/python
# https://httpstatuses.com | status codes explained
# https://github.com/pallets/flask/issues/2998 | logging behaviour explained

import logging
import os
import hashlib
from flask import Flask, request, render_template, jsonify
from werkzeug.utils import secure_filename

from .logdna import LogAPI
from .aws_storage import AWS3Storage
from .mail_sender import GmailSender
from .vt_report import VTReport
from .url_shortener import URLShortener


class App(Flask):
    app_logger = None

    def __init__(self, import_name):
        super().__init__(import_name,
                         static_url_path='',
                         static_folder=os.path.join('Homework01', 'web', 'static'),
                         template_folder=os.path.join('Homework01', 'web', 'templates', 'public'))

        self.config['UPLOAD_FOLDER'] = os.path.join('Homework01', 'web', 'uploads')
        self.config['MAX_CONTENT_LENGTH'] = 0.2 * 1024 * 1024  # 0.2 MB  -> raises RequestEntityTooLarge exception

        self.logger.setLevel(logging.DEBUG)
        App.app_logger = self.logger  # used from static decorators

        formatter = logging.Formatter("%(asctime)s [%(threadName)-12.12s] [%(levelname)-5.5s]  %(message)s")
        fileHandler = logging.FileHandler("{}.log".format(self.__class__.__name__))
        fileHandler.setFormatter(formatter)
        self.logger.addHandler(fileHandler)
        fileHandler.close()

        # metrics
        self.metrics = {
            'VT': 0,
            'logDNA': 0,
            'AWS': 0,
            'shortener': 0,
            'mail': 0
        }

        # logging - DNA
        self.log_api = LogAPI(self.logger, self.metrics)

        #  bind routes callbacks
        self.add_url_rule('/', view_func=self.index, methods=['GET', 'POST'])
        self.add_url_rule('/shutdown', view_func=self.shutdown, methods=['GET', 'POST'])

        # bind request events decorators
        self.before_request(self.log_before_request)
        self.after_request(self.log_after_request)

        # Virus Total hash report
        self.vt_report = VTReport(self.logger)
        # self.vt_report.hash_report('13bc6e477d248677a8f435bef7965fb6')

        # mail sender
        self.mail_sender = GmailSender(self.logger)
        # self.mail_sender.send_email("This is a test email!")

        # AWS3 Storage
        self.storage = AWS3Storage(self.logger)
        # self.storage.upload_to_aws(r'D:\01\test', 'test')

        # URL shortener
        self.url_shortener = URLShortener(self.logger)
        # self.url_shortener.shorten_url('https://www.google.com')

        self.logger.debug('{} initialization finished!'.format(self.__class__.__name__))

    def index(self):
        if request.method == 'POST':
            data = \
                {
                    'success': False,
                    'supported': False,
                    'message': 'Default message.'
                }

            file = request.files['upload_file']

            # if the user does not select a file, browser also submits an empty part without filename
            if file.filename == '':
                data['message'] = 'No selected file!'
            elif file and self.allowed_file(file.filename):
                buffer = file.read()  # use this buffer for AWS upload as well
                md5 = hashlib.md5(buffer).hexdigest()  # low limit so read everything at once

                try:
                    self.metrics['VT'] += 1
                    vt_report = self.vt_report.hash_report(md5)

                    if vt_report['VT_call_succeeded'] is False:
                        data['message'] = 'Failed querying VT!'
                    else:
                        data['supported'] = True

                        if vt_report['VT_found'] is True:
                            min_det_ratio = 10
                            if vt_report['detpecentageint'] < min_det_ratio:
                                self.metrics['AWS'] += 1
                                upload_url = self.storage.upload_to_aws(file, secure_filename(file.filename))
                                if upload_url is not None:

                                    self.metrics['shortener'] += 1
                                    upload_url_shortened = self.url_shortener.shorten_url(upload_url)
                                    if upload_url_shortened is not None:
                                        self.metrics['mail'] += 1
                                        if self.mail_sender.send_email('Download link: {}'.format(
                                                upload_url_shortened)) is True:

                                            data['success'] = True
                                            data['message'] = 'Download link sent on email'
                                        else:
                                            data['message'] = 'Failed shortening the upload URL!'
                                    else:
                                        pass
                                else:
                                    data['message'] = 'Failed uploading to AWS!'
                            else:
                                data['message'] = 'Det percentage higher than {}: [{}%]'.format(
                                    min_det_ratio,
                                    int(vt_report['detpecentageint']))
                        else:
                            data['message'] = 'Unable to find any info on VT!'

                except Exception as e:
                    self.logger.error(e)
            else:
                data['message'] = 'File type not allowed!'

            return jsonify(data)
        elif request.method == 'GET':
            return render_template('upload.html')

        return 'Failure!'

    @staticmethod
    def log_before_request():
        App.app_logger.debug('Headers: {}'.format(request.headers))
        App.app_logger.debug('Body: {}'.format(request.get_data()))

    @staticmethod
    def log_after_request(response):
        App.app_logger.debug('Response: {}'.format(response))
        return response

    @staticmethod
    def allowed_file(filename):
        return '.' in filename and filename.rsplit('.', 1)[1].lower() in ['txt', 'json', 'pdf', 'zip', 'xml']

    def shutdown_server(self):
        func = request.environ.get('werkzeug.server.shutdown')
        if func is None:
            raise RuntimeError('Not running with the Werkzeug Server')
        func()

    def shutdown(self):
        self.logger.info(str(self.metrics))
        self.log_api.threadpool.wait_completion()
        self.shutdown_server()
        return 'Server shutting down...<br>{}'.format(str(self.metrics))
