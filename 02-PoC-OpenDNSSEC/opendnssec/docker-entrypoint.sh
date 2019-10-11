#!/usr/bin/env sh

set -eux

if $MYSQL_AUTOCONF ; then
  if [ -z "$MYSQL_PORT" ]; then
      MYSQL_PORT=3306
  fi   
  
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
    echo "CREATE DATABASE IF NOT EXISTS $MYSQL_DB;" | $MYSQLCMD
    MYSQLCMD="$MYSQLCMD $MYSQL_DB"

    if [ "$(echo "SELECT COUNT(*) FROM information_schema.tables WHERE table_schema = \"$MYSQL_DB\";" | $MYSQLCMD)" -le 1 ]; then
      echo Initializing Database
      cat /opendnssec/schema_mysql.sql | $MYSQLCMD
    fi

  fi

# Initialize and reassign SoftHSM token slot
su - opendnssec -c "softhsm2-util --init-token --slot 0 --label ${SHM_LABEL} --pin ${SHM_PIN} --so-pin ${SHM_SO_PIN}"

# Update config

sed -r -i "s/SHM_LABEL/${SHM_LABEL}/g" /etc/opendnssec/conf.xml
sed -r -i "s/SHM_PIN/${SHM_PIN}/g" /etc/opendnssec/conf.xml
sed -r -i "s/MYSQL_PORT/${MYSQL_PORT}/g" /etc/opendnssec/conf.xml
sed -r -i "s/MYSQL_HOST/${MYSQL_HOST}/g" /etc/opendnssec/conf.xml
sed -r -i "s/MYSQL_DB/${MYSQL_DB}/g" /etc/opendnssec/conf.xml
sed -r -i "s/MYSQL_USER/${MYSQL_USER}/g" /etc/opendnssec/conf.xml
sed -r -i "s/MYSQL_PASS/${MYSQL_PASS}/g" /etc/opendnssec/conf.xml

unset -v MYSQL_PASS

# Erase and setup KASP as opendnssec user on build.
su - opendnssec -c 'yes | ods-enforcer-db-setup'

# Start OpenDNSSEC daemon (in background), ods-enforcerd, ods-signerd
ods-control start

# Import the initial KASP
ods-enforcer policy import

#Add each zone using AXFR with TSIG

ods-enforcer zone add -z pdns.tld -p lab -j DNS -q DNS --xml -i /etc/opendnssec/addns_pdns.xml -o /etc/opendnssec/addns_pdns.xml
ods-enforcer zone add -z bind.tld -p lab -j DNS -q DNS --xml -i /etc/opendnssec/addns_bind.xml -o /etc/opendnssec/addns_bind.xml
ods-enforcer zone add -z nsd.tld -p lab -j DNS -q DNS --xml -i /etc/opendnssec/addns_nsd.xml -o /etc/opendnssec/addns_nsd.xml

exec "$@"