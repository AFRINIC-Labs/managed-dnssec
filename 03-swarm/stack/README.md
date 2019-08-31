# Managed DNSSEC with Docker Swarm #

This lab is a proof of concept for Managed DNSSEC AFRINIC Labs project.


## Design ##
![Design Overview](diagram.png)


### Deployment ###
With an Ansible playbook [`stack.yml`](stack.yml), we can deploy a docker swarm `manager` host. This playbook will:
* Install all dependencies for docker, docker-compose and docker swarm.
* Start a swarm cluster on the node.
* Deploy a local registry to be use in the swarm.
* Copy `management` and `stack` folders to the manager host.
* Build and push images on the local registry.
* Deploy the stack.

The `management` folder will deploy a base docker stack (`stack_api`): MySQL servers (master and slave) and Flask API. This stack will offer an API that will be use by external application to create AFRINIC member DNSSEC signer stack.
The `stack` folder is used by the `stack_api` to deploy AFRINIC member DNSSEC signer stack: MySQL server and PowerDNS.


### Access ###
* Management API **http**: the API is listening on port `5005`. The local registry is listening on port `5000`.
* Signer Stack API **http**: each member signer (PowerDNS) API will use a dedicated port starting `30000`.
* **dns**: each member signer will use a dedicated port starting `8000`.

### Mini documentation ###
1. Prepare vault authentication parameters
We assume that `remote_user` can use `sudo` on remote server. Remote server IP/domain is added in group `managers` in `inventory` file.
```
ansible-vault create group_vars/managers/vault.yml
vault_ssh_pass: <remote_user_password>
vault_ssh_user: <remote_user>

```
2. Add vault password in file
```
echo "vault_super_password" > .vault_pass.txt
```
3. Add vault password file in ansible.cfg.
```
vim ansible.cfg
[defaults]
...
vault_password_file = ./.vault_pass.txt
...
```
4. Update environment variables in management
Those variables are use by the `stack_api` while deploying two MySQL server (master and slave) and a Flask API.
```
vim roles/manager/files/management/.env
MYSQL_HOST=mysql_db
MYSQL_DATABASE=mdnssec
MYSQL_USER=mdnssec
MYSQL_PASSWORD=<random_string>
MYSQL_ROOT_PASSWORD=<random_string>
REPLICATION_USER=repl_api
REPLICATION_PASS=<random_string>

SERVER_ID=4294967285
# max 4294967295

PDNS_DNS_PORT=8000
PDNS_API_PORT=30000
FOLDER_PATH=/data/stack/
ENV_BASE_FILE=env.txt
ENV_FILE=.env
ENV_FILE_SLAVE=.env_slave
COMPOSE_BASE_FILE=docker-compose-template.yml
COMPOSE_FILE=docker-compose.yml
# PLEASE, no / or space at the end the API_BASE
API_BASE=/api/v1
TOKEN=<random_string>
MYSQL_SLAVE_SERVER=mysql_replication_db

APP_ENV=Prod
```
5. Update environment variables in management for MySQL replication
```
vim roles/manager/files/management/.env_slave
SERVER_ID=4294967290
MYSQL_ROOT_PASSWORD=<random_string>
MYSQL_ROOT_HOST=%
FOLDER_PATH=/data/stack/
```
6. Run the playbook
```
ansible-playbook stack.yml
```
7. Test if docker client it running
```
curl -X POST -H 'X-Auth-Token: 9lH7ebTv1HLmog'  http://mdnssec.ri.mu.afrinic.net:5005/api/v1/docker | jq .

{
  "error": null,
  "output": "Docker version 19.03.1, build 74b1e89e8a\n",
  "status": "OK"
}
```
8. Test `stack_api`
```
curl -X POST -H 'X-Auth-Token: 9lH7ebTv1HLmog'  http://mdnssec.ri.mu.afrinic.net:5005/api/v1/stack | jq .

{
  "error": null,
  "output": [
    "\"stack_api:3\""
  ],
  "status": "OK"
}
```
9. You can then, create a deployment for AFRINIC member
```
curl -X POST -H 'X-Auth-Token: 9lH7ebTv1HLmog'  http://mdnssec.ri.mu.afrinic.net:5005/api/v1/stack/deploy/ORG-AFNC1-AFRINIC | jq .

{
  "error": null,
  "output": {
    "api_key": "FUlI35WdeR2WrSB",
    "api_port": 30002,
    "dns_port": 8002,
    "stack": "ORG-AFNC1-AFRINIC_S2",
    "url": "curl -v -H 'X-API-Key: FUlI35WdeR2WrSB' http://HOST:30002/api/v1/servers/localhost"
  },
  "status": "OK"
}

curl -X POST -H 'X-Auth-Token: 9lH7ebTv1HLmog'  http://mdnssec.ri.mu.afrinic.net:5005/api/v1/stack/deploy/ORG-AFNC1-AFRINIC | jq .

{
  "error": "Existing",
  "output": "ORG-AFNC1-AFRINIC_S1 (ORG-AFNC1-AFRINIC) is already in stack",
  "status": "KO"
}

```
10. List of stack deployed in the swarm
```
curl -X POST -H 'X-Auth-Token: 9lH7ebTv1HLmog'  http://mdnssec.ri.mu.afrinic.net:5005/api/v1/stack | jq .

{
  "error": null,
  "output": [
    "\"ORG-AFNC1-AFRINIC_S1:2\"",
    "\"stack_api:3\""
  ],
  "status": "OK"
}

```
We have the default `stack_api` with `3` services (MySQL master, MySQL slave and Flask API) and the new deployed customer stack `ORG-AFNC1-AFRINIC_S1` with `2` services (MySQL master and PowerDNS).

