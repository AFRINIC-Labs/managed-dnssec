FROM python:3-alpine3.9

RUN pip install flask
RUN pip install kubernetes

COPY src /src/

EXPOSE 5000

ENTRYPOINT ["python", "/src/app.py"]