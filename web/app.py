from flask import Flask, render_template, request, redirect, url_for, redirect, session, make_response
import os, requests
from pathlib import Path
from dotenv import load_dotenv
from sqlalchemy.orm import declarative_base, sessionmaker
from sqlalchemy import create_engine, Column, Integer, String, Sequence
from functools import wraps
from datetime import datetime, timedelta
import pytz

app = Flask(__name__)

_BASE_DIR = Path(__file__).resolve().parent.parent
dotenv_path = os.path.join(_BASE_DIR, '.env')
if os.path.exists(dotenv_path):
    load_dotenv(dotenv_path)

_db_host = os.environ['POSTGRES_HOST']
_db_username = os.environ['POSTGRES_USERNAME']
_db_password = os.environ['POSTGRES_PASSWORD']
_db_name = os.environ['POSTGRES_DB']
_db_port = os.environ['POSTGRES_PORT']
engine = create_engine(
    f'postgresql://{_db_username}:{_db_password}@{_db_host}:{_db_port}/{_db_name}', echo=True)

Base = declarative_base()
Session = sessionmaker(bind=engine)


def get_db_session():
    return sessionmaker(bind=engine)()


secret_key = os.environ['SECRET_KEY']

app.config['SECRET_KEY'] = secret_key
app.config["TEMPLATES_AUTO_RELOAD"] = True
app.config['SESSION_COOKIE_SECURE'] = True

app.jinja_env.globals.update(BOTID='BOT_ID')
app.jinja_env.globals.update(BOTNAME='BOT_NAME')
app.jinja_env.globals.update(BOTDOMAIN='BOT_DOMAIN')
app.jinja_env.globals.update(BOT_TOKEN='BOT_TOKEN')

bot_token = os.environ['BOT_TOKEN']
chat_id = os.environ['GROUP_ID']


@app.before_request
def session_lifetime():
    session.permanent = True
    app.permanent_session_lifetime = timedelta(hours=6)


def user_info(tmpl_name, **kwargs):
    telegram = False
    user_id = session.get('user_id')
    username = session.get('name')
    photo = session.get('photo')

    if user_id:
        telegram = True

    return render_template(tmpl_name,
                           telegram=telegram,
                           user_id=user_id,
                           name=username,
                           photo=photo,
                           **kwargs)


def user_check(chat_id, user_id):
    url = f'https://api.telegram.org/bot{bot_token}/getChatMember'
    params = {'chat_id': chat_id, 'user_id': user_id}
    res = requests.get(url=url, params=params)
    if res.status_code != 200 or res.json()['result'].get('status') == 'left':
        return {}
    return res.json()


def requires_authentication(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        user_id = session.get('user_id')
        if not user_id:
            return redirect(url_for('index'))
        return f(*args, **kwargs)

    return decorated_function


@app.route("/")
def index(*args, **kwargs):
    # Check if the user_id is stored in the session (cookie)
    user_id = session.get('user_id')
    host_url = request.url_root

    if user_id and 'last_auth_time':
        # Check if the session has expired based on the session lifetime
        zone_uz = pytz.timezone('Asia/Tashkent')
        current_time = datetime.now(zone_uz)  # Get the current time in UTC
        last_auth_time = session['last_auth_time']
        max_age = app.permanent_session_lifetime

        # Check if the session has not expired
        if (current_time - last_auth_time) < max_age:
            # Update the last_auth_time with the current time to extend the session
            session['last_auth_time'] = current_time
            return redirect(url_for('home'))

        # If user_id or last_auth_time is missing or session has expired, redirect to login page
    return user_info("telegram.html", host_url=host_url)


@app.route("/logout")
def logout():
    # Clear user error and last_auth_time from the session (cookie)
    session.pop("user_id", None)
    session.pop("name", None)
    session.pop("last_auth_time", None)
    return render_template("telegram.html")


@app.route("/login")
def login():
    user_id = request.args.get("id")
    first_name = request.args.get("first_name")
    photo_url = request.args.get("photo_url")
    # Save user error and set the max-age for the session (cookie)
    user_status = user_check(chat_id=chat_id, user_id=user_id)
    if not user_status:
        return redirect(url_for('unauthorized'))
    session['user_id'] = user_id
    session['name'] = first_name
    session['photo'] = photo_url
    zone_uz = pytz.timezone('Asia/Tashkent')
    session['last_auth_time'] = datetime.now(zone_uz)  # Get the current time in UTC
    # session.permanent = True  # Set the session to be permanent (max_age will be set)

    return redirect(url_for('home'))


@app.route("/unauthorized")
def unauthorized():
    return render_template("unauthorized.html")


class Car(Base):
    __tablename__ = 'car'

    id = Column(Integer, Sequence('car_id_seq', start=1, increment=1), primary_key=True, nullable=False,
                autoincrement=True)
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


Base.metadata.create_all(engine)


@app.route('/home')
@requires_authentication
def home():
    user_id = session.get('user_id')
    username = session.get('name')
    photo = session.get('photo')

    if user_id is None:
        # If the user is not authenticated, redirect to the login page
        return redirect(url_for('index'))

    # Fetch the cars data from your database using the SQLAlchemy session
    dbsession = get_db_session()
    cars = dbsession.query(Car).order_by(Car.id.asc()).all()
    dbsession.close()

    return render_template('home.html', cars=cars, telegram=True, user_id=user_id, name=username, photo=photo)


@app.route('/add', methods=['GET', 'POST'])
@requires_authentication
def add_car():
    if request.method == 'POST':
        car_data = {
            'model': request.form['model'],
            'plate': request.form['plate'],
            'owner_phone': request.form['owner_phone'],
            'owner_name': request.form['owner_name'],
            'owner_email': request.form['owner_email'],
            'owner_department': request.form['owner_department'],
            'owner_cabinet': request.form['owner_cabinet'],
            'owner_username': request.form['owner_username'],
        }
        insert_car(car_data)
        return redirect(url_for('home'))
    return render_template('add_car.html')


def insert_car(car_data):
    session = Session()
    last_car = session.query(Car).order_by(Car.id.desc()).first()
    if last_car:
        new_id = last_car.id + 1
    else:
        new_id = 1

    car_data['id'] = new_id
    new_car = Car(**car_data)
    session.add(new_car)
    session.commit()
    session.close()


@app.route('/edit/<int:car_id>', methods=['GET', 'POST'])
@requires_authentication
def edit_car(car_id):
    session = Session()
    car = session.query(Car).filter(Car.id == car_id).first()

    if request.method == 'POST':
        car.model = request.form['model']
        car.plate = request.form['plate']
        car.owner_phone = request.form['owner_phone']
        car.owner_name = request.form['owner_name']
        car.owner_email = request.form['owner_email']
        car.owner_department = request.form['owner_department']
        car.owner_cabinet = request.form['owner_cabinet']
        car.owner_username = request.form['owner_username']
        session.commit()
        session.close()
        return redirect(url_for('home'))

    session.close()
    return render_template('edit_car.html', car=car)


@app.route('/delete/<int:car_id>', methods=['GET', 'POST'])
def delete_car(car_id):
    session = Session()
    car = session.query(Car).filter(Car.id == car_id).first()

    if car:
        session.delete(car)
        session.commit()
    session.close()
    return redirect(url_for('home'))


if __name__ == '__main__':
    app.run(debug=True)
