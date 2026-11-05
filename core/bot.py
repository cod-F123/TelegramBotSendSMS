from telegram import Update
from telegram.ext import Application, ContextTypes, CommandHandler, MessageHandler, ConversationHandler, filters 
from db.db import db
from db.models import User, ExcelFile
from decouple import config
import logging
from datetime import datetime

from tasks import send_message_to_sms

BOT_TOKEN = config("BOT_TOKEN")

GET_MESSAGE = 0
GET_EXCELFILE = 1

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

    await context.bot.send_message(update.effective_chat.id,"راهنما استفاده :\n/update_numbers : آپدیت لیست شماره ها\n/send_sms : ارسال پیامک")
    
    


async def send_sms_handler(update:Update, context:ContextTypes.DEFAULT_TYPE):

    user = User.get_or_create(chat_id = update.effective_chat.id)[0]

    if user.is_admin:

        await update.message.reply_text("متن پیام را ارسال کنید")
        
        return GET_MESSAGE
    
    await context.bot.send_message(update.effective_chat.id, "دستور نامعتبر")
    return ConversationHandler.END


async def get_text_handler(update:Update, context:ContextTypes.DEFAULT_TYPE):

    text = update.message.text

    logger.log(logging.INFO, "Start to send SMS")

    excel_files = ExcelFile.select().order_by(ExcelFile.created_at.desc())

    if len(excel_files) > 0:
        await update.message.reply_text("شروع ارسال")

        send_message_to_sms.delay(message=text, excel_path = excel_files[0].path,chat_id= update.effective_chat.id)

    else:
        await update.message.reply_text("فایل اکسل یافت نشد")

    return ConversationHandler.END




async def update_numbers_handler(update: Update, context:ContextTypes.DEFAULT_TYPE):

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


async def cancel(update:Update, context:ContextTypes.DEFAULT_TYPE):

    return ConversationHandler.END

def main():

    try:

        db.connect()
        db.create_tables([User, ExcelFile])

        app = Application.builder().token(BOT_TOKEN).build()
        

        app.add_handler(CommandHandler(["start", "help"], start))

        app.add_handler(ConversationHandler(
            [CommandHandler(["update_numbers"], update_numbers_handler), CommandHandler("send_sms", send_sms_handler)],
            states= {
                GET_MESSAGE : [MessageHandler(filters.TEXT  & ~filters.COMMAND, get_text_handler)],
                GET_EXCELFILE : [MessageHandler(filters.Document.ALL, get_excelfile_handler)]
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
