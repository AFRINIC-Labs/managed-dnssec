from flask import Flask
from flask import request
from flask import jsonify
from flask import escape
from functools import wraps
from flask import url_for
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import text

# Utilities
import socket
import time
import datetime
import os
import subprocess
import logging

# Compose utils
from compose.cli.utils import get_version_info
from compose.config.environment import Environment
from compose.cli.command import get_project,get_config_path_from_options,get_project_name,get_config_from_options
from compose.service import BuildAction, ImageType
import docker


# error handling
from werkzeug.exceptions import default_exceptions

# Url prefix
#from werkzeug.wsgi import DispatcherMiddleware
from werkzeug.middleware.dispatcher import DispatcherMiddleware

# https://gist.github.com/svieira/3434cbcaf627e50a4808
from werkzeug.serving import run_simple

# https://stackoverflow.com/questions/29332056/global-error-handler-for-any-exception
from werkzeug.exceptions import HTTPException




startTime = datetime.datetime.now().strftime("%Y-%b-%d %H:%M:%S")

PDNS_DNS_PORT = int(os.environ.get('PDNS_DNS_PORT', 8000))
PDNS_API_PORT = int(os.environ.get('PDNS_API_PORT', 30000))
FOLDER_PATH = os.environ.get('FOLDER_PATH', "/home/vagrant/stack/")
ENV_BASE_FILE = os.environ.get('ENV_BASE_FILE', "env.txt")
ENV_FILE = os.environ.get('ENV_FILE',".env")
COMPOSE_BASE_FILE = os.environ.get('COMPOSE_BASE_FILE',"docker-compose-template.yml")
COMPOSE_FILE = os.environ.get('COMPOSE_FILE', "docker-compose.yml")
API_BASE = os.environ.get('API_BASE', '/api/v1')
TOKEN = os.environ.get('TOKEN', "F17s++tlP8Ttuo+1vOTjJqqUiFTeix+yAyc1G9ByFDI")
ENV_FILE_SLAVE = os.environ.get('ENV_FILE_SLAVE',".env_slave")
REPLICATION_SERVER = os.environ.get('REPLICATION_SERVER',"mysql_replication_db")
REPLICATION_USER = os.environ.get('REPLICATION_USER',"repl_api")
REPLICATION_PASS = os.environ.get('REPLICATION_PASS',"qocUcsPQiKuhTJQnIR89b25rCm0")
SERVER_ID = os.environ.get('SERVER_ID', 4294967285)
APP_ENV = os.environ.get('APP_ENV', 'Dev')
REPLICATION_CHANNEL = os.environ.get('REPLICATION_CHANNEL', 'stack_api')

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'mysql+mysqldb://'+ os.environ.get('MYSQL_USER', 'root') + ':'+ os.environ.get('MYSQL_PASSWORD', 'toor') + '@' + os.environ.get('MYSQL_HOST', 'localhost') +'/' + os.environ.get('MYSQL_DATABASE', 'mdnssec')
# (MySQLdb._exceptions.OperationalError) (2013, 'Lost connection to MySQL server during query')
'''
SHOW GLOBAL VARIABLES LIKE "wait_timeout";
+---------------+-------+
| Variable_name | Value |
+---------------+-------+
| wait_timeout  | 28800 |
+---------------+-------+
'''
# https://flask-sqlalchemy.palletsprojects.com/en/2.x/config/#timeouts
# set SQLALCHEMY_POOL_RECYCLE to a value less than your backend’s timeout.
# Depricated as of 2.4
# app.config['SQLALCHEMY_POOL_RECYCLE'] = 10000

app.config['SQLALCHEMY_ENGINE_OPTIONS'] = {
    #"pool_recycle": 3600,
    "pool_pre_ping": True,
}


# Get replication params
def db_slave():
    MGM_FOLDER_PATH = FOLDER_PATH + '../management/'
    info = {}
    with open(MGM_FOLDER_PATH + ENV_FILE_SLAVE) as f:
        for line in f:
            (key, val) = line.strip("\n").split("=")
            info[key] = val
    if "MYSQL_ROOT_PASSWORD" not in info:
        return jsonify( {'status': 'KO', 'output': info, 'error': "MYSQL_ROOT_PASSWORD not in slave environment file" })
    return info

