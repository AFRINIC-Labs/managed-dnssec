from urllib.parse import urljoin
import json
import requests
import logging as logger
from urllib.parse import urlparse

import os


logging = logger.getLogger(__name__)

API_BASE = os.environ.get('API_BASE', 'mdnssec.ri.mu.afrinic.net')
API_PORT = os.environ.get('API_PORT', '30001')
API_URL= 'http://' + API_BASE + ':' + API_PORT + '/'
API_VERSION='api/v1/servers/localhost'
API_KEY=os.environ.get('API_KEY', 'nyo8pUoxZb1AzkD')
MEMBER_IP=os.environ.get('MEMBER_IP', '196.192.112.222')
DS_FILES_FOLDER="data"
headers = {}
headers['X-API-Key'] = API_KEY

# https://github.com/ngoduykhanh/PowerDNS-Admin/blob/master/app/lib/utils.py
def auth_from_url(url):
    auth = None
    parsed_url = urlparse(url).netloc
    if '@' in parsed_url:
        auth = parsed_url.split('@')[0].split(':')
        auth = requests.auth.HTTPBasicAuth(auth[0], auth[1])
    return auth

# https://github.com/ngoduykhanh/PowerDNS-Admin/blob/master/app/lib/utils.py
TIMEOUT = 10
def fetch_remote(remote_url, method='GET', data=None, accept=None, params=None, timeout=None, headers=None):
    if data is not None and type(data) != str:
        data = json.dumps(data)

    if timeout is None:
        timeout = TIMEOUT

    verify = False

    our_headers = {
        'user-agent': 'managed-dnssec/0',
        'pragma': 'no-cache',
        'cache-control': 'no-cache'
    }
    if accept is not None:
        our_headers['accept'] = accept
    if headers is not None:
        our_headers.update(headers)

    r = requests.request(
        method,
        remote_url,
        headers=headers,
        verify=verify,
        auth=auth_from_url(remote_url),
        timeout=timeout,
        data=data,
        params=params
        )
    try:
        if r.status_code not in (200, 201, 204, 400, 422, 404):
            r.raise_for_status()
    except Exception as e:
        msg = "Returned status {0} and content {1}"
        logging.error(msg.format(r.status_code, r.content))
        raise RuntimeError('Error while fetching {0}'.format(remote_url))

    return r

# https://github.com/ngoduykhanh/PowerDNS-Admin/blob/master/app/lib/utils.py
def fetch_json(remote_url, method='GET', data=None, params=None, headers=None):
    r = fetch_remote(remote_url, method=method, data=data, params=params, headers=headers,
                     accept='application/json; q=1')

    if method == "DELETE":
        return True

    if r.status_code == 204 or r.status_code == 404:
        return {}

    if remote_url.endswith('export'):
        data = r.content.decode('utf-8')
    else:
        try:
            assert('json' in r.headers['content-type'])
        except Exception as e:
            raise RuntimeError('Error while fetching {0}'.format(remote_url)) from e

        # don't use r.json here, as it will read from r.text, which will trigger
        # content encoding auto-detection in almost all cases, WHICH IS EXTREMELY
        # SLOOOOOOOOOOOOOOOOOOOOOOW. just don't.
        data = None
        try:
            data = json.loads(r.content.decode('utf-8'))
        except Exception as e:
            raise RuntimeError('Error while loading JSON data from {0}'.format(remote_url)) from e
    return data




def create_tsig(name, algorithm="hmac-sha256", key=None):
    try:
        post_data = {
            "name": name,
            "algorithm": algorithm
        }
        if key:
            post_data["key"] = key
        data = fetch_json(urljoin(API_URL,API_VERSION) + '/tsigkeys', headers=headers, method='POST', data=post_data)
        if 'error' in data:
            return {'status': 'error', 'msg': 'Cannot create TSIG key: ' + str(data)}
        return {'status': 'ok', 'data': data}
    except Exception as e:
        return {'status': 'error', 'msg': str(e) }

def create_slave_zone(domain, tsigkey_id, master):
    try:
        post_data = {
            "name": domain + ".",
            "kind": "Slave",
            "slave_tsig_key_ids": [tsigkey_id],
            "masters": [master],
            "api_rectify": False,
        }

        data = fetch_json(urljoin(API_URL,API_VERSION) + '/zones', headers=headers, method='POST', data=post_data)
        if 'error' in data:
            return {'status': 'error', 'msg': 'Cannot create slave zone: ' + str(data)}
        return {'status': 'ok', 'data': data}
    except Exception as e:
        return {'status': 'error', 'msg': str(e) }

