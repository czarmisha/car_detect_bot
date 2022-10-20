FROM python:3.9-slim

ENV PYTHONUNBUFFERED 1
ENV DONOTWRITEBYTECODE 1

COPY requirements.txt /tmp/requirements.txt
RUN pip install -r /tmp/requirements.txt

COPY . /app

WORKDIR /app

CMD ["python", "bot.py"]
