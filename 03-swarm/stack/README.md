# Managed DNSSEC with Docker Swarm #

This lab is a proof of concept for Managed DNSSEC AFRINIC Labs project.


## Design ##
![Design Overview](diagram.png)


### Deployment ###
With an Ansible playbook [`stack.yml`](stack.yml) that use a custom role [manager](roles/manager), we can deploy a docker swarm `manager` host. This playbook will:
* Install all dependencies for docker, docker-compose and docker swarm.
* Start a swarm cluster on the node.
* Deploy a local registry to be use in the swarm.
* Copy `management` and `stack` folders to the manager host.
* Build and push images on the local registry.
* Deploy the stack.

The `management` folder will deploy a base docker stack (`stack_api`): MySQL servers (master and slave) and Flask API. This stack will offer an API that will be use by external application to create AFRINIC member DNSSEC signer stack.
The `stack` folder is used by the `stack_api` to deploy AFRINIC member DNSSEC signer stack: MySQL server and PowerDNS.


### Access ###
* ~~Management API **http**: the API is listening on port `5005`~~ Management API **http**: the API is listening on port `443`. The local registry is listening on port `5000`.
* Signer Stack API **http**: each member signer (PowerDNS) API will use a dedicated port starting `30000`.
* **dns**: each member signer will use a dedicated port starting `8000`.


| Action                             | HTTP Verb           | Parameters            | Required authentication | Url                                   | Result                                   | 
|------------------------------------|:-------------------:|-----------------------|-------------------------|---------------------------------------|------------------------------------------|
| General info                       | ``GET``             | None                  | X-Auth-Token: TOKEN     | /info                                 | Container network information            |
| Check if docker dameon is running  | ``GET`` or ``POST`` | None                  | X-Auth-Token: TOKEN     | /docker                               | Docker client status                     |
| List all members in the stack      | ``POST``            | None                  | X-Auth-Token: TOKEN     | /stack                                | Array of **Member Stack Name**           |
| Deploy new stack (for a member)    | ``POST``            | Member AFRINIC Org ID | X-Auth-Token: TOKEN     | /stack/deploy/{member_afrinic_org_id} | New **Member Stack Name** with metadata  |
| Get metadata on a member stack     | ``POST``            | Member Stack Name     | X-Auth-Token: TOKEN     | /stack/info/{member_stack_id}         | Member Stack metadata                    |
| Remove member stack                | ``POST``            | Member Stack Name     | X-Auth-Token: TOKEN     | /stack/remove/{member_stack_id}       |  Removed **Member Stack Name**           |

All paths are relative to ~~``http://<swarm_manager_ip_or_fqdn>:5005/api/v1``~~``http://<swarm_manager_ip_or_fqdn>/api/v1``.
### Mini documentation ###
1. Add vault password in file
```
echo "vault_super_password" > .vault_pass.txt
```

2. Prepare vault authentication parameters
We assume that `remote_user` can use `sudo` on remote server. Remote server IP/domain is added in group `managers` in `inventory` file ie replace *<swarm_manager_ip_or_fqdn>* by the swarm server.
```
ansible-vault create group_vars/managers/vault.yml

vault_ssh_pass: <remote_user_password>
vault_ssh_user: <remote_user>

```
3. Add vault password file in ansible.cfg (it should be done already).
```
vim ansible.cfg

[defaults]
...
vault_password_file = ./.vault_pass.txt
...
```
4. Update environment variables in `management` folder
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
REPLICATION_SERVER=mysql_replication_db
REPLICATION_CHANNEL=stack_api

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

APP_ENV=Prod
WORKER_NODE=<swarm_manager_ip_or_fqdn>
```
Variables starting by **MYSQL_** are related to MySQL master instance. Note that MySQL port `3306` is not open to external.


Variables starting by **REPLICATION_** are related to MySQL slave instance (multi-source replication). Note that MySQL port `3306` is not open to external.

**SERVER_ID** is used by the MySQL multi-source replication process to identify each MySQL instance.

Variables starting by **PDNS_** are related to PowerDNS (DNSSEC signer). **PDNS_DNS_PORT** is the starting DNS port for all signer instances (one per AFRINIC member). **PDNS_API_PORT** is the starting API HTTP port for all signer instances (one per AFRINIC member). Those numbers can be changed, but note that the `stack_api` is listening on port `5005` and the local registry on port `5000`.

**FOLDER_PATH** is used by the `stack_api` to store generated **docker-compose.yml** file.

**ENV_BASE_FILE** is the environment template file that is used to generate custom and unique **.env**. This **.env** file will be read by corresponding **docker-compose.yml** file.

**ENV_FILE_SLAVE** store variable for MySQL slave instance (multi-source replication). See parameters bellow.

**COMPOSE_BASE_FILE** is the template that is used to generate custom and unique **docker-compose.yml** file per AFRINIC member while deploying their DNSSEC signing stack. The **docker-compose.yml** file name is predefined with **COMPOSE_FILE** variable.

The API base url is dedinied in **API_BASE**. This base url can be changed which different version of the `stack_api`.

**TOKEN** is the HTTP authentication header to protect access to the `stack_api`.

**APP_ENV** is related to Flask deployment mode.

**WORKER_NODE** is used to set PDNS host.

5. Update environment variables in management for MySQL replication
```
vim roles/manager/files/management/.env_slave

