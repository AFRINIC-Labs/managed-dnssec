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

mv /opendnssec/kasp.xml /etc/opendnssec/
mv /opendnssec/zonelist.xml /etc/opendnssec/


# Update config

sed -e "s/SIGNER_SHM_LABEL/${SHM_LABEL}/g" \
    -e "s/SIGNER_SHM_PIN/${SHM_PIN}/g" \
    -e "s/SIGNER_MYSQL_PORT/${MYSQL_PORT}/g" \
    -e "s/SIGNER_MYSQL_HOST/${MYSQL_HOST}/g" \
    -e "s/SIGNER_MYSQL_DB/${MYSQL_DB}/g" \
    -e "s/SIGNER_MYSQL_USER/${MYSQL_USER}/g" \
    -e "s/SIGNER_MYSQL_PASS/${MYSQL_PASS}/g" /opendnssec/conf.template > /etc/opendnssec/conf.xml

unset -v MYSQL_PASS
unset -v SHM_PIN
unset -v SHM_SO_PIN

sed -e "s/SIGNER_ADAPTER_DNS_TSIG_IN_NAME/${SIGNER_ADAPTER_DNS_TSIG_IN_NAME}/g" \
    -e "s/SIGNER_ADAPTER_DNS_TSIG_IN_ALGORITHM/${SIGNER_ADAPTER_DNS_TSIG_IN_ALGORITHM}/g" \
    -e "s/SIGNER_ADAPTER_DNS_TSIG_IN_SECRET/${SIGNER_ADAPTER_DNS_TSIG_IN_SECRET}/g" \
    -e "s/SIGNER_ADAPTER_DNS_TSIG_OUT_NAME/${SIGNER_ADAPTER_DNS_TSIG_OUT_NAME}/g" \
    -e "s/SIGNER_ADAPTER_DNS_TSIG_OUT_ALGORITHM/${SIGNER_ADAPTER_DNS_TSIG_OUT_ALGORITHM}/g" \
    -e "s/SIGNER_ADAPTER_DNS_TSIG_OUT_SECRET/${SIGNER_ADAPTER_DNS_TSIG_OUT_SECRET}/g" \
    -e "s/SIGNER_ADAPTER_DNS_INBOUND_REMOTE_IP/${SIGNER_ADAPTER_DNS_INBOUND_REMOTE_IP}/g" \
    -e "s/SIGNER_ADAPTER_DNS_INBOUND_REMOTE_PORT/${SIGNER_ADAPTER_DNS_INBOUND_REMOTE_PORT}/g" \
    -e "s/SIGNER_ADAPTER_DNS_OUTBOUND_PEER_IP/${SIGNER_ADAPTER_DNS_OUTBOUND_PEER_IP}/g" /opendnssec/addns.template > /etc/opendnssec/addns.xml

unset -v SIGNER_ADAPTER_DNS_TSIG_IN_SECRET
unset -v SIGNER_ADAPTER_DNS_TSIG_OUT_SECRET

# Erase and setup KASP as opendnssec user on build.
su - opendnssec -c 'yes | ods-enforcer-db-setup'

# Start OpenDNSSEC daemon (in background), ods-enforcerd, ods-signerd
ods-control start

# Import the initial KASP
ods-enforcer policy import

#Add each zone using AXFR with TSIG

#ods-enforcer zone add -z ${UNSIGNED_ZONE} -p ${SIGNER_POLICY_NAME} -j DNS -q DNS --xml -i /etc/opendnssec/addns.xml -o /etc/opendnssec/addns.xml


exec "$@"