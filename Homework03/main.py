# https://www.virustotal.com
# https://testmail.app
# https://app.scrapinghub.com
# https://cloud.google.com/logging/docs/reference/libraries#client-libraries-install-python
# https://httpstatuses.com | status codes explained
# https://github.com/pallets/flask/issues/2998 | logging behaviour explained

import hashlib
import logging
import os
import re
import time

import cloud_gmail as ms
import cloud_logger
import url_shortener as us
import vt_report as vtr
from flask import Flask, request, render_template, jsonify


class App(Flask):
    app_logger = None

    def __init__(self, import_name):
        super().__init__(import_name,
                         static_url_path='',
                         static_folder=os.path.join(os.getcwd(), 'web', 'static'),
                         template_folder=os.path.join(os.getcwd(), 'web', 'templates', 'public'))

        self.config['UPLOAD_FOLDER'] = os.path.join(os.getcwd(), 'web', 'uploads')
        self.config['MAX_CONTENT_LENGTH'] = 2 * 1024 * 1024  # 2 MB  -> raises RequestEntityTooLarge exception

        self.logger.setLevel(logging.DEBUG)
        App.app_logger = self.logger  # used from static decorators

        formatter = logging.Formatter("%(asctime)s [%(threadName)-12.12s] [%(levelname)-5.5s]  %(message)s")
        # fileHandler = logging.FileHandler("{}.log".format(self.__class__.__name__))
        # fileHandler.setFormatter(formatter)
        # self.logger.addHandler(fileHandler)
        # fileHandler.close()

        # metrics
        self.metrics = {
            'VT': 0,
            'VT_total_time': 0,
            'cloud_logger': 0,
            'cloud_logger_total_time': 0,
            'AWS': 0,
            'AWS_total_time': 0,
            'shortener': 0,
            'shortener_total_time': 0,
            'mail': 0,
            'mail_total_time': 0
        }

        # logging - google cloud
        self.cloud_logger = cloud_logger.LogAPI(self.logger, self.metrics)

        #  bind routes callbacks
        self.add_url_rule('/', view_func=self.index, methods=['GET', 'POST'])
        self.add_url_rule('/shutdown', view_func=self.shutdown, methods=['GET', 'POST'])
        self.add_url_rule('/metrics', view_func=self.metrics_route, methods=['GET'])
        self.add_url_rule('/logs', view_func=self.logs_route, methods=['GET'])

        # bind request events decorators
        self.before_request(self.log_before_request)
        self.after_request(self.log_after_request)

        try:
            # Virus Total hash report
            self.vt_report = vtr.VTReport(self.logger)
            # self.vt_report.hash_report('13bc6e477d248677a8f435bef7965fb6')

            # mail sender
            self.mail_sender = ms.MailSender(self.logger)
            # email = self.mail_sender.create_message('me', 'gheorghitamutu@gmail.com', 'Test mail!', 'Test mail!')
            # message = self.mail_sender.send_message(email)

            # AWS3 Storage
            # self.storage = AWS3Storage(self.logger)
            # self.storage.upload_to_aws(r'D:\01\test', 'test')

            # URL shortener
            self.url_shortener = us.URLShortener(self.logger)
            # self.url_shortener.shorten_url('https://www.google.com')
        except Exception as e:
            print(e)

        self.logger.debug('{} initialization finished!'.format(self.__class__.__name__))

    def index(self):
        if request.method == 'POST':
            data = \
                {
                    'success': False,
                    'supported': False,
                    'message': 'Failed uploading the file'
                }

            email = request.form['email']
            if self.is_email_address_valid(email) is not True:
                data['error'] = 'Invalid email address!'
                return jsonify(data)

            file = request.files['upload_file']

            # if the user does not select a file, browser also submits an empty part without filename
            if file.filename == '':
                data['message'] = 'No selected file!'
                return jsonify(data)

            if not file or not self.allowed_file(file.filename):
                data['message'] = 'File type not allowed!'
                return jsonify(data)

            buffer = file.read()  # use this buffer for AWS upload as well
            md5 = hashlib.md5(buffer).hexdigest()  # low limit so read everything at once
            try:
                self.metrics['VT'] += 1
                start = time.time()

                vt_report = self.vt_report.hash_report(md5, buffer)

                self.metrics['VT_total_time'] += (time.time() - start)

                if vt_report['VT_call_succeeded'] is False:
                    data['message'] = 'Failed querying VT!'
                    return jsonify(data)

                data['supported'] = True

                if vt_report['VT_found'] is False:
                    data['message'] = 'Unable to find any info on VT!'
                    return jsonify(data)

                min_det_ratio = 10

                if vt_report['detpecentageint'] > min_det_ratio:
                    data['message'] = 'Det percentage higher than {}: [{}%]'.format(
                        min_det_ratio, int(vt_report['detpecentageint']))
                    return jsonify(data)

                self.metrics['AWS'] += 1
                start = time.time()

                # upload_url = self.storage.upload_to_aws(file, secure_filename(file.filename))
                upload_url = 'http://dummy.deleteme.com/TODO'

                self.metrics['AWS_total_time'] += (time.time() - start)

                if upload_url is None:
                    data['message'] = 'Failed uploading to AWS!'
                    return jsonify(data)

                self.metrics['shortener'] += 1
                start = time.time()

                upload_url_shortened = self.url_shortener.shorten_url(upload_url)

                self.metrics['shortener_total_time'] += (time.time() - start)

                if upload_url_shortened is None:
                    data['message'] = 'Failed shortening the upload URL!'
                    return jsonify(data)

                self.metrics['mail'] += 1
                start = time.time()

                email_id = self.mail_sender.send_message(
                    'me',
                    email,
                    'Here is your download link!',
                    'Download link: {}'.format(upload_url_shortened))

                self.metrics['mail_total_time'] += (time.time() - start)

                if email_id is not False:
                    data['success'] = True
                    data['message'] = 'Download link sent on email'
                else:
                    data['message'] = 'Failed sending the email!'
            except Exception as e:
                self.logger.error(e)

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

    def metrics_route(self):
        return self.metrics

    def logs_route(self):
        return self.cloud_logger.get_logs()

    @staticmethod
    def is_email_address_valid(email):
        if not re.match("^[a-zA-Z0-9.!#$%&'*+/=?^_`{|}~-]+@[a-zA-Z0-9-]+(?:\.[a-zA-Z0-9-]+)*$", email):
            return False
        return True


app = App(__name__)  # fixing gunicorn app finder

if __name__ == '__main__':
    app.run(host='127.0.0.1', port=8080, debug=True)