slave_info = db_slave()

# Connect to slave db
app.config['SQLALCHEMY_BINDS'] = {
    'slave': 'mysql+mysqldb://root:'+ slave_info['MYSQL_ROOT_PASSWORD'] + '@'+ REPLICATION_SERVER +'/'
}

app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

#https://gist.github.com/betrcode/0248f0fda894013382d7
def isOpen(ip, port, timeout):
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.settimeout(timeout)
    print("trying port "+str(port)+" on server "+str(ip))
    try:
        s.connect((ip, int(port)))
        s.shutdown(socket.SHUT_RDWR)
        return True
    except:
        return False
    finally:
        s.close()

def checkHost(ip, port, delay, timeout, retry):
    for i in range(retry):
        print("["+str(i)+"] checking port "+str(port)+" on server "+str(ip))
        if isOpen(ip, port,timeout):
            return True
        else:
            time.sleep(delay)
    return False

if checkHost(os.environ.get('MYSQL_HOST', 'localhost'), 3306, 10, 15, 10):
    db = SQLAlchemy(app)


hitCount = 0


def getServerHitCount():
    global hitCount
    hitCount = hitCount + 1
    return hitCount

class Customer(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    mysql_host = db.Column(db.String(80), nullable=False)
    mysql_db = db.Column(db.String(80), nullable=False)
    mysql_user = db.Column(db.String(80), nullable=False)
    mysql_password = db.Column(db.String(80), nullable=False)
    mysql_container = db.Column(db.String(80), unique=True, nullable=False)
    mysql_server_id = db.Column(db.Integer, unique=True, index=True, nullable=False)
    mysql_repliation_user = db.Column(db.String(80), nullable=False)
    mysql_replication_password = db.Column(db.String(80), nullable=False)
    pdns_container = db.Column(db.String(80), unique=True, nullable=False)
    pdns_volume = db.Column(db.String(80), unique=True, nullable=False)
    api_key = db.Column(db.String(80), nullable=False)
    api_port = db.Column(db.Integer, unique=True, index=True, nullable=False)
    dns_port = db.Column(db.Integer, unique=True, nullable=False)
    namespace = db.Column(db.String(80), unique=True, index=True, nullable=False)
    network = db.Column(db.String(80), unique=True, index=True, nullable=False)
    enabled = db.Column(db.Boolean, default=False, nullable=False)
    stack = db.Column(db.Boolean, default=False, nullable=False)
    created = db.Column(db.DateTime, default=datetime.datetime.utcnow, nullable=False)
    updated = db.Column(db.DateTime, default=datetime.datetime.utcnow,  onupdate=datetime.datetime.utcnow, nullable=False)
    deleted = db.Column(db.DateTime, nullable=True)

    def __repr__(self):
        return '<Customer %r>' % self.namespace

# Flask Application

logging.info(get_version_info('full'))

db.create_all(bind=None)
db.session.commit()

app.config["APPLICATION_ROOT"] = API_BASE


# https://stackoverflow.com/questions/29332056/global-error-handler-for-any-exception
@app.errorhandler(Exception)
def handle_error(e):
    code = 500
    if isinstance(e, HTTPException):
        code = e.code
    return jsonify(error=str(e)), code

# override the default HTML exceptions from Flask
# https://stackoverflow.com/questions/29332056/global-error-handler-for-any-exception
for ex in default_exceptions:
    app.register_error_handler(ex, handle_error)



@app.route("/")
def index():
    return "The URL for this page is {}".format(url_for("index"))

def simple(env, resp):
    resp(b'200 OK', [(b'Content-Type', b'text/plain')])
    return [b'Api:200']

@app.route("/info")
def send_json() :
    global startTime
    return jsonify({"error": None,
                    "output": {'StartTime' : startTime,
                        'Hostname': socket.gethostname(),
                        'LocalAddress': socket.gethostbyname(socket.gethostname()),
                        'RemoteAddress':  request.remote_addr,
                        'Server Info Hit': str(getServerHitCount())},
                    "status": "OK" })


@app.route("/docker", methods=['GET', 'POST'])
def get_docker() :
    cmd = "docker -v" 
    myCmd = cmd.split()
    execute = subprocess.Popen(myCmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    out,err = execute.communicate()
    if not err:
        return jsonify( {'status': 'OK', 'output': out.decode("utf-8"), 'error': err })
    else:
        return jsonify( {'status': 'KO', 'output': out, 'error': err })


def authenticate(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        token = request.headers.get('X-Auth-Token') 
        if not token or token != TOKEN:
            return jsonify( {'status': 'KO', 'output': None, 'error': 'Invalid or missing X-Auth-Token' })
        return f(*args, **kwargs)
    return wrapper

@app.route("/stack/deploy/<string:orgId>", methods=['POST'])
@authenticate
def stack_deploy(orgId):

    print("[stack_deploy]: Checking customer...")
    try:
        customer = Customer.query.filter(Customer.namespace.contains(orgId)).first()
        if customer and customer.stack:
            print(customer)
            print(customer.namespace)
            return jsonify( {'status': 'KO', 'error': 'Existing', 'output': str(customer.namespace) + ' (' + orgId + ') is already in stack' })
    except Exception as err:
        raise err

    print("[stack_deploy]: Stack deploy started...")
    project, namespace, api_data, repl = init_project(orgId)

    # Check if namespace is in stack
    cmd = "docker stack ls --format {{.Name}}"
    print(cmd)
    myCmd = cmd.split()
    execute = subprocess.Popen(myCmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    out,err = execute.communicate()

    stack = []
    for el in out.split():
        if el != "":
            stack.append(el.decode())


    if namespace in stack:
    #if not err:
       return jsonify( {'status': 'KO', 'error': namespace + ' is already in stack', 'output': out.decode("utf-8") })

    # Compose up --build
    # BuildAction.force or BuildAction.none
    # detached=False
    # silent=False
    compose_up_build = project.up(service_names=None, do_build=BuildAction.force, detached=True)
    #container_list = [container.name for container in compose_up_build]
    #print(container_list)
    print("[stack_deploy]: Building compose...")

    # Compose down
    # remove_image_type,include_volumes,
    compose_down = project.down(ImageType.none, True)
    #print(compose_down)
    print("[stack_deploy]: Stopping compose...")

    # Compose push
    # service_names=None, ignore_push_failures=False
    compose_push = project.push()
    #print(compose_push)
    print("[stack_deploy]: Pushing compose image to registry...")

    cmd = "docker stack deploy -c " + FOLDER_PATH + "docker-compose.yml " + namespace
    myCmd = cmd.split()
    execute = subprocess.Popen(myCmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    out,err = execute.communicate()
    print("[stack_deploy]: Running stack deploy...")

    api_data['stack'] = namespace
    api_data['url'] = "curl -v -H 'X-API-Key: " + str(api_data['api_key']) + "' http://HOST:"+ str(api_data['api_port']) +"/api/v1/servers/localhost"
    if not err:
        # Update Customer and set enable to True
        customer = Customer.query.filter_by(namespace=namespace).first()
        if customer:
            customer.stack = True
            db.session.commit()
            # Configure slave for replication
            print(repl)
            configure_slave(namespace, repl)
        return jsonify( {'status': 'OK', 'output': api_data, 'error': err })
    else:
        return jsonify( {'status': 'KO', 'output': out, 'error': err })


@app.route("/stack/remove/<string:namespace>", methods=['POST'])
@authenticate
def stack_remove(namespace):
    try:
        customer = Customer.query.filter_by(namespace=escape(namespace)).first()
        if not customer:
            return jsonify( {'status': 'KO', 'output': "Stack '" +namespace + "' not found", 'error': 'NonExisting' })
        if not customer.stack:
            return jsonify( {'status': 'KO', 'output': "Stack '" + namespace + "' is not on stack", 'error': 'NoStack' })

        print("[stack_remove]: Removing stack...")

        cmd = "docker stack remove " + namespace
        myCmd = cmd.split()
        execute = subprocess.Popen(myCmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        out,err = execute.communicate()
        print("[stack_remove]: Running stack rm...")

        if not err:
            time.sleep(10) # Wait for services to be stopped
            print(namespace + "_"  + customer.pdns_volume)
            cmd = "docker volume rm " + namespace + "_"  + customer.pdns_volume
            myCmd = cmd.split()
            execute = subprocess.Popen(myCmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
            out,err = execute.communicate()
            print("[stack_remove]: Running volume rm...")

        if not err:
            customer.stack = False
            customer.deleted = datetime.datetime.utcnow()
            db.session.commit()
            return jsonify( {'status': 'OK', 'output': namespace, 'error': err })
        else:
            return jsonify( {'status': 'KO', 'output': out, 'error': err })
    except docker.errors.APIError as err:
        if err.response.status_code == 404:
            self.log.info("[stack_remove]: " + err)
        elif err.response.status_code == 500:
            logging.info("[stack_remove]: " + err)
        else:
            raise err
    except Exception as err:
        raise err

@app.route("/stack/info/<string:namespace>", methods=['POST'])
@authenticate
def stack_info(namespace):
    try:
        customer = Customer.query.filter_by(namespace=escape(namespace)).first()
        if not customer:
            return jsonify( {'status': 'KO', 'output': "Stack '" +namespace + "' not found", 'error': 'NonExisting' })
        if not customer.stack:
            return jsonify( {'status': 'KO', 'output': "Stack '" + namespace + "' is not on stack", 'error': 'No Stack' })

        print("[stack_info]: Geting stack info...")

        cmd = "docker stack ls --format {{.Name}}"
        myCmd = cmd.split()
        execute = subprocess.Popen(myCmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        out,err = execute.communicate()
        print("[stack_info]: Listing namespaces in stack...")
        stack = []
        if not err:
            for el in out.split():
                if el != "":
                    stack.append(el.decode())
            if namespace in stack:
                data = {}
                data['api_key'] = customer.api_key
                data['api_port'] = customer.api_port
                data['dns_port'] = customer.dns_port
                data['stack'] = namespace
                data['url'] = "curl -v -H 'X-API-Key: " + str(customer.api_key) + "' http://HOST:"+ str(customer.api_port) +"/api/v1/servers/localhost"
                return jsonify( {'status': 'OK', 'output': data, 'error': err })
            else:
                return jsonify( {'status': 'KO', 'output': namespace + " not deployed" , 'error': err })
        else:
            return jsonify( {'status': 'KO', 'output': out, 'error': err }) 
    except docker.errors.APIError as err:
        if err.response.status_code == 404:
            self.log.info("[stack_info]: " + err)
        elif err.response.status_code == 500:
            logging.info("[stack_info]: " + err)
        else:
            raise err
    except Exception as err:
        raise err

@app.route("/stack", methods=['POST'])
@authenticate
def stack_list():
    cmd = 'docker stack ls --format "{{.Name}}:{{.Services}}"'
    myCmd = cmd.split()
    execute = subprocess.Popen(myCmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    out,err = execute.communicate()
    print("[stack_list]: Listing namespaces in stack...")
    stack = []
    if not err:
        for el in out.split():
            if el != "":
                stack.append(el.decode().strip('"'))
        return jsonify( {'status': 'OK', 'output': stack, 'error': err })
    else:
        return jsonify( {'status': 'KO', 'output': out, 'error': err })



def init_project(orgId):

    print("[init_project]: Compose project init started...")
    namespace, api_data, repl = create_customer(orgId)

    environment = Environment.from_env_file(FOLDER_PATH)
    config_path = get_config_path_from_options(FOLDER_PATH, dict(), environment)
    project = get_project(FOLDER_PATH, config_path, namespace)
    project_name = get_project_name(FOLDER_PATH, namespace)
    print("[init_project]: Compose project init finished...")
    return (project,namespace, api_data, repl)

def random_string(length):
    import random
    import string
    #password_characters = string.ascii_letters + string.digits + string.punctuation
    password_characters = string.ascii_letters + string.digits 
    return ''.join(random.choice(password_characters) for i in range(length))


def create_customer(orgId):
    try:
        print("[create_customer]: Creating new customer...")
        old_customer = Customer.query.order_by(Customer.id.desc()).first()

        if old_customer:
            customer_id = old_customer.id + 1
        else:
            customer_id = 1

        mysql_password = random_string(20)
        mysql_root_password = random_string(30)
        mysql_replication_password = random_string(10)
        api_key = random_string(15)

        api_port = PDNS_API_PORT + customer_id
        dns_port = PDNS_DNS_PORT + customer_id

        namespace = orgId + "_S" + str(customer_id)

        api_data= {
        'api_key': api_key,
        'api_port': api_port,
        'dns_port': dns_port
        }

        replication_user = "rep_" + namespace
        repl_data = {}

        customer = Customer(
            mysql_host = "pdns_db",
            mysql_db = "pdns_db_s"+ str(customer_id),
            mysql_user = "pdns_user_s"+ str(customer_id),
            mysql_password = mysql_password,
            mysql_container =  "mysql_s" + str(customer_id),
            mysql_server_id =  customer_id,
            mysql_repliation_user = replication_user,
            mysql_replication_password =  mysql_replication_password,
            pdns_container = "pdns_s" + str(customer_id),
            pdns_volume = "pdns_mysql_s" + str(customer_id),
            api_key = api_key,
            api_port = api_port,
            dns_port = dns_port,
            namespace = namespace,
            network = "pdns_net_s" + str(customer_id),
            enabled = True,
            stack = False
        )
        db.session.add(customer)
        db.session.commit()
        print("[create_customer]: Saving new customer into database...")

        er = open(FOLDER_PATH + ENV_BASE_FILE)
        env_read = er.read()
        er.close()

        repl_data['user'] = replication_user
        repl_data['password'] = mysql_replication_password
        repl_data['id'] = customer_id

        mysql_service_name = "pdns_db_s" + str(customer_id)

        env_replace_dict  = {
            #'GENERATED_PDNS_API_PORT': str(api_port),
            'GENERATED_PDNS_DNS_PORT': str(dns_port),
            'MYSQL_DB_PASSWORD_REPLACE': mysql_password,
            'REPLICATION_PASS_REPLACE': mysql_replication_password,
            'PDNS_API_KEY_REPLACE': api_key,
            'CUSTOMER_UID_REPLACE': namespace,
            'SERVER_ID_REPLACE': str(customer_id),
	        'MYSQL_DATABASE_REPLACE': "pdns_db_s" + str(customer_id),
            'MYSQL_USER_REPLACE': "pdns_user_s" + str(customer_id),
            'PDNS_CONTAINER_NAME_REPLACE': "pdns_s" + str(customer_id),
            'MYSQL_CONTAINER_NAME_REPLACE': "mysql_s" + str(customer_id),
            'NAMESPACE_REPLACE': namespace,
            'PDNS_DB_VOLUME_REPLACE': "pdns_mysql_s" + str(customer_id),
            'MDNSSEC_NET_NAME_REPLACE': "pdns_net_s" + str(customer_id),
            'REPLICATION_USER_REPLACE': replication_user,
            'MYSQL_ROOT_PASSWORD_REPLACE': mysql_root_password,
            'MYSQL_SERVICE_NAME_REPLACE': mysql_service_name,
            'PDNS_SERVICE_NAME_REPLACE': "pdns_s" + str(customer_id)
        }

        env_write = env_read.replace('GENERATED_PDNS_API_PORT',str(api_port))
        for key,val in env_replace_dict.items():
            env_write = env_write.replace(key,val)

        ew = open(FOLDER_PATH + ENV_FILE, "w")
        ew.write(env_write)
        ew.close()
        print("[create_customer]: Creating environment file...")


        cr = open(FOLDER_PATH + COMPOSE_BASE_FILE)
        compose_read = cr.read()
        cr.close()

        repl_data['host'] = mysql_service_name

        compose_replace_dict  = {
            #'MDSNSSEC_NET_NAME': "pdns_net_c" + str(customer_id),
            'PDNS_DNS_PORT_REPLACE': str(dns_port),
            'MYSQL_CONTAINER_NAME': "mysql_s" + str(customer_id),
            'PDNS_CONTAINER_NAME': "pdns_s" + str(customer_id),
            'PDNS_DB_VOLUME_NAME': "pdns_mysql_s" + str(customer_id),
            'NAMESPACE': namespace,
            'PDNS_API_PORT_REPLACE': str(api_port),
            'MYSQL_SERVICE_NAME': mysql_service_name,
            'PDNS_SERVICE_NAME': "pdns_s" + str(customer_id)
        }

        compose_write = compose_read.replace('MDSNSSEC_NET_NAME',"pdns_net_s" + str(customer_id))

        for key,val in compose_replace_dict.items():
            compose_write = compose_write.replace(key,val)



        cw = open(FOLDER_PATH + COMPOSE_FILE, "w")
        cw.write(compose_write)
        cw.close()
        print("[create_customer]: Creating custom docker-compose file...")


        return (namespace, api_data, repl_data)

    except docker.errors.APIError as err:
        if err.response.status_code == 404:
            self.log.info("[create_customer]: " + err)
        elif err.response.status_code == 500:
            logging.info("[create_customer]: " + err)
        else:
            raise err
    except Exception as err:
        raise err


def configure_slave(channel, repl, port=3306):
    try:
        # Check if slave is already running
        running = False
        query_db = text('use performance_schema')
        result = db.get_engine(bind='slave').execute(query_db)
        query_check = text('SELECT CHANNEL_NAME FROM replication_connection_status where CHANNEL_NAME="' + channel + '"')
        result = db.get_engine(bind='slave').execute(query_check)
        for row in result:
            if channel == row['CHANNEL_NAME']:
                running = True
                break

        # run query
        if not running:
            query_change = text('CHANGE MASTER TO MASTER_HOST="' + repl["host"] +'", MASTER_USER="' + repl["user"] + '", MASTER_PASSWORD="' + repl["password"] + '", MASTER_PORT='+ str(port) +', MASTER_AUTO_POSITION = 1 FOR CHANNEL "' + channel + '"')
            print("[configure_slave] Changing master on slave")
            print(query_change)
            print(repl)
            result = db.get_engine(bind='slave').execute(query_change)
            query_start = text('START SLAVE FOR CHANNEL "' + channel + '"')
            result = db.get_engine(bind='slave').execute(query_start)
    except Exception as err:
        raise err

# Force management database creation on slave, then start replication
try:
    # Add Management database for slave replication
    management_db = {
        'user': REPLICATION_USER,
        'password': REPLICATION_PASS,
        'host': os.environ.get('MYSQL_HOST')
    }
    query_create = text('CREATE DATABASE IF NOT EXISTS ' + os.environ.get('MYSQL_DATABASE', 'mdnssec'))
    result = db.get_engine(bind='slave').execute(query_create)
    configure_slave(REPLICATION_CHANNEL, management_db, 3306)
except Exception as err:
    raise err

# Url prefix
# https://stackoverflow.com/questions/18967441/add-a-prefix-to-all-flask-routes
# https://gist.github.com/svieira/3434cbcaf627e50a4808
parent_app = DispatcherMiddleware(simple, {API_BASE: app})

if __name__ == "__main__":
    #app.run(debug = True, host = '0.0.0.0', port='5005')
    #app.run(debug = True, host = '0.0.0.0')
    run_simple('0.0.0.0', 5000, parent_app)
