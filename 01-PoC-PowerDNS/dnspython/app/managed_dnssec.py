#!/usr/bin/env python

from __future__ import print_function

import dns.query
import dns.resolver
import dns.zone
import dns.tsigkeyring

from urllib.parse import urljoin
import json
import requests
import logging as logger
from urllib.parse import urlparse

import os


logging = logger.getLogger(__name__)


API_URL='http://'+ os.environ['PDNS_MASTER_ADDRESS'] +':8081'
API_VERSION='api/v1/servers/localhost'
API_KEY=os.environ['PDNS_API_KEY']
headers = {}
headers['X-API-Key'] = API_KEY

master_tsigkeys = {
    "nsd.tld": {
        "name": "nsd_master_key",
        "algorithm": "hmac-sha256",
        "key": "TkRTX01BU1RFUl9UU0lHX0tFWQo=",
        "id": "nsd_master_key."
    },
    "bind.tld": {
        "name": "bind_master_key",
        "algorithm": "hmac-sha256",
        "key": "QklORF9NQVNURVJfVFNJR19LRVkK",
        "id": "bind_master_key."
    }
}

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

# Get zones
def get_zones():
    try:
        data = fetch_json(urljoin(API_URL,API_VERSION) + '/zones', headers=headers, method='GET')
        #data = fetch_json(API_URL+ '/zones', headers=headers, method='GET')
        if 'error' in data:
            return {'status': 'error', 'msg': 'Cannot get zones list'}
        else:
            zones = [d['name'].rstrip('.') for d in data]
            return {'status': 'ok', 'data': zones}
    except Exception as e:
        return {'status': 'error', 'msg': str(e) }

def get_zone_info(zone):
    try:
        data = fetch_json(urljoin(API_URL,API_VERSION) + '/zones/{0}'.format(zone), headers=headers, method='GET')
        if 'error' in data:
            return {'status': 'error', 'msg': 'Cannot get zone info'}
        else:
            return {'status': 'ok', 'data': data}
    except Exception as e:
        return {'status': 'error', 'msg': str(e) }

def get_zone_metadata(zone):
    try:
        data = fetch_json(urljoin(API_URL,API_VERSION) + '/zones/{0}/metadata'.format(zone), headers=headers, method='GET')
        if 'error' in data:
            return {'status': 'error', 'msg': 'Cannot get zone metadata'}
        else:
            return {'status': 'ok', 'data': data}
    except Exception as e:
        return {'status': 'error', 'msg': str(e) }

def get_zone_data(zone):
    try:
        data = fetch_json(urljoin(API_URL,API_VERSION) + '/zones/{0}/export'.format(zone), headers=headers, method='GET')
        if 'error' in data:
            return {'status': 'error', 'msg': 'Cannot get zone records'}
        else:
            return {'status': 'ok', 'data': data}
    except Exception as e:
        return {'status': 'error', 'msg': str(e) }

def get_zone_dnssec(zone):
    try:
        data = fetch_json(urljoin(API_URL,API_VERSION) + '/zones/{0}/cryptokeys'.format(zone), headers=headers, method='GET')
        if 'error' in data:
            return {'status': 'error', 'msg': 'Cannot get zone dnssec status'}
        else:
            return {'status': 'ok', 'data': data}
    except Exception as e:
        return {'status': 'error', 'msg': str(e) }

