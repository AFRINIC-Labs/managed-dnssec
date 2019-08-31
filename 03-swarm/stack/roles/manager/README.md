Swarm Manager and Management Stack
==================================

Manager role deploy a full docker swarm (one node) with a local registry and default stack (`management stack`) that will be used to deploy AFRINIC member DNSSEC signing stack API.

Requirements
------------
* Account on remote server with sudo privilege (can ssh).
* server IP/domain in `inventory` file.
* Vault password
* Vault authentication params


Role Variables
--------------
1. managers

`ansible_ssh_user`: remote user defined in vault.

`ansible_ssh_pass`: remote user password defined in vault.

`ansible_become_pass`: `ansible_ssh_pass`

2. all

`docker_compose_version`: docker-compose version. Currently *1.24.1*.

`docker_compose_os`: docker-compose  os. Currently *Linux*.

`docker_compose_arch`: docker-compose  architecture. Currently *x86_64*.


`replication_net`: network used by all MySQL instance for multi-source replication. Current is *db_replication_net*.

`management_api`: name of the management stack. Current is *stack_api*.

`signer_api`: Management API (Flask) image name. Current is *signer-api*.

`signer_api_tag`: Management API (Flask) image tag. Current is *1.0*.

`signer_api_port`: Management API (Flask) container listen (external). Current is *5005*.

`signer_api_resources`: Management API (Flask) container resource restrictions.

  `limits`: Maximum resources utilisation.

   `cpus`: Number of maximum CPU time assigned to the container. Current is *'0.3'*.

   `memory`: Maximum memory allocated to the container. Current is *256M*

  `reservations`: Guaranteed resources utilisation.

   `cpus`: Guaranteed number CPU time assigned to the container. Current is  *'0.1'*.

   `memory`: Guaranteed memory allocated to the container. Current is *128M*.


`private_registry`: private registry IP/FQDN. Current is *registry.mdnssec.ri.mu.afrinic.net*.

`private_registry_port`: private registry http port. Current is *5000*.

`private_registry_service`: private registry service name. Current is *registry*.

`private_registry_image`: image use from docker hub to create private registry. Current is *registry:2*.

`private_registry_port_published`: private registry container exposed (external) port. Current is *5000*.

`private_registry_port_target`: private registry container listened (internal) port. Current is *5000*.

`private_registry_volume`: private registry volume to store custom images. Current is *registry_data*.

`private_registry_resources`: Private registry container resource restrictions.

  `limits`: Maximum resources utilisation.

  `cpus`: Number of maximum CPU time assigned to the container. Current is *'0.5'*.

   `memory`: Maximum memory allocated to the container. Current is *128M*.

  `reservations`: Guaranteed resources utilisation.

   `cpus`: Guaranteed number CPU time assigned to the container. Current is *'0.25'*.

   `memory`: Guaranteed memory allocated to the container. Current is *20M*.


`remote_dst_path`: Folder where project data will be copied. Current is *"/home/{{ ansible_ssh_user }}"*.

`mysql_server_master`: MySQL (master) image name. Current is *mysql-master57*.

`mysql_server_master_tag`: MySQL (master) image tag. Current is *1.0*.

`mysql_server_master_resources`: MySQL (master) container resource restrictions.

  `limits`: Maximum resources utilisation.

   `cpus`: Number of maximum CPU time assigned to the container. Current is *'0.5'*

   `memory`: Maximum memory allocated to the container. Current is *256M*.

  `reservations`: Guaranteed resources utilisation.

   `cpus`: Guaranteed number CPU time assigned to the container. Current is *'0.25'*

   `memory`: Guaranteed memory allocated to the container. Current is *128M*.

`mysql_server_slave`: MySQL (slave) image name. Current is *mysql-slave57*.

`mysql_server_slave_tag`: MySQL (slave) image tag. Current is  *1.0*.

`mysql_server_slave_resources`: MySQL (slave) container resource restrictions.

  `limits`: Maximum resources utilisation.

   `cpus`: Number of maximum CPU time assigned to the container. Current is *'1.0'*.

   `memory`: Maximum memory allocated to the container. Current is *512M*

  `reservations`: Guaranteed resources utilisation.

   `cpus`: Guaranteed number CPU time assigned to the container. Current is *'0.5'*

   `memory`: Guaranteed memory allocated to the container. Current is *256M*

`pdns_api`: PowerDNS image name. Current is *pdns42*.

`pdns_api_tag`: PowerDNS image tag. Current is *1.0*.

`pdns_common_resources`: PowerDNS container resource restrictions on **member stack**.

  `limits`: Maximum resources utilisation.

   `cpus`: Number of maximum CPU time assigned to the container. Current is *'0.2'*.

   `memory`: Maximum memory allocated to the container. Current is *256M*.

  `reservations`: Guaranteed resources utilisation.

   `cpus`: Guaranteed number CPU time assigned to the container. Current is *'0.1'*.

   `memory`: Guaranteed memory allocated to the container. Current is *128M*.

`mysql_server_common_resources`: MySQL container resource restrictions on **member stack**.

  `limits`: Maximum resources utilisation.

   `cpus`: Number of maximum CPU time assigned to the container. Current is *'0.3'*.

   `memory`: Maximum memory allocated to the container. Current is *512M*.

  `reservations`: Guaranteed resources utilisation.

   `cpus`: Guaranteed number CPU time assigned to the container. Current is *'0.1'*.

   `memory`: Guaranteed memory allocated to the container. Current is *256M*.


Dependencies
------------
None

Example Playbook
----------------

Usage example:

    - hosts: all
      gather_facts: true
      roles:
        - role: manager

License
-------

BSD

Author Information
------------------

Alfred Arouna