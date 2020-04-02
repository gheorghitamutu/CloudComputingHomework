import datetime
import json
import sys

from google.cloud import storage
from oauth2client import client


class CloudConfig:
    def __init__(self, logger):
        self.logger = logger
        try:
            self.storage_client = storage.Client()
            self.credentials_bucket = self.storage_client.get_bucket('credentials-and-secrets')

            self.config_json = json.loads(self.download_blob_as_string('configs/config'))
            self.mail_credentials_json = json.loads(self.download_blob_as_string('credentials/credentials.json'))

            try:
                self.mail_credentials = self.OAuth2Credentials_from_json(self.mail_credentials_json)
            except Exception as e:
                self.logger.exception(e)
        except Exception as e:
            self.logger.exception(e)
            sys.exit(1)

    def download_blob_as_string(self, path):
        blob = self.credentials_bucket.get_blob(path)
        content = blob.download_as_string()

        return content

    def OAuth2Credentials_from_json(self, data):
        EXPIRY_FORMAT = '%Y-%m-%dT%H:%M:%SZ'

        if (data.get('token_expiry') and
                not isinstance(data['token_expiry'], datetime.datetime)):
            try:
                data['token_expiry'] = datetime.datetime.strptime(
                    data['token_expiry'], EXPIRY_FORMAT)
            except ValueError:
                data['token_expiry'] = None

        return client.OAuth2Credentials(
            data['access_token'],
            data['client_id'],
            data['client_secret'],
            data['refresh_token'],
            data['token_expiry'],
            data['token_uri'],
            data['user_agent'],
            revoke_uri=data.get('revoke_uri', None),
            id_token=data.get('id_token', None),
            id_token_jwt=data.get('id_token_jwt', None),
            token_response=data.get('token_response', None),
            scopes=data.get('scopes', None),
            token_info_uri=data.get('token_info_uri', None))
