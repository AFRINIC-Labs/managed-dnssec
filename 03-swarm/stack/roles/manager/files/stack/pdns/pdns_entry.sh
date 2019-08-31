#!/bin/sh
set -e

if $MYSQL_AUTOCONF ; then
  if [ -z "$MYSQL_PORT" ]; then
      MYSQL_PORT=3306
  fi

  echo "[Entrypoint-PowerDNS] Creating pdns.conf"

  sed -e "s/MYSQL_PASS/${MYSQL_PASSWORD}/g" \
      -e "s/MYSQL_HOST/${MYSQL_HOST}/g" \
      -e "s/MYSQL_PORT/${MYSQL_PORT}/g" \
      -e "s/MYSQL_USER/${MYSQL_USER}/g" \
      -e "s/MYSQL_DATABASE/${MYSQL_DATABASE}/g" \
      -e "s/API_KEY/${API_KEY}/g" \
      -e "s/API_PORT/${API_PORT}/g" /pdns.template > /etc/powerdns/pdns.conf

  MYSQLCMD="mysql --host=${MYSQL_HOST} --user=${MYSQL_USER} --password=${MYSQL_PASSWORD} --port=${MYSQL_PORT} -r -N"

  # wait for Database come ready
  isDBup () {
    echo "SHOW STATUS" | $MYSQLCMD 1>/dev/null
    echo $?
  }

  until [ `isDBup` -eq 0 ]; do
    >&2 echo '[Entrypoint-PowerDNS] MySQL is unavailable - sleeping'
    sleep 1
  done 

  # init database if necessary
  echo "CREATE DATABASE IF NOT EXISTS ${MYSQL_DATABASE};" | $MYSQLCMD
  MYSQLCMD="$MYSQLCMD --database=${MYSQL_DATABASE}"

  if [ "$(echo "SELECT COUNT(*) FROM information_schema.tables WHERE table_schema = \"$MYSQL_DATABASE\";" | $MYSQLCMD)" -le 1 ]; then
    echo "[Entrypoint-PowerDNS] Initializing Database"
    cat /schema_mysql.sql | $MYSQLCMD
  fi


fi
MYSQL_PASSWORD=""
unset -v MYSQL_PASSWORD

exec "$@"

