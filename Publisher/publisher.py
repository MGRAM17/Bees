

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
import subprocess
from dotenv import load_dotenv
import threading

load_dotenv()

use_sensors = True 

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
COMMANDS_TOPIC = "gc-hive/commands"

# sample time in seconds
sample_time = 60

# setting callbacks for different events to see if it works, print the message etc.
def on_connect(client, userdata, flags, rc, properties=None):
	print("CONNACK received with code %s." % rc)
	if rc != paho.CONNACK_ACCEPTED:
		raise IOError("Couldn't establish a connection with the MQTT server")

def success_response():
    client.publish(topic=COMMANDS_TOPIC, payload="success", qos=1, retain=False)

def run_commands_threading(*commands : list):
    for command in commands:
        subprocess.call(command, shell=True)

def on_message(client : paho.Client, userdata, msg : paho.MQTTMessage):
    print(msg.topic + " " + str(msg.qos) + " " + str(msg.payload))

    save_request_stat(sys.getsizeof(msg.payload) + sys.getsizeof(msg.topic) + HEADER_SIZE )
    if msg.topic == STATS_TOPIC and msg.payload == b"request":
        publish_stats(client)
    if msg.topic == STATS_TOPIC and msg.payload == b"reset":
        save_request_stat(reset=True)
        save_request_stat(sys.getsizeof(msg.payload) + sys.getsizeof(msg.topic) + HEADER_SIZE )
        publish_stats(client)
    if msg.topic == COMMANDS_TOPIC:
        if not os.path.exists("logs.json"):
            with open("logs.json", "w") as f:
                f.write(f'{{"last_reset":"{datetime.now().isoformat()}","total_byte_usage": 0,"total_requests": 0}}')
        with open("logs.json") as f:
            logs = json.load(f)
        
        if msg.payload == b"desktop-disable":
            success_response()

            logs["gui"] = "terminal"
            with open("logs.json", "w") as f:
                json.dump(logs, f, indent=4)
            print("Disabling Desktop...")
            
            timer = threading.Thread(target=run_commands_threading, args=["sudo systemctl disable lightdm", "sudo reboot"])
            timer.start()  
        if msg.payload == b"desktop-enable":
            success_response()
            
            logs["gui"] = "desktop"
            with open("logs.json", "w") as f:
                json.dump(logs, f, indent=4)
            print("Enabling Desktop...")

            timer = threading.Thread(target=run_commands_threading, args=["sudo systemctl set-default graphical.target", "sudo dpkg-reconfigure lightdm", "sudo reboot"])
            timer.start()  
        if msg.payload == b"reboot":
            success_response()
            
            print("Rebooting...")
            timer = threading.Thread(target=run_commands_threading, args=["sudo reboot"])
            timer.start()  

    

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
    
    # Added after update; may not exist yet
    gui = logs["gui"] if "gui" in logs else "terminal"
    
    # [last_reset, total_requests, total_byte_usage, desktop/termianl]
    jsonstr = json.dumps([logs["last_reset"], logs["total_requests"], logs["total_byte_usage"], gui])
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
    try:
        # initialise the sensor
        sensor = bme680.BME680()
        time.sleep(1)

        # define the sampling rate for individual paramters
        sensor.set_humidity_oversample(bme680.OS_2X)
        sensor.set_pressure_oversample(bme680.OS_4X)
        sensor.set_temperature_oversample(bme680.OS_8X)

        # filter out noises
        sensor.set_filter(bme680.FILTER_SIZE_3)
    except:
        sensor = None


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
client.subscribe("gc-hive/commands", qos=1)

client.loop_start()

# loop to read data from sensors and publish
while True:
    
    now = datetime.now().strftime("%d-%b-%Y (%H:%M:%S.%f)")
    if use_sensors:
        if sensor and sensor.get_sensor_data():
            pres = sensor.data.pressure
            hum = sensor.data.humidity
            temp = sensor.data.temperature
            res = round(sensor.data.gas_resistance)

            publish_data(client, temp, pres, hum, res)
        else:
            client.publish(topic=DATA_TOPIC, payload=json.dumps({"error":"Sensor not connected or working!"}), qos=2, retain=False)
    else:
        temp = random.randint(2000, 2300)/100
        pres = random.randint(101700, 101800)/100
        hum = random.randint(4000, 4200)/100
        res = random.randint(100000000, 103000000)

        publish_data(client, temp, pres, hum, res)

    
    
    time.sleep(sample_time)
