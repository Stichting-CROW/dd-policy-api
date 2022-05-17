FROM python:3.9-slim-bullseye

RUN apt-get clean \
    && apt-get -y update
RUN apt-get -y install python3-dev \
    && apt-get -y install build-essential libpq-dev


COPY requirements.txt /
RUN pip install -r /requirements.txt

COPY . /srv/policy-api
WORKDIR /srv/policy-api

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "80"]