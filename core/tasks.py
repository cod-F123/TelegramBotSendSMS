from celery import Celery
from decouple import config
import asyncio
import logging

from utils import send_message_to_numbers, add_number_to_excel, send_message_to_telegram



logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
# set higher logging level for httpx to avoid all GET and POST requests being logged
logging.getLogger("httpx").setLevel(logging.WARNING)

logger = logging.getLogger(__name__)


PRIMARY_NUMBERS = config("PRIMARY_NUMBERS", cast=lambda nms: [num.strip() for num in nms.split(",")], default="")


app = Celery(
    "tasks",
    broker=config("CELERY_BROKER_URL"),
    result_backend=config("CELERY_RESULT_BACKEND", default=None), 
)

app.conf.broker_connection_retry_on_startup = True
app.conf.broker_connection_max_retries = 10
app.conf.broker_transport_options = {
    "max_retries": 5,               
    "interval_start": 0,
    "interval_step": 0.2,
    "interval_max": 0.5,
    "socket_keepalive": True,       
    "socket_timeout": 30,           
    "visibility_timeout": 43200,    
}

app.conf.task_acks_late = True              
app.conf.task_reject_on_worker_lost = True  
app.conf.worker_prefetch_multiplier = 1    



@app.task(bind=True, autoretry_for=(Exception,), retry_backoff=True, retry_kwargs={"max_retries": 5})
def send_message_to_sms(self, message, excel_path, chat_id):
    try:
        
        result  = send_message_to_numbers(message, excel_path, PRIMARY_NUMBERS)

    except Exception as exc:
        logger.log(logging.ERROR, f"Error : {exc}")
        raise self.retry(exc=exc)

    text = f"به {result.get('success_fully_count')} با موفقیت ارسال شد\n به {result.get('unsuccess_fully_count')} ارسال نشد"

    try:
        asyncio.run(send_message_to_telegram(text,chat_id=chat_id))

    except Exception as exc:
        logger.exception("Error sending Telegram notification")



@app.task(bind=True, max_retries=5)
def insert_number_to_excel(self, numbers, excel_path, chat_id):

    try:
        result = add_number_to_excel(numbers, excel_path)

    except Exception as exc:
        logger.exception("Error inserting numbers into Excel")
        raise

    text = f"{len(result)} شماره اضافه شد\n" + "\n".join(result)

    try:
        asyncio.run(send_message_to_telegram(text, chat_id))

    except Exception as exc:
        logger.exception("Error sending Telegram notification")
