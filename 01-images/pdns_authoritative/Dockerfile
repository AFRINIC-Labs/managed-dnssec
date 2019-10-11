# https://github.com/connectitnet/powerdns-for-docker/blob/master/pdns/Dockerfile
#FROM python:3.6-stretch
FROM debian:stretch-slim
LABEL maintainer="Alfred Arouna"

ENV DEBIAN_FRONTEND=noninteractive \
    MYSQL_AUTOCONF=true

RUN apt-get update && apt-get install -y --no-install-recommends curl gnupg apt-transport-https dirmngr \
  && apt-key adv --no-tty --fetch-keys http://repo.powerdns.com/FD380FBB-pub.asc

RUN echo "deb [arch=amd64] http://repo.powerdns.com/debian stretch-auth-42 main" > /etc/apt/sources.list.d/pdns.list
COPY preference.pdns /etc/apt/preferences.d/pdns
RUN apt-get update && apt-get install -y --no-install-recommends \
  pdns-server \
  pdns-backend-mysql \
  pdns-tools \
  mysql-client

EXPOSE 53/tcp 53/udp

#COPY pdns.conf /etc/powerdns/
COPY pdns.template /

ADD pdns_entry.sh /

ADD schema_mysql.sql /


ENTRYPOINT [ "bash","/pdns_entry.sh"]

CMD [ "/usr/sbin/pdns_server" ]