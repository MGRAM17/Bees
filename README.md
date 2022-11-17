# Bees

## How it is laid out

There are two different programs here, each in their own respective folder:

 ### Publisher
 
 This is what runs off the Raspberry Pi. It reads the data from sensors and publishes it to the MQTT broker. It also stores relevent information
 
 ### Subscriber
 
 (a demonstration of this can be seen on the [repl](https://subscriber.matthewingram.repl.co/))
 
 This is a webserver dashboard which reads data coming from the publisher and displays it with charts and tables. The subscriber is also used to monitor data usage and communicate to and from the publisher.
 
 ## Environmental variables
 
 Each program requires a `.env` file to contain secret information. Here is how it should look
 
 ```py
mqttbroker="mqtt broker uri here"
mqttport="port here"
mqttuser="mqtt username here"
mqttpwd="mqtt password here"
password="webserver password here (not required with the publisher)"
 ```
 
 ## Requirements
 
 ### Publisher
 
 - [bme680](https://pypi.org/project/bme680/) (`pip install bme680`)
 - [paho-mqtt](https://pypi.org/project/paho-mqtt/) (`pip install paho-mqtt`)
 
  ### Susbcriber
 
 - [Flask](https://pypi.org/project/Flask/) (`pip install Flask`)
 - [paho-mqtt](https://pypi.org/project/paho-mqtt/) (`pip install paho-mqtt`)
 - [replit](https://pypi.org/project/paho-mqtt/) (`pip install replit`)
