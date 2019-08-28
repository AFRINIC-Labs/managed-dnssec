#!/bin/sh
OPTIONS=$@
chown -R named:named /etc/bind /var/run/named
chown -R named:named /var/cache/bind
chmod -R 770 /var/cache/bind /var/run/named
chmod -R 750 /etc/bind
wget -q -O /etc/bind/bind.keys https://ftp.isc.org/isc/bind9/keys/9.11/bind.keys.v9_11
rndc-confgen -a -r /dev/urandom
chown -R named:named /etc/bind/rndc.key
# Run in foreground and log to STDERR (console):
exec /usr/sbin/named -c /etc/bind/named.conf -g -u named $OPTIONS