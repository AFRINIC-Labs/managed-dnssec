FROM python:3-alpine
RUN apk add curl
RUN pip install dnspython requests
VOLUME /usr/src/app
RUN mkdir /usr/src/app/data
WORKDIR /usr/src/app
CMD [ "python", "-u","./app.py" ]