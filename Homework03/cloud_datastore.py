from google.cloud import datastore


class Datastore:
    def __init__(self, logger):
        self.client = datastore.Client()

    def insert_user_data(self, data):
        with self.client.transaction():
            incomplete_key = self.client.key("users_info")

            task = datastore.Entity(key=incomplete_key)

            task.update({
                'email': data['email'],
                'uploaded_file_url': data['uploaded_file_url']
            })

            self.client.put(task)