SERVER_ID=4294967290
MYSQL_ROOT_PASSWORD=<random_string>
MYSQL_ROOT_HOST=%
FOLDER_PATH=/data/stack/
```
We allow authenticated root user to access the slave database without any restriction. Note that MySQL port `3306` is not open to external. We give highest **SERVER_ID** to the MySQL slave instance.

---
**NOTE**

We use a seperate environment file for MySQL slave instance to avoid variable name conflicts. MySQL image is waiting for variables like **SERVER_ID**, **MYSQL_ROOT_PASSWORD**, **MYSQL_ROOT_HOST**, etc and it is not possible to assign two different value to the same variable (used by master and slave instances).

---

6. Run the playbook
```
ansible-playbook stack.yml
```
7. Test if docker client it running
```
curl -s -k -L  -X POST -H 'X-Auth-Token: TOKEN'  https://<swarm_manager_ip_or_fqdn>/api/v1/docker

{
  "error": null,
  "output": "Docker version 19.03.1, build 74b1e89e8a\n",
  "status": "OK"
}

```
8. Test `stack_api`
```
curl -s -k -L  -X POST -H 'X-Auth-Token: TOKEN'  https://<swarm_manager_ip_or_fqdn>/api/v1/stack

{
  "error": null,
  "output": [
    "stack_api:3"
  ],
  "status": "OK"
}

```
9. You can then, create a deployment for AFRINIC member
```
curl -s -k -L -X POST -H 'X-Auth-Token: TOKEN'  https://<swarm_manager_ip_or_fqdn>/api/v1/stack/deploy/ORG-AFNC1-AFRINIC

{
  "error": null,
  "output": {
    "api_key": "Unjrbbji6howwDU",
    "api_port": 30001,
    "dns_port": 8001,
    "stack": "ORG-AFNC1-AFRINIC_S1",
    "url": "curl -v -H 'X-API-Key: Unjrbbji6howwDU' https://<swarm_manager_ip_or_fqdn>:30001/api/v1/servers/localhost"
  },
  "status": "OK"
}


curl -s -k -L -X POST -H 'X-Auth-Token: TOKEN'  https://<swarm_manager_ip_or_fqdn>/api/v1/stack/deploy/ORG-AFNC1-AFRINIC

{
  "error": "Existing",
  "output": "ORG-AFNC1-AFRINIC_S1 (ORG-AFNC1-AFRINIC) is already in stack",
  "status": "KO"
}

```
10. List of stack deployed in the swarm
```
curl -s -k -L -X POST -H 'X-Auth-Token: TOKEN'  https://<swarm_manager_ip_or_fqdn>/api/v1/stack

{
  "error": null,
  "output": [
    "ORG-AFNC1-AFRINIC_S1:2",
    "stack_api:3"
  ],
  "status": "OK"
}

```
We have the default `stack_api` with ~~`3`~~`4` services (MySQL master, MySQL slave ~~and~~, Flask API, Nginx Reverse proxy) and the new deployed customer stack `ORG-AFNC1-AFRINIC_S1` with `2` services (MySQL master and PowerDNS).

11. Get information on a AFRINIC member stack using the stack name
```
curl -s -k -L  -X POST -H 'X-Auth-Token: TOKEN'  https://<swarm_manager_ip_or_fqdn>/api/v1/stack/info/ORG-AFNC1-AFRINIC_S1

{
  "error": null,
  "output": {
    "api_key": "Unjrbbji6howwDU",
    "api_port": 30001,
    "dns_port": 8001,
    "stack": "ORG-AFNC1-AFRINIC_S1",
    "url": "curl -v -H 'X-API-Key: Unjrbbji6howwDU' http://<swarm_manager_ip_or_fqdn>:30001/api/v1/servers/localhost"
  },
  "status": "OK"
}

```
12. Check if PowerDNS API is running
```
curl -s -k -L -H 'X-API-Key: Unjrbbji6howwDU' http://<swarm_manager_ip_or_fqdn>:30001/api/v1/servers/localhost

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
curl -s -k -L -X POST -H 'X-Auth-Token: TOKEN'  https://<swarm_manager_ip_or_fqdn>/api/v1/stack/remove/ORG-AFNC1-AFRINIC_S1

{
  "error": null,
  "output": "ORG-AFNC1-AFRINIC_S1",
  "status": "OK"
}

curl -s -k -L -X POST -H 'X-Auth-Token: TOKEN'  https://<swarm_manager_ip_or_fqdn>/api/v1/stack/remove/ORG-AFNC1-AFRINIC_S1

{
  "error": "NoStack",
  "output": "Namespace 'ORG-AFNC1-AFRINIC_S1' is not on stack",
  "status": "KO"
}

```

### Next Steps ###
From step `12`, we can start using PowerDNS API. See [testing](../testing) for an implementation example.
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

### Other Configs ###
According to [Per zone settings: Domain Metadata](https://doc.powerdns.com/authoritative/domainmetadata.html), following metadata could be defined for each zone.
* PUBLISH-CDNSKEY 1
* PUBLISH-CDS 1 2 4
* ALLOW-AXFR-FROM AUTO-NS <AFRINIC_IP>
* ALSO-NOTIFY <AFRINIC_IP>:<AFRINIC_PORT>
* extra metadata with "X-"
