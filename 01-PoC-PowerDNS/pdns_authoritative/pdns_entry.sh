#!/bin/sh
set -e

if $MYSQL_AUTOCONF ; then
  if [ -z "$MYSQL_PORT" ]; then
      MYSQL_PORT=3306
  fi
  # Set MySQL Credentials in pdns.conf
  sed -r -i "s/^[# ]*gmysql-host=.*/gmysql-host=${MYSQL_HOST}/g" /etc/powerdns/pdns.conf
  sed -r -i "s/^[# ]*gmysql-port=.*/gmysql-port=${MYSQL_PORT}/g" /etc/powerdns/pdns.conf
  sed -r -i "s/^[# ]*gmysql-user=.*/gmysql-user=${MYSQL_USER}/g" /etc/powerdns/pdns.conf
  sed -r -i "s/^[# ]*gmysql-password=.*/gmysql-password=${MYSQL_PASS}/g" /etc/powerdns/pdns.conf
  sed -r -i "s/^[# ]*gmysql-dbname=.*/gmysql-dbname=${MYSQL_DATABASE}/g" /etc/powerdns/pdns.conf

  # Set API parameters in pdns.conf
  sed -r -i "s/^[# ]*api-key=.*/api-key=${PDNS_API_KEY}/g" /etc/powerdns/pdns.conf
  sed -r -i "s/^[# ]*webserver-address=.*/webserver-address=${PDNS_WEBSERVER_ADDRESS}/g" /etc/powerdns/pdns.conf
  sed -r -i "s/^[# ]*webserver-allow-from=.*/webserver-allow-from=${PDNS_WEBSERVER_ALLOW_FROM}/g" /etc/powerdns/pdns.conf


  MYSQLCMD="mysql --host=${MYSQL_HOST} --user=${MYSQL_USER} --password=${MYSQL_PASS} --port=${MYSQL_PORT} -r -N"


  # wait for Database come ready
   isDBup () {
    echo "SHOW STATUS" | $MYSQLCMD 1>/dev/null
    echo $?
   }

   until [ `isDBup` -eq 0 ]; do
    >&2 echo 'MySQL is unavailable - sleeping'
    sleep 1
   done

fi

# Run pdns server
#trap "pdns_control quit" SIGHUP SIGINT SIGTERM

#pdns_server "$@" &

exec "$@"

