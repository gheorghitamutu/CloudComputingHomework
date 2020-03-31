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


# TODO: add logger!!
class MailSender:
    def __init__(self):
        SCOPE = 'https://www.googleapis.com/auth/gmail.compose'  # Allows sending only, not reading

        # Initialize the object for the Gmail API
        # https://developers.google.com/gmail/api/quickstart/python
        store = file.Storage('credentials.json')
        creds = store.get()
        if not creds or creds.invalid:
            flow = client.flow_from_clientsecrets(
                'client_secret_184366389851-u8b66fhhagsvhrdk4p4atm9023scrra0.apps.googleusercontent.com.json',
                SCOPE)

            args = tools.argparser.parse_args()
            args.auth_host_port = [9000, 9090]  # work around because you're on a flask server with 8080 default!!!
            creds = tools.run_flow(flow, store, args)

        self.service = build('gmail', 'v1', http=creds.authorize(Http()))
        self.user_id = 'me'

    def send_message(self, message):
        """Send an email message.

      Args:
        service: Authorized Gmail API service instance.
        user_id: User's email address. The special value "me"
        can be used to indicate the authenticated user.
        message: Message to be sent.

      Returns:
        Sent Message.
      """
        try:
            message = (self.service.users().messages().send(userId=self.user_id, body=message).execute())

            print('Message Id: %s' % message['id'])
            return message
        except errors.HttpError as error:
            print('An error occurred: %s' % error)
            return False

    def create_message(self, sender, to, subject, message_text):
        """Create a message for an email.

      Args:
        sender: Email address of the sender.
        to: Email address of the receiver.
        subject: The subject of the email message.
        message_text: The text of the email message.

      Returns:
        An object containing a base64url encoded email object.
      """
        message = MIMEText(message_text)
        message['to'] = to
        message['from'] = sender
        message['subject'] = subject
        message_encoded = urlsafe_b64encode(message.as_bytes())
        return {'raw': message_encoded.decode()}

    def create_message_with_attachment(self, sender, to, subject, message_text, file_dir, filename):
        """Create a message for an email.

      Args:
        sender: Email address of the sender.
        to: Email address of the receiver.
        subject: The subject of the email message.
        message_text: The text of the email message.
        file_dir: The directory containing the file to be attached.
        filename: The name of the file to be attached.

      Returns:
        An object containing a base64url encoded email object.
      """
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
            msg = MIMEText(fp.read(), _subtype=sub_type)
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