def set_master_zone(zone):
    try:
        # Check if zone is Master
        data = fetch_json(urljoin(API_URL,API_VERSION) + '/zones/{0}'.format(zone), headers=headers, method='GET')
        if 'error' in data:
            return {'status': 'error', 'msg': 'Could not check if zone '+zone+' is Master'}
        else:
            if data['kind'] != 'Master': 
            #Enable API-RECTIFY for domain, BEFORE activating DNSSEC
                post_data = {
                    "api_rectify": True
                }
                data = fetch_json(urljoin(API_URL,API_VERSION) + '/zones/{0}'.format(zone), headers=headers, method='PUT', data=post_data)
                if 'error' in data:
                    return {'status': 'error', 'msg': 'API-RECTIFY could not be enabled for domain '+zone, 'data': data} 
                # Set Zone to Master
                post_data = {
                    "kind": "Master"
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

def create_axfr_tsig(zone):
    try:
        # Check if metadata exist
        data = fetch_json(urljoin(API_URL,API_VERSION) + '/tsigkeys/{0}'.format(master_tsigkeys[zone]['id']), headers=headers, method='GET')
        if 'error' in data:
            return {'status': 'error', 'msg': 'Could not check tsigkeys for '+zone, 'data': data}
        else:
            if 'id' not in data:
                # Create tsigkey
                data = fetch_json(urljoin(API_URL,API_VERSION) + '/tsigkeys', headers=headers, method='POST', data=master_tsigkeys[zone])
                if 'error' in data:
                    return {'status': 'error', 'msg': 'Impossible to create tsigkeys for '+zone, 'data': data}
                else:
                    return {'status': 'ok', 'data': data}
            else:
                return {'status': 'ok', 'data': data}
    except Exception as e:
        return {'status': 'error', 'msg': str(e) }

def set_axfr_tsig(zone):
    try:
        # Check if tsigkey is assign to zone
        data = fetch_json(urljoin(API_URL,API_VERSION) + '/zones/{0}/metadata/TSIG-ALLOW-AXFR'.format(zone), headers=headers, method='GET')
        if 'error' in data:
            return {'status': 'error', 'msg': 'Impossible to check tsigkeys for '+zone, 'data': data}
        else:
            if len(data['metadata']) == 0:
                # # Add tsigkey
                # post_data = {
                #     "kind": "TSIG-ALLOW-AXFR",
                #     "metadata" : master_tsigkeys[zone]['name']
                # }
                # data = fetch_json(urljoin(API_URL,API_VERSION) + '/zones/{0}/metadata'.format(zone), headers=headers, method='POST', data=post_data)
                post_data = {
                    "master_tsig_key_ids": [master_tsigkeys[zone]['id']]
                }
                data = fetch_json(urljoin(API_URL,API_VERSION) + '/zones/{0}'.format(zone), headers=headers, method='PUT', data=post_data)
                if 'error' in data:
                    return {'status': 'error', 'msg': 'Impossible to add tsigkeys for '+zone, 'data': data}
                else:
                    return {'status': 'ok', 'data': data}
            else:
                return {'status': 'ok', 'data': data}
    except Exception as e:
        return {'status': 'error', 'msg': str(e) }

def enable_dnssec(zone):
    try:
        print('Setting zone to Master...')
        master_zone = set_master_zone(zone)
        if master_zone['status'] == 'ok':
            print('Creating Master tsig key...')
            tsig_axfr = create_axfr_tsig(zone)
            if tsig_axfr['status'] == 'ok':
                print('Attaching Master tsig to zone...')
                axfr_tsig = set_axfr_tsig(zone)
                if axfr_tsig['status'] != 'ok':
                    return {'status': 'error', 'msg': 'Impossible to prepare zone '+zone+' for DNSSEC signing: Attaching Master tsig to zone.', 'data': axfr_tsig['msg']}
            else:
                return {'status': 'error', 'msg': 'Impossible to prepare zone '+zone+' for DNSSEC signing: Creating Master tsig key.', 'data': tsig_axfr['msg'] }
        else:
            return {'status': 'error', 'msg': 'Impossible to prepare zone '+zone+' for DNSSEC signing: Setting zone to Master.', 'data': master_zone['msg'] }

        # Activate DNSSEC
        post_data = {
             "active": True,
             "keytype": "ksk",
             "algo": "RSASHA1"
        }
        data = fetch_json(urljoin(API_URL,API_VERSION)  + '/zones/{0}/cryptokeys'.format(zone), headers=headers, method='POST', data=post_data)
        if 'error' in data:
            return {'status': 'error', 'msg': 'Cannot enable DNSSEC for domain '+zone+'. Error: {0}'.format(data['error']), 'data': data}
        else:
            return {'status': 'ok', 'data': data}
    except Exception as e:
        return {'status': 'error', 'msg': str(e) }


def get_sign_zone(zone):
    try:
        keyring = dns.tsigkeyring.from_text({
            master_tsigkeys[zone]['id'] : master_tsigkeys[zone]['key']
        })
        keyalgorithm = master_tsigkeys[zone]['algorithm']

        z = dns.zone.from_xfr(dns.query.xfr(os.environ['PDNS_MASTER_ADDRESS'], zone, keyring=keyring, keyalgorithm=keyalgorithm))
        #z.to_file(zone)
        #for n in sorted(z.nodes.keys()):
        for n in z.nodes.keys():
            print(z[n].to_text(n))
        print(ZONE_TPL.format(
            domainname=zone,
            serial=datetime.datetime.now().strftime('%Y%m%d01'),
        ))
    except Exception as e:
        return {'status': 'error', 'msg': str(e) }

zones_data = get_zones()
zi = zm = zd = False
if zones_data['status'] == 'ok':
    zones = zones_data['data']
    for z in zones:
        print("Zone {0}".format(z))
        z_info = get_zone_info(z)
        if z_info['status'] == 'ok':
            zi = True
            print("=== Zone Infos "+ "*" * 30)
            for d in z_info['data']:
                if d == 'rrsets':
                    continue
                print("{0} : {1}".format(d,z_info['data'][d]))
        z_meta = get_zone_metadata(z)
        if z_meta['status'] == 'ok':
            zm = True
            print("=== Zone Metadata "+ "*" * 30)
            print(z_meta['data'])
        z_record = get_zone_data(z)
        if z_record['status'] == 'ok':
            zd = True
            print("=== Unsigned zone "+ "*" * 30)
            print(z_record['data'])

if zi is True and zm is True and zd is True:
    print("=== Select which zone to sign."+ "*" * 30)
    zones = zones_data['data']
    for z in zones:
        print("Id: {0}: {1}".format(zones.index(z)+1, z))
    while True:
        print("\nSelect your domain Id or type q to exit.")
        choice = input("\nEnter your choice: ")
        if choice == 'q' or choice == 'Q':
            break
        elif int(choice) > len(zones):
            print("#"*30)
            print("Invalid domain Id")
            print("#"*30)
        else:
            print(zones[int(choice)-1])
            dnssec_status = get_zone_dnssec(zones[int(choice)-1])
            if dnssec_status['status'] == 'ok':
                if len(dnssec_status['data']) == 0:
                    print("#"*30)
                    print("No DNSSEC key for {0}".format(zones[int(choice)-1]))
                    print("#"*30)
                    sign = input("\nEnter YES|yes to sign this domain: ")
                    if sign == 'YES' or sign == 'yes' or sign == 'y':
                        signing = enable_dnssec(zones[int(choice)-1])
                        print(signing)
                else:
                    print("#"*30)
                    print("Available DNSSEC Key(s) for {0}".format(zones[int(choice)-1]))
                    print(dnssec_status['data'])
                    print("#"*30)
                    print("")
                    print("=== Signed zone "+ "*" * 30)
                    signed = get_sign_zone(zones[int(choice)-1])
                    print(signed)


