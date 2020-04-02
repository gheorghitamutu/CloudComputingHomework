import hashlib
import logging
import os
import re
import sys
import time

import cloud_config
import cloud_datastore as db
import cloud_gmail as ms
import cloud_logger
import cloud_storage as google_storage
import url_shortener as us
import vt_report as vtr
from flask import Flask, request, render_template, jsonify
from werkzeug.utils import secure_filename


class App(Flask):
    app_logger = None

    def __init__(self, import_name):
        super().__init__(import_name,
                         static_url_path='',
                         static_folder=os.path.join(os.getcwd(), 'web', 'static'),
                         template_folder=os.path.join(os.getcwd(), 'web', 'templates', 'public'))

        self.config['UPLOAD_FOLDER'] = os.path.join(os.getcwd(), 'web', 'uploads')
        self.config['MAX_CONTENT_LENGTH'] = 10 * 1024 * 1024  # 10 MB  -> raises RequestEntityTooLarge exception

        self.logger.setLevel(logging.DEBUG)
        App.app_logger = self.logger

        # metrics
        self.metrics = {
            'VT': 0,
            'VT_total_time': 0,
            'cloud_logger': 0,
            'cloud_logger_total_time': 0,
            'GCloud_Storage': 0,
            'GCloud_Storage_total_time': 0,
            'datastore': 0,
            'datastore_total_time': 0,
            'shortener': 0,
            'shortener_total_time': 0,
            'mail': 0,
            'mail_total_time': 0
        }

        #  bind routes callbacks
        self.add_url_rule('/', view_func=self.index, methods=['GET', 'POST'])
        self.add_url_rule('/shutdown', view_func=self.shutdown, methods=['GET', 'POST'])
        self.add_url_rule('/metrics', view_func=self.metrics_route, methods=['GET'])
        self.add_url_rule('/logs', view_func=self.logs_route, methods=['GET'])

        try:
            # get config and credentials from cloud
            self.cloud_config = cloud_config.CloudConfig(self.logger)

            # logging - google cloud
            self.cloud_logger = cloud_logger.LogAPI(self.logger, self.metrics)

            # bind request events decorators
            self.before_request(self.log_before_request)
            self.after_request(self.log_after_request)

            # Virus Total hash report
            self.vt_report = vtr.VTReport(self.logger, self.cloud_config)

            # mail sender
            self.mail_sender = ms.MailSender(self.logger, self.cloud_config)

            # Google Storage
            self.storage = google_storage.GCloudStorage(self.logger, self.cloud_config)

            # Google DataStore
            self.database = db.Datastore(self.logger)

            # URL shortener
            self.url_shortener = us.URLShortener(self.logger)

        except Exception as e:
            self.logger.exception(e)
            self.logger.debug('{} initialization finished with errors!'.format(self.__class__.__name__))
            sys.exit(1)

        self.logger.debug('{} initialization finished!'.format(self.__class__.__name__))

    def index(self):
        if request.method == 'POST':
            data = {
                'success': False,
                'supported': False,
                'message': 'Failed uploading the file'
            }

            email = str(request.form['email'])
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

            buffer = file.read()  # use this buffer for Cloud Storage upload as well
            md5 = hashlib.md5(buffer).hexdigest()  # low limit so read everything at once
            try:
                # check if file already exists for this email
                self.metrics['datastore'] += 1
                start = time.time()

                # TODO: search if after hash, is more reliable
                # Also, pretty sure it doesn't matter the user, it just needs to be there
                upload_url_shortened = self.database.get_file_url(email, secure_filename(file.filename))

                self.metrics['datastore_total_time'] += (time.time() - start)

                if upload_url_shortened is None:
                    data['message'] = "Database error!"
                    return jsonify(data)

                if upload_url_shortened is False:
                    # virus scan
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

                    if vt_report['detpercentageint'] > min_det_ratio:
                        data['message'] = 'Det percentage higher than {}: [{}%]'.format(
                            min_det_ratio, int(vt_report['detpercentageint']))
                        return jsonify(data)

                    # adding file to storage
                    self.metrics['GCloud_Storage'] += 1
                    start = time.time()

                    upload_url = \
                        self.storage.upload_file(buffer, file.content_type, secure_filename(file.filename), email)

                    if upload_url is None:
                        data['message'] = 'Failed uploading to GCloud_Storage!'
                        return jsonify(data)

                    self.metrics['GCloud_Storage_total_time'] += (time.time() - start)

                    # make url shorter
                    self.metrics['shortener'] += 1
                    start = time.time()

                    upload_url_shortened = self.url_shortener.shorten_url(upload_url)

                    self.metrics['shortener_total_time'] += (time.time() - start)

                    if upload_url_shortened is None:
                        data['message'] = 'Failed shortening the upload URL!'
                        return jsonify(data)

                    # add user data for this file in db
                    self.metrics['datastore'] += 1
                    start = time.time()
                    db_data = {
                        'email': email,
                        'uploaded_file_url': upload_url_shortened,
                        'file_name': secure_filename(file.filename),
                        'hash': md5
                    }

                    if self.database.insert_user_data(db_data) is False:
                        data['message'] = 'Database error!'
                        return jsonify(data)

                    self.metrics['datastore_total_time'] += (time.time() - start)

                data['supported'] = True

                # send email
                self.metrics['mail'] += 1
                start = time.time()

                email_response = self.mail_sender.send_message(
                    'me',
                    email,
                    'Here is your download link!',
                    'Download link: {}'.format(upload_url_shortened))

                self.metrics['mail_total_time'] += (time.time() - start)

                if email_response is False:
                    data['message'] = 'Failed sending the email!'
                    return jsonify(data)

                data['success'] = True
                data['message'] = 'Download link sent on email.'
            except Exception as e:
                self.logger.exception(e)

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
        if type(filename) != str:
            return False

        return '.' in filename and filename.rsplit('.', 1)[1].lower() in \
               ['txt', 'json', 'pdf', 'zip', 'xml', 'png', 'bin', 'jpg', 'zip']

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