def check_axfr(zone):
    try:
        # Check if zone exists
        data = fetch_json(urljoin(API_URL,API_VERSION) + '/zones/{0}'.format(zone), headers=headers, method='GET')
        if 'error' in data:
            return {'status': 'error', 'msg': 'Cannot get slave zone on server: ' + str(data)}
        # Get all the MetaData associated with the zone
        data = fetch_json(urljoin(API_URL,API_VERSION) + '/zones/{0}/metadata'.format(zone), headers=headers, method='GET')
        if 'error' in data:
            return {'status': 'error', 'msg': 'Cannot get slave zone metadata: ' + str(data)}
        # Retrieve slave zone from its master
        data = fetch_json(urljoin(API_URL,API_VERSION) + '/zones/{0}/axfr-retrieve'.format(zone), headers=headers, method='PUT')
        if 'error' in data:
            return {'status': 'error', 'msg': 'Cannot retrieve slave zone from its master: ' + str(data)}
        # Returns the zone in AXFR format
        data = fetch_json(urljoin(API_URL,API_VERSION) + '/zones/{0}/export'.format(zone), headers=headers, method='GET')
        if 'error' in data:
            return {'status': 'error', 'msg': 'Cannot the zone in AXFR format: ' + str(data)}

        return {'status': 'ok', 'data': data}
    except Exception as e:
        return {'status': 'error', 'msg': str(e) }

def set_master(zone, tsigkey):
    try:
        # Check if zone is Master
        data = fetch_json(urljoin(API_URL,API_VERSION) + '/zones/{0}'.format(zone), headers=headers, method='GET')
        if 'error' in data:
            return {'status': 'error', 'msg': 'Could not check if zone '+zone+' is Master'}
        else:
            if data['kind'] != 'Master':
                # Set Zone to Master
                post_data = {
                    "kind": "Master",
                    "master_tsig_key_ids": [tsigkey],
                    "api_rectify": True
                }
                data = fetch_json(urljoin(API_URL,API_VERSION) + '/zones/{0}'.format(zone), headers=headers, method='PUT', data=post_data)
                if 'error' in data:
                    return {'status': 'error', 'msg': 'Zone '+zone+' could not be change to Master', 'data': data}
                else:
                    return {'status': 'ok', 'data': data}
            else:
                return {'status': 'ok', 'data': data}
    except Exception as e:
        return {'status': 'error', 'msg': str(e) }

def create_cryptokeys(zone, keytype, algorithm, active, bit):
    try:
        post_data = {
            "keytype": keytype,
            "active": active,
            "algorithm": algorithm,
            "bits": bit
        }
        data = fetch_json(urljoin(API_URL,API_VERSION) +'/zones/{0}/cryptokeys'.format(zone), headers=headers, method='POST', data=post_data)
        if 'error' in data:
            return {'status': 'error', 'msg': 'Cannot add ' + keytype + ' to zone: ' + zone, 'detail': data}
    except Exception as e:
        return {'status': 'error', 'msg': str(e) }

def set_nsec3(zone):
    try:
        # Update DNSSEC NSEC3PARAM
        post_data = {
            "nsec3param": "1 0 5 ab",
            "nsec3narrow": False,
            "dnssec": True
        }
        data = fetch_json(urljoin(API_URL,API_VERSION)  + '/zones/{0}'.format(zone), headers=headers, method='PUT', data=post_data)
        if 'error' in data:
            return {'status': 'error', 'msg': 'Cannot enable DNSSEC for domain '+zone+'. Error: {0}'.format(data['error']), 'data': data}
        else:
            return {'status': 'ok', 'data': data}
    except Exception as e:
        return {'status': 'error', 'msg': str(e) }

def get_ds(zone):
    try:
        data = fetch_json(urljoin(API_URL,API_VERSION)  + '/zones/{0}/cryptokeys'.format(zone), headers=headers, method='GET')
        if 'error' in data:
            return {'status': 'error', 'msg': 'Cannot get DS for domain '+zone+'. Error: {0}'.format(data['error']), 'data': data}
        else:
            for key in data:
                if key["keytype"] == "ksk" and key["active"]:
                    dsset = key["ds"]
                    print(dsset)
                    if dsset:
                        file = open(DS_FILES_FOLDER + "/dsset-"+zone, "w")
                        for ds in dsset:
                            print(ds)
                            file.write(zone + ". IN DS " + ds + "\n")
                        file.close()
                        return {'status': 'ok', 'data': key["ds"]}
                    else:
                        return {'status': 'error', 'msg': 'No DS in '+ str(dsset)}
    except Exception as e:
        return {'status': 'error', 'msg': str(e) }

def publish_child_dnssec(zone, type):
    try:
        post_data = {}
        if type == "cds":
            post_data['kind'] = "PUBLISH-CDS"
            post_data['metadata'] = ["1","2","4"]
        elif type == "cdnskey":
            post_data['kind'] = "PUBLISH-CDNSKEY"
            post_data['metadata'] = ["1"]
        data = fetch_json(urljoin(API_URL,API_VERSION)  + '/zones/{0}/metadata'.format(zone), headers=headers, method='POST', data=post_data)
        if 'error' in data:
            return {'status': 'error', 'msg': 'Cannot publish '+type+' for zone '+ zone +'. Error: {0}'.format(data['error']), 'data': data}
        return {'status': 'ok', 'data': str(data)}
    except Exception as e:
        return {'status': 'error', 'msg': str(e) }

