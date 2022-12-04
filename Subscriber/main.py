
#
import time
import paho.mqtt.client as paho
from paho import mqtt

from paho.mqtt import client as mqtt_client

import json
import flask 
import threading

import config
import os
import typing
import datetime

import flask_socketio
import math

# Replit db for storing values if on repl.it
from replit import db 

# Remove logging
import logging
log = logging.getLogger('werkzeug')
log.setLevel(logging.ERROR)

TIMEOUT_TIME = 5

# broker details - for security these are hidden and need to be included for code to work
mqttbroker = os.getenv("mqttbroker")
mqttport = int(os.getenv("mqttport"))
mqttuser = os.getenv("mqttuser")
mqttpwd = os.getenv("mqttpwd")
PASSWORD = os.getenv("password")

STATS_TOPIC = "gc-hive/stats"
DATA_TOPIC = "gc-hive/data"
COMMANDS_TOPIC = "gc-hive/commands"

# setting callbacks for different events to see if it works, print the message etc.
def on_connect(client, userdata, flags, rc, properties=None):
    print("CONNACK received with code %s." % rc)

def request_stats(client : paho.Client):
    client.publish(topic=STATS_TOPIC, payload="request", qos=2, retain=False)
def reset_stats(client : paho.Client):
    client.publish(topic=STATS_TOPIC, payload="reset", qos=2, retain=False)
def desktop(client : paho.Client, enable=False):
    if enable:
        client.publish(topic=COMMANDS_TOPIC, payload="desktop-enable", qos=2, retain=False)
    else:
        client.publish(topic=COMMANDS_TOPIC, payload="desktop-disable", qos=2, retain=False)
def reboot(client: paho.Client):
    client.publish(topic=COMMANDS_TOPIC, payload="reboot", qos=2, retain=False)

# If on ReplIt, use their DB system to hold information. Otherwise initialise new list
all_bee_data_compressed : typing.List[typing.List[typing.Union[str, float]]] = list(list(d) for d in db["data"]) if db and "data" in db else []
stats_recieved : typing.List[typing.Union[str, int]] = []
success = False
last_message : datetime.datetime = datetime.datetime.now()

# If the sensors send an error but are not offline, it is stored here
error = None

# print message, useful for checking if it was successful
def on_message(client, userdata, msg : mqtt_client.MQTTMessage):
    global stats_recieved
    global last_message
    global error
    global success

    print(msg.topic + " " + str(msg.qos) + " " + str(msg.payload))

    if msg.topic == STATS_TOPIC:
        if msg.payload not in [b"request", b"reset"]:
            stats_recieved = json.loads(msg.payload)
    
    if msg.topic == DATA_TOPIC:
        last_message = datetime.datetime.now()

        stats_recieved = []
        if msg.retain == True:
            return
        
        data = json.loads(msg.payload)

        if type(data) == dict:
            print(f"ERROR: {data['error']}")
            error = data["error"]
            socketio.emit("errors", error)
            return
        error = None

        #all_bee_data.append(data)
        d = [datetime.datetime.now().isoformat()] + data
        all_bee_data_compressed.append(d)

        socketio.emit("data", "new")

        # If on ReplIt, use their DB system to hold information
        try:
            if "data" not in db:
                db["data"] = []
            db["data"] = list(db["data"]) + [d]
        except:
            pass
    if msg.topic == COMMANDS_TOPIC:
        if msg.payload == b"success":
            success = True

# using MQTT version 5 here, for 3.1.1: MQTTv311, 3.1: MQTTv31
# userdata is user defined data of any type, updated by user_data_set()
# client_id is the given name of the client
client = paho.Client(client_id="", userdata=None, protocol=paho.MQTTv5)
client.on_connect = on_connect

# enable TLS for secure connection
client.tls_set(tls_version=mqtt.client.ssl.PROTOCOL_TLS)
# set username and password
client.username_pw_set(mqttuser, mqttpwd)
# connect to HiveMQ Cloud on port 8883 (default for MQTT)
client.connect(mqttbroker, mqttport)

# setting callbacks, use separate functions like above for better visibility
client.on_message = on_message

# subscribe to all topics of encyclopedia by using the wildcard "#"
client.subscribe("gc-hive/data", qos=1)
client.subscribe("gc-hive/stats", qos=1)
client.subscribe("gc-hive/commands", qos=1)

flask_app = flask.Flask(__name__)
socketio = flask_socketio.SocketIO(flask_app)

if not config.production_mode:
    flask_app.config['SEND_FILE_MAX_AGE_DEFAULT'] = 0
    flask_app.config["TEMPLATES_AUTO_RELOAD"] = True

@flask_app.route("/")
def index():
    return flask.render_template("index.html")

