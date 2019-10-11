#!/bin/sh
set -e

if $MYSQL_AUTOCONF ; then
  if [ -z "$MYSQL_PORT" ]; then
      MYSQL_PORT=3306
  fi

  sed -e "s/MYSQL_PASS/${MYSQL_PASS}/g" \
      -e "s/MYSQL_HOST/${MYSQL_HOST}/g" \
      -e "s/MYSQL_PORT/${MYSQL_PORT}/g" \
      -e "s/MYSQL_USER/${MYSQL_USER}/g" \
      -e "s/MYSQL_DATABASE/${MYSQL_DATABASE}/g" \
      -e "s/SIGNER_API_KEY/${SIGNER_API_KEY}/g" /pdns.template > /etc/powerdns/pdns.conf


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

  # init database if necessary
  echo "CREATE DATABASE IF NOT EXISTS ${MYSQL_DATABASE};" | $MYSQLCMD
  MYSQLCMD="$MYSQLCMD --database=${MYSQL_DATABASE}"

  if [ "$(echo "SELECT COUNT(*) FROM information_schema.tables WHERE table_schema = \"$MYSQL_DATABASE\";" | $MYSQLCMD)" -le 1 ]; then
    echo Initializing Database
    cat /schema_mysql.sql | $MYSQLCMD
  fi


fi
unset -v $MYSQL_PASS

exec "$@"

