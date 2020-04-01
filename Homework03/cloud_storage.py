import json
import os
from google.cloud import storage


class GCloudStorage:
    def __init__(self, logger):
        # config
        module_path = os.path.dirname(__file__)
        config_abs_path = os.path.join(module_path, 'config')

        self.config = dict()
        with open(config_abs_path, 'r') as fp_config:
            self.config = json.load(fp_config)

        self.logger = logger
        self.bucket_name = self.config["BUCKET_NAME"]
        self.storage_client = storage.Client()
        self.bucket = self.storage_client.get_bucket(self.bucket_name)

    def upload_file(self, file_obj, key):
        try:
            blob = self.bucket.blob(key)
            blob.upload_from_string(file_obj.read(), content_type=file_obj.content_type)
            blob.make_public()
            upload_url = "https://storage.cloud.google.com/{}/{}".format(self.bucket_name, key)
            return upload_url
        except Exception as e:
            self.logger.error("Something went wrong")
            return None
