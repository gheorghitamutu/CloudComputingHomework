import logging
import os

from flask import Flask, json, request, Response

from Homework02.db import initialize_db
from Homework02.db.models import Task


class App(Flask):
    def __init__(self, import_name):
        super().__init__(import_name)

        self.config['MONGODB_SETTINGS'] = {
            'db': 'Homework02',
            'host': 'localhost',
            'port': 27017
        }

        initialize_db(self)

        self.logger.setLevel(logging.DEBUG)
        formatter = logging.Formatter("%(asctime)s [%(threadName)-12.12s] [%(levelname)-5.5s]  %(message)s")
        fileHandler = logging.FileHandler("{}.log".format(self.__class__.__name__))
        fileHandler.setFormatter(formatter)
        self.logger.addHandler(fileHandler)
        fileHandler.close()

        self.current_directory = os.path.realpath(os.path.dirname(__file__))

        # populate mongodb with dummy data from json file
        with open(os.path.join(self.current_directory, 'default_data.json'), 'r') as dd:
            content = dd.read().strip()
            tasks_json = json.loads(content)
            objects_deleted = Task.objects.delete()
            self.logger.debug('Deleted {} objects from {} collection.'.format(objects_deleted, Task.__name__.lower()))
            for task_json in tasks_json:
                task = Task(**task_json).save()
                assert task.done is True
            self.logger.debug('Inserted {} objects in {} collection.'.format(
                Task.objects.count(), Task.__name__.lower()))

        # api routes
        self.add_url_rule('/api/v1/tasks', view_func=self.tasks, methods=['GET', 'POST', 'PUT', 'PATCH', 'DELETE'])
        self.add_url_rule('/api/v1/tasks/<task_id>', view_func=self.task,
                          methods=['GET', 'POST', 'PUT', 'PATCH', 'DELETE'])

        # error handling
        self.register_error_handler(404, self.not_found)

    def tasks(self):
        self.logger.debug(request.method)

        if request.method == 'GET':
            tasks = Task.objects().to_json()
            return Response(tasks, mimetype="application/json", status=200)
        elif request.method == 'POST':
            body = request.get_json()
            if type(body) is list:
                tasks = [Task(**item) for item in body]
                task_objects = list()
                for task in tasks:
                    task_objects.append(task.save())
                response_json = {'id': [str(to.id) for to in task_objects]}
                return Response(json.dumps(response_json), mimetype='application/json', status=201)
            else:
                task = Task(**body).save()
                return Response(json.dumps({'id': [str(task.id)]}), mimetype='application/json', status=201)
        elif request.method == 'PUT':
            pass  # 405 (Method Not Allowed)
        elif request.method == 'PATCH':
            pass  # 405 (Method Not Allowed)
        elif request.method == 'DELETE':
            pass  # 405 (Method Not Allowed)

        return Response(json.dumps({'error': 'Method Not Allowed'}), mimetype='application/json', status=405)

    def task(self, task_id):
        self.logger.debug(request.method)

        if request.method == 'GET':
            try:
                tasks = Task.objects.get(id=task_id)
                return Response(tasks.to_json(), mimetype='application/json', status=200)
            except Exception as e:
                self.logger.error(e)
                return Response(json.dumps({'error': str(e)}), mimetype='application/json', status=404)
        elif request.method == 'POST':
            body = request.get_json()
            task = Task(**body).save()
            return Response(json.dumps({'id': [str(task.id)]}), mimetype='application/json', status=201)
        elif request.method == 'PUT':
            body = request.get_json()
            try:
                Task.objects.get(id=task_id).update(**body)
                return Response(status=200)
            except Exception as e:
                return Response(json.dumps({'error': str(e)}), mimetype='application/json', status=404)
        elif request.method == 'PATCH':
            body = request.get_json()
            try:
                Task.objects.get(id=task_id).update(**body)
                return Response(status=200)
            except Exception as e:
                return Response(json.dumps({'error': str(e)}), mimetype='application/json', status=404)
        elif request.method == 'DELETE':
            try:
                Task.objects.get(id=task_id).delete()
                return Response(status=200)
            except Exception as e:
                return Response(json.dumps({'error': str(e)}), mimetype='application/json', status=404)

        return Response(json.dumps({'error': 'Method Not Allowed'}), mimetype='application/json', status=405)

    def not_found(self, error):
        self.logger.error(error)
        return Response(json.dumps({'error': 'Not found'}), mimetype='application/json', status=404)
