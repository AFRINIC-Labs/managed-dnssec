FROM python:3-alpine3.9
RUN apk add --no-cache build-base
RUN apk add --no-cache libffi-dev
RUN apk add --no-cache openssl-dev
RUN pip install flask
RUN pip install flask_sqlalchemy
RUN pip install docker-compose
RUN apk add mariadb-connector-c-dev
RUN pip install mysqlclient
ARG DOCKER_CLI_VERSION="19.03.1"
ENV DOWNLOAD_URL="https://download.docker.com/linux/static/stable/x86_64/docker-$DOCKER_CLI_VERSION.tgz"
RUN apk add curl \
    && mkdir -p /tmp/download \
    && curl -L $DOWNLOAD_URL | tar -xz -C /tmp/download \
    && mv /tmp/download/docker/docker /usr/local/bin/ \
    && rm -rf /tmp/download \
    && rm -rf /var/cache/apk/*
COPY src /src/
RUN mkdir /data
EXPOSE 5000
ENTRYPOINT ["python", "/src/mdnssec.py"]
