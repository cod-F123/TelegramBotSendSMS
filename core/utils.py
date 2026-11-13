from decouple import config 
from telegram import Bot
import requests
import openpyxl
import logging

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



def send_payamak(message : str, number:str) -> dict:

    data = {
        "username" : PAYAMAK_USERNAME,
        "password" : PAYAMAK_PASSWORD,
        "from" : PAYAMAK_FROM,
        "to" : number,
        "text" : message
    }

    response = requests.post(PAYAMAK_URL, data=data)

    return response.json()


def read_excel_get_numbers(excel_path:str) -> list[str]:
    
    numbers = []
    wb = openpyxl.load_workbook(excel_path)
    
    ws = wb.active

    for row in range(0, ws.max_row):
        for col in ws.iter_cols(1, ws.max_column):
            numbers.append(str(col[row].value))

    return numbers


def add_number_wrire_excel(excel_path : str, numbers : list[str]):
    wb = openpyxl.load_workbook(excel_path)
    
    ws = wb.active

    for number in numbers:
        ws.append([number])

    wb.save(excel_path)


def send_message_to_numbers(message :str, excel_path : str, extra_numbers : list[str]) -> dict:

    numbers = read_excel_get_numbers(excel_path)

    success_fully_sended_count = 0

    for number in numbers:

        status_number = send_payamak(message, number)

        if status_number.get("StrRetStatus") == "Ok":
            success_fully_sended_count += 1
    

    for extra_number in extra_numbers:

        status_number = send_payamak(message, extra_number)

        if status_number.get("StrRetStatus") == "Ok":
            success_fully_sended_count += 1


    
    return {
        "success_fully_count" : success_fully_sended_count,
        "unsuccess_fully_count" : len(numbers) + len(extra_numbers) - success_fully_sended_count
    }


def add_number_to_excel(new_numbers: list[str], excel_path) -> list[str]:

    numbers = read_excel_get_numbers(excel_path)

    avable_numbers = list(filter(lambda num : num not in numbers, new_numbers))

    add_number_wrire_excel(excel_path, avable_numbers)

    return avable_numbers


def send_quick_message(numbers: list[str],message: str)->dict:

    success_fully_sended_count = 0
    
    for number in numbers:

        status_number = send_payamak(message, "98s"+number)

        if status_number.get("StrRetStatus") == "Ok":
            success_fully_sended_count += 1
    

    return {
        "success_fully_count" : success_fully_sended_count,
        "unsuccess_fully_count" : len(numbers) - success_fully_sended_count
    }




async def send_message_to_telegram(message, chat_id):

    bot = Bot(token=BOT_TOKEN)
    try:
        await bot.send_message(chat_id,text=message)
    
    except Exception as error:

        logger.log(logging.ERROR, f"Error : {error}")

    finally:
        await bot.close()
