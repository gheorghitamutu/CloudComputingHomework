import json
import os

import boto3
from botocore.exceptions import NoCredentialsError


class AWS3Storage:
    def __init__(self, logger):
        self.logger = logger

        # config
        module_path = os.path.dirname(__file__)
        config_abs_path = os.path.join(module_path, 'config')

        self.api_config = dict()
        with open(config_abs_path, 'r') as fp_config:
            self.api_config = json.load(fp_config)

        self.ACCESS_KEY = self.api_config['AWS_Access_Key_ID']
        self.SECRET_KEY = self.api_config['AWS_Secret_Access_Key']

        self.s3 = boto3.client('s3', aws_access_key_id=self.ACCESS_KEY, aws_secret_access_key=self.SECRET_KEY)
        self.bucket_name = 'cloudcomputinghomework01'
        self.bucket = boto3.resource(
            's3',
            aws_access_key_id=self.ACCESS_KEY,
            aws_secret_access_key=self.SECRET_KEY).Bucket(self.bucket_name)
        self.bucket_location = self.s3.get_bucket_location(Bucket=self.bucket_name)['LocationConstraint']

    def upload_to_aws(self, file_obj, key):
        try:
            self.s3.upload_fileobj(file_obj, self.bucket_name, key)
            self.logger.info("Upload Successful!")

            file_object = [fo for fo in self.bucket.objects.all() if fo.key == key][0]

            acl_response = file_object.Acl().put(ACL='public-read')
            if acl_response['ResponseMetadata']['HTTPStatusCode'] != 200:
                return None

            upload_url = "https://s3-{}.amazonaws.com/{}/{}".format(self.bucket_location, self.bucket_name, key)
            self.logger.info("Download URL [{}]".format(upload_url))

            return upload_url
        except FileNotFoundError:
            self.logger.error("The file was not found")
            return None
        except NoCredentialsError:
            self.logger.error("Credentials not available")
            return None
