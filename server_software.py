from stmpy import Driver, Machine
import paho.mqtt.client as mqtt
import json
import time
import threading


# send message "send_telemetry" to make pi2 publish battery to the "all" topic.

# this will publish the telemetry of 2 units. the server should check in order:

# if battery < 80, check next unit

# else: send message "request_assign" and request assign the first that has enough battery.

