from db.db import BaseModel
from datetime import datetime
import peewee

class User(BaseModel):

    chat_id = peewee.BigIntegerField(index=True, primary_key=True)

    is_admin = peewee.BooleanField(default=False)

    
class ExcelFile(BaseModel):

    id = peewee.IntegerField(primary_key=True, index=True)

    created_at = peewee.DateTimeField(default=datetime.now)

    path = peewee.CharField(max_length=255)



