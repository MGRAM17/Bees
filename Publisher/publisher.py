

# import time library for delay purposes
import time

# import datetime library for timestamp
from datetime import datetime

import json

# import paho mqtt libraries to publish sensor data
import paho.mqtt.client as paho
from paho import mqtt

import random
import sys
import os

use_sensors = False 

if use_sensors:
    # import the BME680 library for RPI
    import bme680

HEADER_SIZE = 20

# broker details - for security these are hidden and need to be included for code to work
mqttbroker = os.getenv("mqttbroker")
mqttport = int(os.getenv("mqttport"))
mqttuser = os.getenv("mqttuser")
mqttpwd = os.getenv("mqttpwd")

DATA_TOPIC = "gc-hive/data"
STATS_TOPIC = "gc-hive/stats"

# sample time in seconds
sample_time = 60

# setting callbacks for different events to see if it works, print the message etc.
def on_connect(client, userdata, flags, rc, properties=None):
	print("CONNACK received with code %s." % rc)
	if rc != paho.CONNACK_ACCEPTED:
		raise IOError("Couldn't establish a connection with the MQTT server")

def on_message(client, userdata, msg : paho.MQTTMessage):
    save_request_stat(sys.getsizeof(msg.payload) + sys.getsizeof(msg.topic) + HEADER_SIZE )
    if msg.topic == STATS_TOPIC and msg.payload == b"request":
        publish_stats(client)
    if msg.topic == STATS_TOPIC and msg.payload == b"reset":
        save_request_stat(reset=True)
        save_request_stat(sys.getsizeof(msg.payload) + sys.getsizeof(msg.topic) + HEADER_SIZE )
        publish_stats(client)

    print(msg.topic + " " + str(msg.qos) + " " + str(msg.payload))

def save_request_stat(packet_size=None, reset=False):
    if not os.path.exists("logs.json"):
        with open("logs.json", "w") as f:
            f.write(f'{{"last_reset":"{datetime.now().isoformat()}","total_byte_usage": 0,"total_requests": 0}}')

    if reset:
        return os.remove("logs.json")

    with open("logs.json") as f:
        logs = json.load(f)
    
    logs["total_byte_usage"] += packet_size 
    logs["total_requests"] += 1 

    with open("logs.json", "w") as f:
        json.dump(logs, f, indent=4)

def publish_stats(client : paho.Client):
    if not os.path.exists("logs.json"):
        with open("logs.json", "w") as f:
            f.write(f'{{"last_reset":"{datetime.now().isoformat()}","total_byte_usage": 0,"total_requests": 0}}')
    
    with open("logs.json") as f:
        logs = json.load(f)
    
    # [last_reset, total_requests, total_byte_usage]
    jsonstr = json.dumps([logs["last_reset"], logs["total_requests"], logs["total_byte_usage"]])
    packet_size = sys.getsizeof(jsonstr) + HEADER_SIZE 

    result = client.publish(topic=STATS_TOPIC, payload=jsonstr, qos=0, retain=False)
    
    save_request_stat(packet_size)
    print("P", f"published to {STATS_TOPIC} - {result}\n")

    return result


def publish_data(client : paho.Client, temperature, pressure, humidity, resistance):
    print("V", temperature, pressure, humidity)
    
    # [time, temperature, pressure, humidity, resistance]
    data = [temperature, pressure, humidity, resistance]
    print("D", data)

    if not os.path.exists("data.json"):
        with open("data.json", "w") as f:
            f.write('[]')
    
    with open("data.json") as f:
        data_logs : list = json.load(f)
    data_logs.append([datetime.now().isoformat()] + data)
    with open("data.json", "w") as f:
        json.dump(data_logs, f, indent=4)
            
    jsonstr = json.dumps(data)

    packet_size = sys.getsizeof(jsonstr) + HEADER_SIZE 
    
    print("J", jsonstr)
    result = client.publish(topic=DATA_TOPIC, payload=jsonstr, qos=2, retain=False)
    save_request_stat(packet_size)
    print("P", f"published to {DATA_TOPIC} - {result}\n")
    
    return result

if use_sensors:
    # initialise the sensor
    sensor = bme680.BME680()
    time.sleep(1)

    # define the sampling rate for individual paramters
    sensor.set_humidity_oversample(bme680.OS_2X)
    sensor.set_pressure_oversample(bme680.OS_4X)
    sensor.set_temperature_oversample(bme680.OS_8X)

    # filter out noises
    sensor.set_filter(bme680.FILTER_SIZE_3)


# initialise the MQTT client

# create the client
#client = paho.Client(client_id="", userdata=None, protocol=paho.MQTTv5)
client = paho.Client("p2")
client.on_connect = on_connect
client.on_message = on_message

# enable TLS for secure connection
client.tls_set(tls_version=mqtt.client.ssl.PROTOCOL_TLS)

# set username and password
client.username_pw_set(mqttuser, mqttpwd)

# connect to HiveMQ Cloud on port 8883 (default for MQTT)
client.connect(mqttbroker, mqttport)
client.subscribe("gc-hive/stats", qos=1)

client.loop_start()

# loop to read data from sensors and publish
while True:
    
    now = datetime.now().strftime("%d-%b-%Y (%H:%M:%S.%f)")
    if use_sensors:
        if sensor.get_sensor_data():
            pres = sensor.data.pressure
            hum = sensor.data.humidity
            temp = sensor.data.temperature
            res = round(sensor.data.gas_resistance)
    else:
        temp = random.randint(2000, 2300)/100
        pres = random.randint(101700, 101800)/100
        hum = random.randint(4000, 4200)/100
        res = random.randint(100000000, 103000000)

    
    
    #publish_value(client, topic, data)
    publish_data(client, temp, pres, hum, res)
    
    #if sensor.data.heat_stable:
    #    output += f", {sensor.data.gasresitance} ohms"
    #print(output)
    
    time.sleep(sample_time)
