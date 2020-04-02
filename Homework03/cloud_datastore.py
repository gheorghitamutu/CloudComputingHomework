from google.cloud import datastore


class Datastore:
    def __init__(self, logger):
        self.client = datastore.Client()
        self.logger = logger

    def insert_user_data(self, data):
        self.logger.debug('Adding new row for email [{}]'.format(data["email"]))
        try:
            with self.client.transaction():
                incomplete_key = self.client.key("users_info")
                task = datastore.Entity(key=incomplete_key)

                task.update({
                    'email': data['email'],
                    'uploaded_file_url': data['uploaded_file_url'],
                    'file_name': data['file_name'],
                    'hash': data['hash']
                })
                self.client.put(task)
            self.logger.debug("Datastore addition was successful")
            return True
        except Exception as e:
            self.logger.exception(e)
            return None

    def get_file_url(self, email, file_name):
        self.logger.debug('Checking if user file already exists')
        try:
            query = self.client.query(kind="users_info")
            query.add_filter("email", '=', email)
            query.add_filter("file_name", '=', file_name)
            entities = [entity for entity in query.fetch()]

            if len(entities) == 0:
                return False

            self.logger.debug('Checking for user file existence was successful')

            return entities[0]["uploaded_file_url"]
        except Exception as e:
            self.logger.exception(e)
            return None
