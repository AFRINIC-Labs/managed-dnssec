# Managed-dnssec
A container-based hosted DNSSEC service

## Objectives ##

## Delivrables ie Proof of Concept (PoC) ##

## Docker Compose PoC ##
Three implementation have been tested:
* `PowerDNS` as signer with other authoritative DNS servers (bind, nsd). `dnspython` is used to retrived signed zone. More details [here](01-PoC-PowerDNS)
* `OpenDNNSEC` as signer (using DNS adapter) with other authoritative DNS servers (bind, nsd, pdns). `knot` is used to retrived signed zone. See next implementation.
* Same as previous one with MySQL backend for OpenDNSSEC Enforcer. More details [here](02-PoC-OpenDNSSEC).

## Kubernetes PoC ##

## Docker Swarm Poc ##
