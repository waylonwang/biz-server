FROM python:3.5.1
MAINTAINER Waylon Wang <waylon.act@gmail.com>

WORKDIR /biz-server
COPY *.py ./
COPY common common
COPY plugins plugins
COPY templates templates
COPY static static
COPY bower_components bower_components
COPY requirements.txt requirements.txt

RUN pip install --upgrade pip
RUN pip install -r requirements.txt

RUN apt-get update \
    && apt-get install -y libav-tools \
    && apt-get install -y net-tools \
    && apt-get install -y iputils-ping \
    && apt-get install -y vim \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /
VOLUME /biz-server

CMD python /biz-server/app.py