@flask_app.route("/api/data", methods=["GET"])
def api_data():
    # Paginator: ?start={timestamp}, ?finish={timestamp}, ?every=1, ?page=1
    
    # 2022-11-18 15:20:00
    data_to_send = []
    per_page = 12 * 60
    start = datetime.datetime(2020, 1, 1) if not flask.request.args.get("start") else datetime.datetime.strptime(flask.request.args.get("start"), '%Y-%m-%d %H:%M:%S')
    finish = datetime.datetime.now() if not flask.request.args.get("finish") else datetime.datetime.strptime(flask.request.args.get("finish"), '%Y-%m-%d %H:%M:%S')
    
    page = int(flask.request.args.get("page")) if flask.request.args.get("page") else -1

    for i, data in enumerate(all_bee_data_compressed):
        iso = datetime.datetime.fromisoformat(data[0])

        if iso < start or iso > finish:
            continue 
            
        data_to_send.append(data)
    
    every = 1
    if flask.request.args.get("every") and flask.request.args.get("every") == "auto":
        every = math.ceil(len(data_to_send) / 500 + 0.001)
    elif flask.request.args.get("every"):
        every = int(flask.request.args.get("every"))

    total_length = len(data_to_send)
    if page != -1:
        data_to_send = data_to_send[per_page*page : (per_page*page)+per_page]
    data_to_send = data_to_send[::every]

    if error or (datetime.datetime.now() - last_message) > datetime.timedelta(seconds=65):
        return flask.jsonify({
            "error":True, 
            "data":data_to_send, 
            "page":page, 
            "pages":total_length // per_page,
            "every":every,
            "message": error or "Sensors not responding..."
        })

    return flask.jsonify({
		"error":False, 
		"data":data_to_send, 
		"page":page, 
        "pages":total_length // per_page,
        "every":every
	})

@flask_app.route("/api/stats", methods=["GET"])
def api_stats():
    if stats_recieved == []:
        request_stats(client)
    
    started_time = datetime.datetime.now()
    while stats_recieved == []:
        if (datetime.datetime.now() - started_time) > datetime.timedelta(seconds=TIMEOUT_TIME):
            return flask.jsonify({"error":True, "message":"Failed. The sensors may be offline..."})
    rec = stats_recieved.copy()
    
    return flask.jsonify({"data":rec})

@flask_app.route("/api/password", methods=["GET"])
def api_password():
    pwd = flask.request.args.get("pwd")
    if pwd == PASSWORD:
        return flask.jsonify({"valid":True})
    else:
        return flask.jsonify({"valid":False})



@flask_app.route("/api/stats", methods=["DELETE"])
def api_reset_stats():
    global stats_recieved
    stats_recieved = []

    pwd = flask.request.args.get("pwd")
    if pwd != PASSWORD:
        return flask.jsonify({"error":True, "message":"Password was incorrect"})

    reset_stats(client)
    
    started_time = datetime.datetime.now()
    while stats_recieved == []:
        if (datetime.datetime.now() - started_time) > datetime.timedelta(seconds=TIMEOUT_TIME):
            return flask.jsonify({"error":True, "message":"Failed. The sensors may be offline..."})
    rec = stats_recieved.copy()
    
    return flask.jsonify({"data":rec})

@flask_app.route("/api/enable_desktop", methods=["GET"])
def api_enable_desktop():
    global success 
    success = False 

    pwd = flask.request.args.get("pwd")
    if pwd != PASSWORD:
        return flask.jsonify({"error":True, "message":"Password was incorrect"})

    desktop(client, enable=True)
    
    started_time = datetime.datetime.now()
    while not success:
        if (datetime.datetime.now() - started_time) > datetime.timedelta(seconds=TIMEOUT_TIME):
            return flask.jsonify({"error":True, "message":"Failed. The sensors may be offline..."})
    
    return flask.jsonify({"message": "Sensors are restarting... This may take a few minutes"})

@flask_app.route("/api/disable_desktop", methods=["GET"])
def api_disable_desktop():
    global success 
    success = False 

    pwd = flask.request.args.get("pwd")
    if pwd != PASSWORD:
        return flask.jsonify({"error":True, "message":"Password was incorrect"})

    desktop(client, enable=False)
    
    started_time = datetime.datetime.now()
    while not success:
        if (datetime.datetime.now() - started_time) > datetime.timedelta(seconds=TIMEOUT_TIME):
            return flask.jsonify({"error":True, "message":"Failed. The sensors may be offline..."})
    
    return flask.jsonify({"message": "Sensors are restarting... This may take a few minutes"})

@flask_app.route("/api/reboot", methods=["GET"])
def api_reboot():
    global success 
    success = False 

    pwd = flask.request.args.get("pwd")
    if pwd != PASSWORD:
        return flask.jsonify({"error":True, "message":"Password was incorrect"})

    reboot(client)
    
    started_time = datetime.datetime.now()
    while not success:
        if (datetime.datetime.now() - started_time) > datetime.timedelta(seconds=TIMEOUT_TIME):
            return flask.jsonify({"error":True, "message":"Failed. The sensors may be offline..."})
    
    return flask.jsonify({"message": "This may take a few minutes"})

@flask_app.route("/api/data", methods=["DELETE"])
def api_clear_data():
    global all_bee_data_compressed
    
    pwd = flask.request.args.get("pwd")
    if pwd != PASSWORD:
        return flask.jsonify({"error":True, "message":"Password was incorrect"})

    all_bee_data_compressed = []
    try:
        db["data"] = []
    except:
        pass
    return flask.jsonify({"message":"Cleared all memory"})


def run_flask_app():
    #flask_app.run("0.0.0.0", 5000)
    socketio.run(flask_app, host="0.0.0.0", port=5000)

t = threading.Thread(target=run_flask_app)
t.start()

# loop_forever for simplicity, here you need to stop the loop manually
# you can also use loop_start and loop_stop
client.loop_forever()

