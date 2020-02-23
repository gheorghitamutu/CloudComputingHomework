import smtplib
import os
import json


class GmailSender:
    def __init__(self, logger):
        self.logger = logger

        self.subject = '[{}] Your File Download Link'.format(self.__class__.__name__)

        # config
        module_path = os.path.dirname(__file__)
        config_abs_path = os.path.join(module_path, 'config')

        self.api_config = dict()
        with open(config_abs_path, 'r') as fp_config:
            self.api_config = json.load(fp_config)

        self.sender = self.api_config['GMail_Username']
        self.password = self.api_config['GMail_Password']
        self.to = self.api_config['GMail_To']

        self.server = smtplib.SMTP('smtp.gmail.com', 587)
        self.server.ehlo()
        self.server.starttls()
        self.server.login(self.sender, self.password)

    def send_email(self, text):
        email_body = '\r\n'.join(
            ['To: {}'.format(self.to),
             'From: {}'.format(self.sender),
             'Subject: {}'.format(self.subject),
             '',
             text])

        try:
            self.server.sendmail(self.sender, [self.to], email_body)
            self.logger.info('Email sent.')
        except Exception as e:
            self.logger.error('Error sending mail: [{}]'.format(e))

    def __del__(self):
        self.server.quit()
