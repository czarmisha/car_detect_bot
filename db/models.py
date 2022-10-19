import os
from pathlib import Path
from dotenv import load_dotenv
from sqlalchemy.orm import declarative_base, sessionmaker
from sqlalchemy import create_engine, Column, SmallInteger, String

_BASE_DIR = Path(__file__).resolve().parent.parent
dotenv_path = os.path.join(_BASE_DIR, '.env')
if os.path.exists(dotenv_path):
    load_dotenv(dotenv_path)

_db_host = os.environ['POSTGRES_HOST']
_db_username = os.environ['POSTGRES_USERNAME']
_db_password = os.environ['POSTGRES_PASSWORD']
_db_name = os.environ['POSTGRES_DB']
engine = create_engine(
    f'postgresql://{_db_username}:{_db_password}@{_db_host}:5432/{_db_name}', echo=True)

Base = declarative_base()
Session = sessionmaker()


class Car(Base):
    __tablename__ = 'car'

    id = Column(SmallInteger, primary_key=True)
    model = Column(String(70), nullable=False)
    plate = Column(String(50), nullable=False)
    owner_phone = Column(String(50), nullable=False)
    owner_name = Column(String(70), nullable=True)
    owner_email = Column(String(100), nullable=True)
    owner_department = Column(String(150), nullable=True)
    owner_cabinet = Column(String(50), nullable=True)
    owner_username = Column(String(70), nullable=True)

    def __repr__(self):
        return f'<Car: plate - {self.plate}>'
