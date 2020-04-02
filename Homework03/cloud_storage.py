import hashlib

from google.cloud import storage


class GCloudStorage:
    def __init__(self, logger, cloud_config):
        self.logger = logger
        self.cloud_config = cloud_config
        self.bucket_name = self.cloud_config.config_json["BUCKET_NAME"]
        self.storage_client = storage.Client()
        self.bucket = self.storage_client.get_bucket(self.bucket_name)

    def upload_file(self, content, file_type, key, email):
        file_new_name = hashlib.md5(email.encode("utf8")).hexdigest() + key
        self.logger.debug('Uploading file [{}] to bucket [{}]'.format(key, self.bucket))
        try:
            blob = self.bucket.blob(file_new_name)
            blob.upload_from_string(content, content_type=file_type)
            blob.make_public()
            upload_url = "https://storage.cloud.google.com/{}/{}".format(self.bucket_name, file_new_name)
            self.logger.debug('File [{}] was uploaded successfully to bucke [{}]'.format(key, self.bucket_name))
            return upload_url
        except Exception as e:
            self.logger.exception(e)
            return None


