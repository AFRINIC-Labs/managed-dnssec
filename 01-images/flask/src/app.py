from flask import Flask
from flask import request
from flask import jsonify
import datetime
import os

import utils
import hit


from kubernetes import client, config
from kubernetes.client import Configuration
from kubernetes.client.apis import core_v1_api
from kubernetes.client.rest import ApiException
from kubernetes.stream import stream

startTime = datetime.datetime.now().strftime("%Y-%b-%d %H:%M:%S")

app = Flask(__name__)

result = []

@app.route("/")
def index() :
    return "Api:200"

@app.route("/info")
def show_details() :
    global startTime
    return "<html>" + \
            "<head><title>Docker + Flask Demo</title></head>" + \
            "<body>" + \
            "<table>" + \
            "<tr><td> Start Time </td> <td>" +  startTime + "</td> </tr>" \
            "<tr><td> Hostname </td> <td>" + utils.gethostname() + "</td> </tr>" \
            "<tr><td> Local Address </td> <td>" + utils.getlocaladdress() + "</td> </tr>" \
            "<tr><td> Remote Address </td> <td>" + request.remote_addr + "</td> </tr>" \
            "<tr><td> Server Hit </td> <td>" + str(hit.getServerHitCount()) + "</td> </tr>" \
            "</table>" + \
            "</body>" + \
            "</html>"


@app.route("/json")
def send_json() :
    global startTime
    return jsonify( {'StartTime' : startTime,
                     'Hostname': utils.gethostname(),
                     'LocalAddress': utils.getlocaladdress(),
                     'RemoteAddress':  request.remote_addr,
                     'Server Hit': str(hit.getServerHitCount())} )


@app.route("/k8s/<namespace>")
def get_k8s_pod(namespace) :
    try:
        # Configs can be set in Configuration class directly or using helper utility
        #config.load_kube_config()
        config.load_incluster_config()

        ns = 'customer-01'
        v1 = client.CoreV1Api()
        print("Listing pods with their IPs:")
        #ret = v1.list_pod_for_all_namespaces(watch=False)
        ret = v1.list_namespaced_pod(namespace, watch=False)

        for i in ret.items:
            #print("%s\t%s\t%s" % (i.status.pod_ip, i.metadata.namespace, i.metadata.name))
            #result.append("%s\t%s\t%s" % (i.status.pod_ip, i.metadata.namespace, i.metadata.name))
            result.append(i.metadata.name)
        #ret = v1.connect_get_namespaced_pod_exec(result[0], ns, command="ods-enforcer key list -v", container="signer")
        return jsonify( {'result':  result})
    except Exception as e:
        raise e

# Doc for CoreV1Api
# https://github.com/kubernetes-client/python/blob/master/kubernetes/docs/CoreV1Api.md

@app.route("/k8s/exec")
def get_k8s_exec_once() :
    try:
        # Configs can be set in Configuration class directly or using helper utility
        config.load_incluster_config()

        #config.load_kube_config()
        c = Configuration()
        c.assert_hostname = False
        Configuration.set_default(c)
        api = core_v1_api.CoreV1Api()

        # For Minikube issue as explained on link below
        # https://stackoverflow.com/questions/54050504/running-connect-get-namespaced-pod-exec-using-kubernetes-client-corev1api-give)
        #configuration.assert_hostname = False

        # Stream is required for exec...according to:
        # https://stackoverflow.com/questions/49250370/kubernetes-pod-exec-api-upgrade-request-required


        ns = 'customer-01'
        exec_command=['/bin/sh', '-c','ods-enforcer key list -v']
        resp = stream(api.connect_get_namespaced_pod_exec, result[0], ns,
              command=exec_command,
              container="signer",
              stderr=True, stdin=False,
              stdout=True, tty=False)
        return jsonify( {"exec": resp, 'result':  result})
    except ApiException as e:
        raise  e


@app.route("/k8s/exec/<namespace>/<cmd>")
def get_k8s_exec_cmd(namespace, cmd, zone=None, policy=None) :
    try:
        # Configs can be set in Configuration class directly or using helper utility
        config.load_incluster_config()

        #config.load_kube_config()
        c = Configuration()
        c.assert_hostname = False
        Configuration.set_default(c)
        api = core_v1_api.CoreV1Api()

        # For Minikube issue as explained on link below
        # https://stackoverflow.com/questions/54050504/running-connect-get-namespaced-pod-exec-using-kubernetes-client-corev1api-give)
        #configuration.assert_hostname = False

        # Stream is required for exec...according to:
        # https://stackoverflow.com/questions/49250370/kubernetes-pod-exec-api-upgrade-request-required

        opendnssec_container = "signer"
        zone=""
        policy=""

        if cmd == "sign":
            zone = request.args.get('zone')
            if not zone:
                return jsonify( {"Error": 'No zone for signing! '})
            policy = request.args.get('policy')
            if not policy:
                return jsonify( {"Error": 'No policy for signing! '})

        commands = {
            "test": "ods-enforcer key list -v",
            "status": "ods-enforcer running",
            "sign": "ods-enforcer zone add -z " + zone + " -p " + policy +" -j DNS -q DNS --xml -i /etc/opendnssec/addns.xml -o /etc/opendnssec/addns.xml"
        }

        # Get pods
        pod_name_start = "dnssec-deployment-" + namespace
        pod = ""
        ret = api.list_namespaced_pod(namespace, watch=False)
        pods = [ i.metadata.name for i in ret.items]
        for p in pods:
            if p.startswith(pod_name_start):
                pod = p 
                break
        if not pod:
            return jsonify( {"Error": 'No Pod starting by '+pod_name_start, 'details':  ret})

        if cmd in commands:
            command = commands[cmd]
        else:
            command = "ods-enforcer running"

        exec_command=['/bin/sh', '-c',command ]
        resp = stream(api.connect_get_namespaced_pod_exec, pod, namespace,
              command=exec_command,
              container=opendnssec_container,
              stderr=True, stdin=False,
              stdout=True, tty=False)
        return resp
    except ApiException as e:
        raise  e


if __name__ == "__main__":
    app.run(debug = True, host = '0.0.0.0')