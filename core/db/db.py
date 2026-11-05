from peewee import SqliteDatabase, Model


db = SqliteDatabase("database.db")


class BaseModel(Model):

    class Meta:
        database = db 

