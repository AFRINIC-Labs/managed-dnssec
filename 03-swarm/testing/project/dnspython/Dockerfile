FROM python:3-alpine
RUN apk add curl
RUN pip install dnspython requests
VOLUME /usr/src/app
WORKDIR /usr/src/app
CMD [ "python", "-u","./app.py" ]