# https://github.com/connectitnet/powerdns-for-docker/blob/master/pdns/Dockerfile
FROM python:3.6-jessie
LABEL maintainer="Jonathan Senecal <JSenecal@jonathansenecal.com>"

ENV DEBIAN_FRONTEND=noninteractive \
    MYSQL_AUTOCONF=true

RUN echo "deb [arch=amd64] http://repo.powerdns.com/debian jessie-auth-42 main" > /etc/apt/sources.list.d/pdns.list
COPY preference.pdns /etc/apt/preferences.d/pdns

RUN apt-get update && apt-get install -y --no-install-recommends curl gnupg gnupg-curl apt-transport-https \
  && apt-key adv --no-tty --fetch-keys https://repo.powerdns.com/FD380FBB-pub.asc \
  && apt-get update && apt-get install -y --no-install-recommends \
  pdns-server \
  pdns-backend-mysql \
  pdns-tools \
  mysql-client 

EXPOSE 53/tcp 53/udp


VOLUME /etc/powerdns/

ADD pdns_entry.sh /


ENTRYPOINT [ "bash","/pdns_entry.sh"]

CMD [ "/usr/sbin/pdns_server" ]