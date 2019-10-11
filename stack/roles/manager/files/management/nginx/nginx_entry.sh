#!/bin/sh
set -e
echo "[Entrypoint-NGINX] Creating TLS Certificate"
openssl req -subj '/CN<swarm_manager_ip_or_fqdn>/' -x509 -days 365 -nodes -batch -newkey rsa:2048 -keyout /etc/nginx/ssl/nginx.key -out /etc/nginx/ssl/nginx.crt
echo "[Entrypoint-NGINX] Creating Diffie-Hellman parameters"
openssl dhparam -out /etc/nginx/ssl/dhparam.pem 2048
exec "$@"