#https://github.com/ventz/docker-bind/blob/master/container/Dockerfile
FROM alpine:3.9
EXPOSE 53 53/udp

RUN apk --update upgrade && apk add bind

VOLUME /etc/bind /var/cache/bind

COPY entrypoint.sh /
ENTRYPOINT ["/entrypoint.sh"]