"""
dig +short @196.192.112.222  nsd.tld soa                                                                                                                           ✔  10547  22:56:14
ns1.nsd.tld. hostmaster.nsd.tld. 2019080201 7200 3600 604800 43200
dig +short @196.192.112.222 pdns.tld soa                                                                                                                          ✔  10548  22:56:23
ns1.pdns.tld. hostmaster.pdns.tld. 2019080201 7200 3600 604800 43200
dig +short @196.192.112.222 bind.tld soa                                                                                                                          ✔  10549  22:56:31
ns1.bind.tld. hostmaster.bind.tld. 2019061102 7200 3600 604800 43200

dig +short @196.192.112.222 -p 530 bind.tld soa
"""

## Slaves Mode
tsigkey = create_tsig("nsd_slave", "hmac-sha256", "TlNEX1RTSUdfU0VDUkVUX0tFWQo=")
print(tsigkey)
if tsigkey['status'] == 'ok' and tsigkey["data"]["id"]:
    nsd_tld = create_slave_zone("nsd.tld", tsigkey["data"]["id"], MEMBER_IP)
    print(nsd_tld)
    if nsd_tld['status'] == 'ok' and nsd_tld["data"]["name"]:
        nsd_data = check_axfr(nsd_tld["data"]["name"])
        print(nsd_data)

tsigkey = create_tsig("bind_slave", "hmac-sha256", "QklORF9UU0lHX1NFQ1JFVF9LRVkK")
print(tsigkey)
if tsigkey['status'] == 'ok' and tsigkey["data"]["id"]:
    nsd_tld = create_slave_zone("bind.tld", tsigkey["data"]["id"], MEMBER_IP)
    print(nsd_tld)
    if nsd_tld['status'] == 'ok' and nsd_tld["data"]["name"]:
        nsd_data = check_axfr(nsd_tld["data"]["name"])
        print(nsd_data)

tsigkey = create_tsig("pdns_slave", "hmac-sha256", "cG93ZXJkbnNfc2VydmVyCg==")
print(tsigkey)
if tsigkey['status'] == 'ok' and tsigkey["data"]["id"]:
    nsd_tld = create_slave_zone("pdns.tld", tsigkey["data"]["id"], MEMBER_IP)
    print(nsd_tld)
    if nsd_tld['status'] == 'ok' and nsd_tld["data"]["name"]:
        nsd_data = check_axfr(nsd_tld["data"]["name"])
        print(nsd_data)

## Master mode
tsigkey = create_tsig("nsd_master", "hmac-sha256", "bmRzcGRuc21hc3Rlcgo=")
print(tsigkey)
if tsigkey['status'] == 'ok' and tsigkey["data"]["id"]:
    nsd_master = set_master("nsd.tld", tsigkey["data"]["id"])
    print(nsd_master)
    nsd_signed_ksk = create_cryptokeys("nsd.tld", "ksk", "rsasha512", True, 2048)
    print(nsd_signed_ksk)
    nsd_signed_zsk = create_cryptokeys("nsd.tld", "zsk", "rsasha512", True, 1024)
    print(nsd_signed_zsk)
    nsec3 = set_nsec3("nsd.tld")
    print(nsec3)
    ds = get_ds("nsd.tld")
    print(ds)

tsigkey = create_tsig("bind_master", "hmac-sha256", "YmluZG1hc3Rlcgo=")
print(tsigkey)
if tsigkey['status'] == 'ok' and tsigkey["data"]["id"]:
    bind_master = set_master("bind.tld", tsigkey["data"]["id"])
    print(bind_master)
    bind_signed_ksk = create_cryptokeys("bind.tld", "ksk", "rsasha512", True, 2048)
    print(bind_signed_ksk)
    bind_signed_zsk = create_cryptokeys("bind.tld", "zsk", "rsasha512", True, 1024)
    print(bind_signed_zsk)
    nsec3 = set_nsec3("bind.tld")
    print(nsec3)
    ds = get_ds("bind.tld")
    print(ds)

tsigkey = create_tsig("pdns_master", "hmac-sha256", "cGRuc3NsYXZla25vdAo=")
print(tsigkey)
if tsigkey['status'] == 'ok' and tsigkey["data"]["id"]:
    pdns_master = set_master("pdns.tld", tsigkey["data"]["id"])
    print(pdns_master)
    pdns_signed_ksk = create_cryptokeys("pdns.tld", "ksk", "rsasha512", True, 2048)
    print(pdns_signed_ksk)
    pdns_signed_zsk = create_cryptokeys("pdns.tld", "zsk", "rsasha512", True, 1024)
    print(pdns_signed_zsk)
    nsec3 = set_nsec3("pdns.tld")
    print(nsec3)
    ds = get_ds("pdns.tld")
    print(ds)