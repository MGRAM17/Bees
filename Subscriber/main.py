
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

# broker details - for security these are hidden and need to be included for code to work
mqttbroker = os.getenv("mqttbroker")
mqttport = int(os.getenv("mqttport"))
mqttuser = os.getenv("mqttuser")
mqttpwd = os.getenv("mqttpwd")
PASSWORD = os.getenv("password")

STATS_TOPIC = "gc-hive/stats"
DATA_TOPIC = "gc-hive/data"

# setting callbacks for different events to see if it works, print the message etc.
def on_connect(client, userdata, flags, rc, properties=None):
    print("CONNACK received with code %s." % rc)

def request_stats(client : paho.Client):
    client.publish(topic=STATS_TOPIC, payload="request", qos=2, retain=False)
def reset_stats(client : paho.Client):
    client.publish(topic=STATS_TOPIC, payload="reset", qos=2, retain=False)

all_bee_data_compressed : typing.List[typing.List[typing.Union[str, float]]] = []
stats_recieved : typing.List[typing.Union[str, int]] = []
last_message : datetime.datetime = datetime.datetime.now()

# print message, useful for checking if it was successful
def on_message(client, userdata, msg : mqtt_client.MQTTMessage):
    global stats_recieved
    global last_message
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

        #all_bee_data.append(data)
        d = [datetime.datetime.now().isoformat()] + data
        all_bee_data_compressed.append(d)

        socketio.emit("data", "new")

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
    if (datetime.datetime.now() - last_message) > datetime.timedelta(seconds=65):
        return flask.jsonify({"error":True, "message":"Haven't recieved a message in over a minute... Sensors may be offline.", "data":all_bee_data_compressed})
    return flask.jsonify({"error":False, "data":all_bee_data_compressed})

@flask_app.route("/api/stats", methods=["GET"])
def api_stats():
    if stats_recieved == []:
        request_stats(client)
    
    started_time = datetime.datetime.now()
    while stats_recieved == []:
        if (datetime.datetime.now() - started_time) > datetime.timedelta(seconds=5):
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
        if (datetime.datetime.now() - started_time) > datetime.timedelta(seconds=5):
            return flask.jsonify({"error":True, "message":"Failed. The sensors may be offline..."})
    rec = stats_recieved.copy()
    
    return flask.jsonify({"data":rec})

@flask_app.route("/api/data", methods=["DELETE"])
def api_clear_data():
    global all_bee_data_compressed
    
    pwd = flask.request.args.get("pwd")
    if pwd != PASSWORD:
        return flask.jsonify({"error":True, "message":"Password was incorrect"})

    all_bee_data_compressed = []
    return flask.jsonify({"message":"Cleared all memory"})


def run_flask_app():
    #flask_app.run("0.0.0.0", 5000)
    socketio.run(flask_app, host="0.0.0.0", port=5000)

t = threading.Thread(target=run_flask_app)
t.start()

# loop_forever for simplicity, here you need to stop the loop manually
# you can also use loop_start and loop_stop
client.loop_forever()

