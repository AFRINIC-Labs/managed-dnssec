# Managed DNSSEC Docker Compose Poc with OpenDNSSEC (MySQL as datastore) #

This lab is a proof of concept for Managed DNSSEC AFRINIC Labs project. 


## Design ##
![Design Overview](diagram.png)

For each container (execpt MySQL), there is a corresponding folder in the project. Each container has a dedicated IP.

### DNS Servers ###
Four authoritative DNS servers:
* **nsd_authoritative** (NSD 4.1.27):
  - zone: `nsd.tld`. Zone file is in `etc/nsd/zones`.
  - Custom Dockerfile based on [Hardware](https://github.com/hardware/nsd-dnssec/blob/master/Dockerfile)
* **bind_authoritative** (Bind, from alpine:3.9)
  - zone: `bind.tld`. Zone file is in `etc/bind/zones`.
  - Custom Dockerfile based on [ventz](https://github.com/ventz/docker-bind/blob/master/container/Dockerfile)
* **pdns_authoritative** (PowerDNS 4.2.0-rc2)
  - Fetch zones from shared MySQL database
  - Custom Dockerfile based on [connectitnet](https://github.com/connectitnet/powerdns-for-docker/blob/master/pdns/Dockerfile)
* **knot_authoritative** (Knot 2.7)
  - Fetch signed zones from signer (OpenDNSSEC)
  - Use official image from Docker hub

#### Signer ####
**opendnssec** container from custom Dockerfile (based on [bombsimon](https://github.com/bombsimon/docker-opendnssec-softhsm/blob/master/Dockerfile)) sign zones using TSIG AXFR to retrieve zones from masters (**nsd_authoritative**, **bind_authoritative**, **pdns_authoritative**) and send signed zones to **knot_authoritative** using TSIG AXFR.

#### Storage ####
One **shared_mysql** container from `mysql/mysql-server:5.7` image. MySQL Data and configurations (`bind_authoritative`/`nsd_authoritative`/`pdns_authoritative`/`shared_mysql` / `opendnssec`) are saved to disk using docker volume from `etc` folder. **opendnssec** create required tables on **shared_mysql** database to be use by Enforcer Datastore.

#### Environment ####
Environment variables related to MySQL, PowerDNS and OpenDNSSEC are defined in `.env` file.


### How to ###
How to deploy the lab
* Clean some volume
```
docker volume rm nsd_db
docker volume rm shared_mysql_data
docker volume rm pdns_authoritative
```
* Build it
```
docker-compose build
```
* Run it
```
docker-compose up -d
```
* Connect to `knot_authoritative`
```
docker exec -it knot_authoritative /bin/sh
```
* Run kdrill commands
```
kdig soa nsd.tld
kdig soa pdns.tld
kdig soa bind.tld
```
* External access (from host where docker-compose has been run)
```
dig @172.16.10.10 soa nsd.tld
dig @172.16.10.10 soa pdns.tld
dig @172.16.10.10 soa bind.tld
```
