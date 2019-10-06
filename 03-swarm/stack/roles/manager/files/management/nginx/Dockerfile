FROM nginx:1.17.4
RUN apt-get update && \
     apt-get install --no-install-recommends --no-install-suggests  -y iputils-ping dnsutils curl openssl
RUN mkdir -p /etc/nginx/ssl
COPY nginx_entry.sh /
#COPY default.template /etc/nginx/conf.d/default.template
COPY default.template /etc/nginx/conf.d/default.conf
EXPOSE 443
ENTRYPOINT [ "bash","/nginx_entry.sh"]
CMD ["nginx", "-g", "daemon off;"]
