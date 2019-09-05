# Managed-DNSSEC
A container-based hosted DNSSEC service.

## Objectives ##
* Automate DNSSEC zone signing for AFRINIC Members.
* Deploy a container-based infrastructure using differents approach.
* Test containers schedulers solutions.

## Delivrables ##
* DNSSEC signing  using native Docker Compose (PoC).
* Orchestration and scheduling of DNSSEC signing using k8s (PoC).
* **DNSSEC signing  using Docker Swarm** (Staging).

### Docker Compose PoC ###
Three implementations have been tested:
* `PowerDNS` as signer with other authoritative DNS servers (bind, nsd). `dnspython` is used to retrieved signed zone. More details [here](01-compose/01-PoC-PowerDNS).
* `OpenDNSSEC` as signer (using DNS adapter) with other authoritative DNS servers (bind, nsd, pdns). `knot` is used to retrieved signed zone. See next implementation.
* Same as previous one with MySQL backend for OpenDNSSEC Enforcer. More details [here](01-compose/02-PoC-OpenDNSSEC).

### Kubernetes PoC ###
Two implementations have been tested:
* `PowerDNS` as signer with MySQL backend. More details [here](02-k8s/02-pdns)
* `OpenDNSSEC` as signer (using DNS adapter) with MySQL backend. Since `OpenDNSSEC` did not offer an API, we added a `Flask` API that use `k8s` `Role` and `RoleBinding` on `pods/exec` resources. This API can then, receive external request and run openDNSSEC related command. More details [here](02-k8s/03-opendnssec)

We use private registry to store custom images. More details [here](02-k8s/01-images)

### Docker Swarm ###
This is the selected choice. We use PowerDNS 4.2.x (require to manipulate TSIGKeys). More details [here](03-swarm/stack). For testing, we have deployed authoritative DNS servers (NSD, Bind) as master to the signer (PowerDNS) and Knot as slave for the signer (PowerDNS). More details [here](03-swarm/testing).

