import mimetypes
import os
from base64 import urlsafe_b64encode
from email.mime.audio import MIMEAudio
from email.mime.base import MIMEBase
from email.mime.image import MIMEImage
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from apiclient import errors
from apiclient.discovery import build
from httplib2 import Http
from oauth2client import file, client, tools


class MailSender:
    def __init__(self, logger):
        self.logger = logger
        self.user_id = 'me'
        self.scope = 'https://www.googleapis.com/auth/gmail.compose'
        self.storage = file.Storage('credentials.json')

        credentials = self.storage.get()
        if not credentials or credentials.invalid:
            flow = client.flow_from_clientsecrets(
                'client_secret_184366389851-u8b66fhhagsvhrdk4p4atm9023scrra0.apps.googleusercontent.com.json',
                self.scope)

            args = tools.argparser.parse_args()
            args.auth_host_port = [9000, 9090]  # work around because you're on a flask server with 8080 default!!!
            credentials = tools.run_flow(flow, self.storage, args)

        self.service = build('gmail', 'v1', http=credentials.authorize(Http()))

    def send_message(self, sender, to, subject, message_text):
        message = MailSender.create_message(sender, to, subject, message_text)

        self.logger.debug('Sending message [{}]'.format(message))
        try:
            response = (self.service.users().messages().send(userId=self.user_id, body=message).execute())
            self.logger.debug('Message sent: [{}]'.format(response))
            return response
        except errors.HttpError as error:
            self.logger.error('Error sending the email: [{}]'.format(str(error)))
            return None

    @staticmethod
    def create_message(sender, to, subject, message_text):
        message = MIMEText(message_text)
        message['to'] = to
        message['from'] = sender
        message['subject'] = subject
        message_encoded = urlsafe_b64encode(message.as_bytes())
        return {'raw': message_encoded.decode()}

    @staticmethod
    def create_message_with_attachment(sender, to, subject, message_text, file_dir, filename):
        message = MIMEMultipart()
        message['to'] = to
        message['from'] = sender
        message['subject'] = subject

        msg = MIMEText(message_text)
        message.attach(msg)

        path = os.path.join(file_dir, filename)
        content_type, encoding = mimetypes.guess_type(path)

        if content_type is None or encoding is not None:
            content_type = 'application/octet-stream'

        main_type, sub_type = content_type.split('/', 1)
        if main_type == 'text':
            fp = open(path, 'rb')
            msg = MIMEText(fp.read().decode(), _subtype=sub_type)
            fp.close()
        elif main_type == 'image':
            fp = open(path, 'rb')
            msg = MIMEImage(fp.read(), _subtype=sub_type)
            fp.close()
        elif main_type == 'audio':
            fp = open(path, 'rb')
            msg = MIMEAudio(fp.read(), _subtype=sub_type)
            fp.close()
        else:
            fp = open(path, 'rb')
            msg = MIMEBase(main_type, sub_type)
            msg.set_payload(fp.read())
            fp.close()

        msg.add_header('Content-Disposition', 'attachment', filename=filename)
        message.attach(msg)

        return {'raw': base64.urlsafe_b64encode(message.as_string())}

