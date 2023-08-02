import os
from dotenv import load_dotenv
from telegram.ext import Updater
from handlers import detect

dotenv_path = os.path.join(os.path.dirname(__file__), '.env')
if os.path.exists(dotenv_path):
    load_dotenv(dotenv_path)

token = os.environ['BOT_TOKEN']

if __name__ == '__main__':
    print("TOKEN:", token)
    updater = Updater(token=token)
    dispatcher = updater.dispatcher

    dispatcher.add_handler(detect.detect_handler)

    updater.start_polling()

