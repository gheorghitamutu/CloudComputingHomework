from .db import db


class Task(db.Document):
    title = db.StringField(required=True)
    description = db.StringField(max_length=300, required=True)
    references = db.StringField(max_length=300, required=True)
    done = db.BooleanField(required=True)
