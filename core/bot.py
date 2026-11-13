from telegram import Update
from telegram.ext import Application, ContextTypes, CommandHandler, MessageHandler, ConversationHandler, filters 
from db.db import db
from db.models import User, ExcelFile
from decouple import config
import logging
from datetime import datetime
import os

from tasks import send_message_to_sms, insert_number_to_excel, send_quick_sms

BOT_TOKEN = config("BOT_TOKEN")

GET_MESSAGE ,GET_EXCELFILE, GET_NUMBERS_FOR_QUICK_SEND, GET_TEXT_FOR_QUICK_SEND, GET_NUMBERS_AND_ADD_TO_EXCEL = range(5)

# Enable logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
# set higher logging level for httpx to avoid all GET and POST requests being logged
logging.getLogger("httpx").setLevel(logging.WARNING)

logger = logging.getLogger(__name__)

async def start(update:Update, context:ContextTypes.DEFAULT_TYPE):

    user = User.get_or_create(chat_id = update.effective_chat.id)[0]

    if not user.is_admin:

        await context.bot.send_message(update.effective_chat.id, "دستور نامعتبر")
        return

    await context.bot.send_message(update.effective_chat.id,"راهنما استفاده :\n/update_numbers : آپدیت لیست شماره ها\n/add_number : اضافه کردن شماره به اکسل\n/send_sms : ارسال پیامک\n/quick_send ارسال سریع\n\nبرای خروج از هر پروسه [/cancel] را ارسال کنید.")
    
    


async def send_sms_handler(update:Update, context:ContextTypes.DEFAULT_TYPE):

    user = User.get_or_create(chat_id = update.effective_chat.id)[0]

    if user.is_admin:

        await update.message.reply_text("متن پیام را ارسال کنید")
        
        return GET_MESSAGE
    
    await context.bot.send_message(update.effective_chat.id, "دستور نامعتبر")
    return ConversationHandler.END


async def get_text_handler(update:Update, context:ContextTypes.DEFAULT_TYPE):

    text = update.message.text

    excel_files = ExcelFile.select().order_by(ExcelFile.created_at.desc())

    if len(excel_files) > 0:

        if not os.path.exists(excel_files[0].path):
            
            await update.message.reply_text("فایل اکسل وجود ندارد لطفا مجدد فایل اکسل را آپلود کنید")

            return ConversationHandler.END

        logger.log(logging.INFO, "Start to send SMS")

        await update.message.reply_text("شروع ارسال")

        send_message_to_sms.delay(message=text, excel_path = excel_files[0].path,chat_id= update.effective_chat.id)

    else:
        await update.message.reply_text("فایل اکسل یافت نشد")

    return ConversationHandler.END




async def update_excelfile_handler(update: Update, context:ContextTypes.DEFAULT_TYPE):

    user = User.get_or_create(chat_id = update.effective_chat.id)[0]

    if user.is_admin:
        await update.message.reply_text("فایل اکسل را آپلود کنید")
        return GET_EXCELFILE
    
    await context.bot.send_message(update.effective_chat.id, "دستور نامعتبر")
    return ConversationHandler.END


async def get_excelfile_handler(update:Update, context:ContextTypes.DEFAULT_TYPE):

    logger.log(logging.INFO, "Start to Update Excel File")

    document = await update.message.document.get_file()

    now = datetime.now()
    path = f"media/excel/{now.year}-{now.month}-{now.day}__{now.hour}-{now.minute}.xlsx"

    try:

        await document.download_to_drive(path)

        ExcelFile.create(path=path)

        await update.message.reply_text("آپدیت انجام شد")
    
    except Exception as e:
        logger.log(logging.ERROR, f"Error : {e}") 

        await update.message.reply_text("خطا در آپدیت")
        
    return ConversationHandler.END



