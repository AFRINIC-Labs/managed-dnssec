FROM nginx:1.17.4
RUN apt-get update && \
     apt-get install --no-install-recommends --no-install-suggests  -y iputils-ping dnsutils curl openssl
RUN mkdir -p /etc/nginx/ssl
COPY default.template /etc/nginx/conf.d/default.conf
COPY dhparam.pem /etc/nginx/ssl/dhparam.pem
COPY nginx.key /etc/nginx/ssl/nginx.key
COPY nginx.crt /etc/nginx/ssl/nginx.crt
EXPOSE 443
