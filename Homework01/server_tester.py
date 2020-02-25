import requests
import time
from Homework01.threadpool import ThreadPool


class Tester:
    def __init__(self):
        self.url = 'http://127.0.0.1:5000/'
        self.file_not_found = r'D:\01\test_not_found_on_vt.txt'
        self.file_found = r'D:\01\test_found_on_vt.txt'
        self.file_infected = r'D:\01\test_infected_on_vt.txt'

        self.url_shutdown = '{}shutdown'.format(self.url)

    def make_request_not_found(self):
        files = {
            'upload_file': open(self.file_not_found, 'rb')
        }

        self.make_request(files)

    def make_request_found(self):
        files = {
            'upload_file': open(self.file_infected, 'rb')
        }

        self.make_request(files)

    def make_request_infected(self):
        files = {
            'upload_file': open(self.file_found, 'rb')
        }

        self.make_request(files)

    def make_request(self, files):
        try:
            response = requests.post(self.url, files=files)
            print(response.text)
        except Exception as e:
            print(e)

    def request_server_shutdown(self):
        try:
            response = requests.post(self.url_shutdown)
            print(response.text)
        except Exception as e:
            print(e)


if __name__ == '__main__':
    num_tries = 64

    tester = Tester()
    pool = ThreadPool(12)

    start = time.time()

    for _ in range(num_tries):
        pool.add_task(tester.make_request_not_found)
        pool.add_task(tester.make_request_found)
        pool.add_task(tester.make_request_infected)
    pool.wait_completion()

    end = time.time()

    print(tester.request_server_shutdown())
    print('Delta: {}'.format(end - start))
