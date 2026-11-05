from celery import Celery
from decouple import config
from telegram import Bot
import logging
import asyncio
import requests
import openpyxl

PAYAMAK_USERNAME = config("USERNAME_PAYAMAK")
PAYAMAK_PASSWORD = config("PASSWORD_PAYAMAK")
PAYAMAK_FROM = config("FROM_PAYAMAK")
PAYAMAK_URL = config("URL_PAYAMAK")

BOT_TOKEN = config("BOT_TOKEN")


logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
# set higher logging level for httpx to avoid all GET and POST requests being logged
logging.getLogger("httpx").setLevel(logging.WARNING)

logger = logging.getLogger(__name__)


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


def send_payamak(message, number):

    data = {
        "username" : PAYAMAK_USERNAME,
        "password" : PAYAMAK_PASSWORD,
        "from" : PAYAMAK_FROM,
        "to" : number,
        "text" : message
    }

    response = requests.post(PAYAMAK_URL, data=data)

    return response.json()


def read_excle_and_send_message(message, excel_path):
    
    wb = openpyxl.load_workbook(excel_path)
    
    ws = wb.active

    sended_successfuly = []

    for row in range(0, ws.max_row):
        for col in ws.iter_cols(1, ws.max_column):
            number = str(int(col[row].value))

            status = send_payamak(message, "98"+number )

            if status.get("StrRetStatus") == "Ok":
                sended_successfuly.append("98" +number)

    return sended_successfuly


async def send_message_to_telegram(message, chat_id):

    bot = Bot(token=BOT_TOKEN)
    try:
        await bot.send_message(chat_id,text=message)
    
    except Exception as error:

        logger.log(logging.ERROR, f"Error : {error}")

    finally:
        await bot.close()




@app.task(bind=True, autoretry_for=(Exception,), retry_backoff=True, retry_kwargs={"max_retries": 5})
def send_message_to_sms(self, message, excel_path, chat_id):
    try:
        
        list_of_sended = read_excle_and_send_message(message, excel_path=excel_path)

        text = "پیام با موفقیت به شماره های زیر ارسال شد\n" + "\n".join(list_of_sended)

        asyncio.run(send_message_to_telegram(text,chat_id=chat_id))


    except Exception as exc:
        logger.log(logging.ERROR, f"Error : {exc}")
        raise self.retry(exc=exc)