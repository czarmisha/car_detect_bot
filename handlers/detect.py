import os, requests, base64, logging
from pathlib import Path
from datetime import datetime
from telegram import Update
from telegram.ext import CallbackContext, MessageHandler, Filters
from sqlalchemy import select, func
from dotenv import load_dotenv
from db.models import Car, Session, engine

_BASE_DIR = Path(__file__).resolve().parent.parent
dotenv_path = os.path.join(_BASE_DIR, '.env')
if os.path.exists(dotenv_path):
    load_dotenv(dotenv_path)

_TOKEN = os.environ['PLATE_RECOGNITION_TOKEN']

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO
)
logger = logging.getLogger(__name__)

local_session = Session(bind=engine)

def get_plate_numbers(file_path):
    logger.info('API is working')
    with open(file_path, "rb") as image:
            img_b64 = base64.b64encode(image.read())
            url = 'https://api.platerecognizer.com/v1/plate-reader/'
            data={
                'regions': 'uz',
                'upload': img_b64,
                "detection_rule": "strict",
            }
            headers = {
                "Authorization": f"Token {_TOKEN}"
            }
            response = requests.post(url=url, headers=headers, data=data)
            if response.ok:
                return (True, response.json()['results'])
            else:
                return (False, response.text)


def car_detect(update: Update, context: CallbackContext):
    logger.info('Start detection')
    logger.info('Downloading file')
    file = context.bot.getFile(update.message.photo[1].file_id)
    file_path = f'media/images/{update.effective_user.id}-{datetime.now().strftime("%Y%m%d%H%M")}.jpg'
    file.download(file_path)

    plate_nums = get_plate_numbers(file_path)
    if not plate_nums[0]:
        logger.info('I can\'t recognize the plate number')
        os.remove(file_path)
        return #ignore if does not recognize plate on image
    for num in plate_nums[1]:
        logger.info(f"FINDING CAR from db. Plate num: {num['plate']}")
        statement = select(Car).filter(func.similarity(Car.plate, num['plate'].upper()) > 0.4)
        car = local_session.execute(statement).scalars().first()
        if car:
            logger.info('SUCCESS DETECTION')
            txt = 'Это возможно наша машина:\n'
            txt +=  f'Номер машины: {car.plate}\n' if car.plate else ''
            txt +=  f'Имя: {car.owner_name}' if car.owner_name else ''
            txt +=  f' - {car.owner_username}\n' if car.owner_username else ''
            txt +=  f'Номер владельца: {car.owner_phone}\n' if car.owner_phone else ''
            txt +=  f'Отдел: {car.owner_department}\n' if car.owner_department else ''
            txt +=  f'Кабинет: {car.owner_cabinet}\n' if car.owner_cabinet else ''

            update.message.reply_text(txt)
            if not car.owner_username:
                context.bot.send_contact(update.effective_chat.id, car.owner_phone, car.owner_name)
            
            break

    os.remove(file_path)

detect_handler = MessageHandler(Filters.photo, car_detect)