11. Get information on a AFRINIC member stack using the stack name
```
curl -X POST -H 'X-Auth-Token: 9lH7ebTv1HLmog'  http://mdnssec.ri.mu.afrinic.net:5005/api/v1/stack/info/ORG-AFNC1-AFRINIC_S2 | jq .

{
  "error": null,
  "output": {
    "api_key": "FUlI35WdeR2WrSB",
    "api_port": 30001,
    "dns_port": 8001,
    "stack": "ORG-AFNC1-AFRINIC_S1",
    "url": "curl -v -H 'X-API-Key: FUlI35WdeR2WrSB' http://HOST:30001/api/v1/servers/localhost"
  },
  "status": "OK"
}

```
12. Check if PowerDNS API is running
```
curl -H 'X-API-Key: FUlI35WdeR2WrSB' http://mdnssec.ri.mu.afrinic.net:30002/api/v1/servers/localhost | jq .

{
  "config_url": "/api/v1/servers/localhost/config{/config_setting}",
  "daemon_type": "authoritative",
  "id": "localhost",
  "type": "Server",
  "url": "/api/v1/servers/localhost",
  "version": "4.2.0",
  "zones_url": "/api/v1/servers/localhost/zones{/zone}"
}

```
13. Remove a stack from the swarm
```
curl -X POST -H 'X-Auth-Token: 9lH7ebTv1HLmog'  http://mdnssec.ri.mu.afrinic.net:5005/api/v1/stack/remove/ORG-AFNC1-AFRINIC_S1 | jq .

{
  "error": null,
  "output": "ORG-AFNC1-AFRINIC_S1",
  "status": "OK"
}

curl -X POST -H 'X-Auth-Token: 9lH7ebTv1HLmog'  http://mdnssec.ri.mu.afrinic.net:5005/api/v1/stack/remove/ORG-AFNC1-AFRINIC_S1 | jq .

{
  "error": "NoStack",
  "output": "Namespace 'ORG-AFNC1-AFRINIC_S1' is not on stack",
  "status": "KO"
}

```

### Next Steps ###
From step `12`, we can start using PowerDNS API
1. Create slave TSIG keys
2. Create slave zone
3. Assign slave TSIG key to slave zone
4. Check zone data
    1. zone existence
    2. zone metadata
    3. zone signed ?
    4. zone data (verify AXFR is ok)
5. Set zone to master
6. Create master TSIG key
7. Assign master TSIG key to master zone
8. Create DNSSEC cryptokeys (KSK/ZSK or CSK)
9. Check is zone is signed
10. Get signed zone on member DNS server