async def add_numbers_to_excelfile_handler(update:Update, context:ContextTypes.DEFAULT_TYPE):

    user = User.get_or_create(chat_id = update.effective_chat.id)[0]

    if not user.is_admin:

        await update.message.reply_text("دستور نامعتبر")

        return ConversationHandler.END
    
    excel_files = ExcelFile.select().order_by(ExcelFile.created_at.desc())

    if len(excel_files) > 0:

        if not os.path.exists(excel_files[0].path):
            
            await update.message.reply_text("فایل اکسل وجود ندارد لطفا مجدد فایل اکسل را آپلود کنید")

            return ConversationHandler.END

        await update.message.reply_text("[اضافه کردن شماره]\n\nبرای اضاف کردن شماره یا شماره هارو ارسال کنید\nبرای ارسال چند شماره آنهارا با  '-' جدا کنید \nبرای مثال  : \n\t9976543210 - 90123456789 - 9110000000")
        return GET_NUMBERS_AND_ADD_TO_EXCEL

    else:
        await update.message.reply_text("فایل اکسلی برای اضافه کردن شماره یافت نشد.\nابتدا فایل اکسل را اپلود کنید\n /update_numbers")
        return ConversationHandler.END
    
    


async def get_numbers_and_add_to_excel_handler(update:Update, context:ContextTypes.DEFAULT_TYPE):
    
    logger.log(logging.INFO, "Start to Add Number or Numbers to last Excel.")

    numbers_text = update.message.text
    numbers = numbers_text.split("-")

    excel_files = ExcelFile.select().order_by(ExcelFile.created_at.desc())

    insert_number_to_excel.delay(numbers, excel_path = excel_files[0].path, chat_id=update.effective_chat.id)


    return ConversationHandler.END


async def send_quick_message_handler(update: Update, context:ContextTypes.DEFAULT_TYPE):

    user = User.get_or_create(chat_id = update.effective_chat.id)[0]

    if not user.is_admin:

        await update.message.reply_text("دستور نامعتبر")

        return ConversationHandler.END 
    
    await update.message.reply_text("[ارسال سریع]\nشماره  یا شماره های مورد نظر را ارسال کنید\nبرای ارسال شماره ها آنهارا با  '-' جدا کنید\nمثال : \n\t9976543210 - 90123456789 - 9110000000")

    return GET_NUMBERS_FOR_QUICK_SEND


async def get_quick_numbers_handler(update:Update, context:ContextTypes.DEFAULT_TYPE):

    numbers_text = update.message.text
    numbers = numbers_text.split("-")

    context.user_data["quick_send_numbers"] = numbers

    await update.message.reply_text("متن پیام را ارسال کنید")
    return GET_TEXT_FOR_QUICK_SEND


async def get_quick_send_text_handler(update:Update, context:ContextTypes.DEFAULT_TYPE):

    numbers = context.user_data.get("quick_send_numbers", [])

    message = update.message.text


    await update.message.reply_text("شروع ارسال")

    send_quick_sms.delay(numbers = numbers, message = message, chat_id= update.effective_chat.id)


    context.user_data.pop("quick_send_numbers",None)

    return ConversationHandler.END
        

async def cancel(update:Update, context:ContextTypes.DEFAULT_TYPE):

    await update.message.reply_text("پروسه توسط شما کنسل شد")

    return ConversationHandler.END


def main():

    try:

        db.connect()
        db.create_tables([User, ExcelFile])

        app = Application.builder().token(BOT_TOKEN).build()
        

        app.add_handler(CommandHandler(["start", "help"], start))

        app.add_handler(ConversationHandler(
            [CommandHandler(["update_numbers"], update_excelfile_handler), CommandHandler("send_sms", send_sms_handler), CommandHandler(["add_number"], add_numbers_to_excelfile_handler), CommandHandler(["quick_send"], send_quick_message_handler)],
            states= {
                GET_MESSAGE : [MessageHandler(filters.TEXT  & ~filters.COMMAND, get_text_handler)],
                GET_EXCELFILE : [MessageHandler(filters.Document.ALL, get_excelfile_handler)],
                GET_NUMBERS_AND_ADD_TO_EXCEL : [MessageHandler(filters.TEXT & ~filters.COMMAND, get_numbers_and_add_to_excel_handler)],
                GET_NUMBERS_FOR_QUICK_SEND : [MessageHandler(filters.TEXT & ~filters.COMMAND, get_quick_numbers_handler)],
                GET_TEXT_FOR_QUICK_SEND : [MessageHandler(filters.TEXT & ~filters.COMMAND, get_quick_send_text_handler)]
            },
            fallbacks=[CommandHandler("cancel", cancel)]
        ))

        app.run_polling()

    except Exception as e:

        logger.log(logging.WARNING, f"Error : {e}")
        
    finally:
        db.close()


if __name__ == "__main__":
    main()
