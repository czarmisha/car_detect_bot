import os
import requests
import logging
import re
from pathlib import Path
from datetime import datetime
from telegram import Update
from telegram.ext import CallbackContext, MessageHandler, Filters
from sqlalchemy import select, func
from dotenv import load_dotenv
from db.models import Car, Session, engine
import telebot

_BASE_DIR = Path(__file__).resolve().parent.parent
dotenv_path = os.path.join(_BASE_DIR, '.env')
if os.path.exists(dotenv_path):
    load_dotenv(dotenv_path)

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO
)
logger = logging.getLogger(__name__)

TOKEN = os.environ['BOT_TOKEN']
bot = telebot.TeleBot(TOKEN)


def get_plate_numbers(photo_url):
    logger.info('API is working')

    url = "https://license-plate-detection.p.rapidapi.com/license-plate-detection"

    payload = {"url": photo_url}
    headers = {
        "content-type": "application/json",
        "X-RapidAPI-Key": "4f4806731fmsh1202809157ba9b3p1db88fjsne2d8098201c4",
        "X-RapidAPI-Host": "license-plate-detection.p.rapidapi.com"
    }

    try:
        response = requests.post(url, json=payload, headers=headers)
        response.raise_for_status()  # Raise an exception for bad responses (4xx or 5xx)

        data = response.json()

        # Extract plate numbers from the list of dictionaries
        return data

    except requests.exceptions.RequestException as e:
        logger.error(f"Error while calling license plate API: {e}")
        return []
    except Exception as e:
        logger.error(f"Error while processing license plate API response: {e}")
        return []




def car_detect(update: Update, context: CallbackContext):
    logger.info('Start detection...')
    logger.info('Downloading file')

    photo = update.message.photo[-1]
    file = bot.get_file(photo.file_id)
    file_path = file.file_path
    url = f'https://api.telegram.org/file/bot{TOKEN}/{file_path}'

    plate_nums = get_plate_numbers(url)
    if not plate_nums:
        logger.info('I can\'t recognize the plate number')
        return  update.message.reply_text('did not recognize the plate number')

    local_session = Session(bind=engine)
    for num in plate_nums:
        l_pic = num['value']
        l5_pic = l_pic[-5:]
        statement = select(Car).filter(func.similarity(func.substr(Car.plate, 4, 5), l5_pic.upper()) > 0.3)
        car = local_session.execute(statement).scalars().first()

        if car:
            phone = re.sub("[^0-9]", "", car.owner_phone)
            if len(phone) == 9:
                phone = f'+998{phone}'
            elif len(phone) == 12:
                phone = f'+{phone}'
            logger.info('SUCCESS DETECTION')
            txt = 'Это возможно наша машина:\n'
            txt += f'Номер машины: {car.plate}\n' if car.plate else ''
            txt += f'Имя: {car.owner_name}' if car.owner_name else ''
            txt += f'- {car.owner_username}\n' if car.owner_username else ''
            txt += f'Номер владельца: {phone}\n' if phone else ''
            txt += f'Отдел: {car.owner_department}\n' if car.owner_department else ''
            txt += f'Кабинет: {car.owner_cabinet}\n' if car.owner_cabinet else ''


            update.message.reply_text(txt)
            # if not car.owner_username:
            #     context.bot.send_contact(update.effective_chat.id, phone, car.owner_name)
        #else:
            #logger.info('else')
            #plt_num=num['value']
            #domen=os.environ['BOT_DOMAIN']
            #txt2 = f'Не удалось распознать номер ( {plt_num} ) \n(совет: сфоткать номер машины спереди чтобы номер был четко виден)\nДругой возможный вариант: этот автомобиль не зарегистрирован в нашей базе.\nЕсли это ваш автомобиль и данные о вашем автомобиле не существует в базе данных, просим перейти на сайт {domen} и внести данные о вашем автомобиле туда!\n'
            #update.message.reply_text(txt2)
            break
    local_session.close()


detect_handler = MessageHandler(Filters.photo, car_detect)

