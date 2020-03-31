import requests


class URLShortener:
    def __init__(self, logger):
        self.logger = logger

        self.api_01 = 'https://cleanuri.com/api/v1/shorten'
        self.api_02 = 'https://rel.ink/api/links/'

    def shorten_url(self, url):
        data = {
            'url': url
        }

        response = requests.post(self.api_01, data=data)

        if response.status_code == 200:
            self.logger.info(response.json())
            return response.json()['result_url']

        self.logger.error(response.json())
        response = requests.post(self.api_02, json=data)

        if response.status_code == 201:
            self.logger.info(response.json())
            return 'https://rel.ink/'.format(response['hashid'])

        self.logger.error(response.json())

        return None
