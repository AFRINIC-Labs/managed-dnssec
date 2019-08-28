#!/bin/sh
set -e

chown -R pdns:pdns /etc/powerdns 
# Set API parameters in pdns.conf
sed -r -i "s/^[# ]*api-key=.*/api-key=${PDNS_API_KEY}/g" /etc/powerdns/pdns.conf
sed -r -i "s/^[# ]*webserver-address=.*/webserver-address=${PDNS_WEBSERVER_ADDRESS}/g" /etc/powerdns/pdns.conf
sed -r -i "s/^[# ]*webserver-allow-from=.*/webserver-allow-from=${PDNS_WEBSERVER_ALLOW_FROM}/g" /etc/powerdns/pdns.conf
if [ ! -f "/etc/powerdns/bind/dnssec.db" ]
 then
  pdnsutil create-bind-db /etc/powerdns/bind/dnssec.db
fi
pdnsutil import-tsig-key pdns_master_key hmac-sha256 'cG93ZXJkbnNfc2VydmVyCg=='
pdnsutil activate-tsig-key pdns.tld pdns_master_key master
exec "$@"

