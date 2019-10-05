FROM nginx:1.17.4-alpine
#COPY default.template /etc/nginx/conf.d/default.template
#RUN apt-get install -y curl
COPY default.template /etc/nginx/conf.d/default.conf
##COPY nginx_entry.sh /
#RUN apt-get update && \
#     apt-get install --no-install-recommends --no-install-suggests  -y iputils-ping dnsutils curl
##ENTRYPOINT [ "bash","/nginx_entry.sh"]
##CMD ["nginx", "-g", "daemon off;"]
