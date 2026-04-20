
# send message "send_telemetry" to make pi2 publish battery to the "all" topic.

# this will publish the telemetry of 2 units. the server should check in order:

# if battery < 80, check next unit

# else: send message "request_assign" and request assign the first that has enough battery.

import paho.mqtt.client as mqtt
import json
import time

broker = "localhost"
drone_telemetry = {}

def on_message(self, client, userdata, msg):

    global drone_telemetry

    # Retrieve and decode data
    data = json.loads(msg.payload.decode())

    # Get drone id and battery from payload
    drone_id = data.get("id")
    battery = data.get("battery")
    
    if drone_id and battery is not None:
        # Save id and battery in dict, then print it
        drone_telemetry[drone_id] = battery
        print(f"{drone_id}: {battery}%")


client = mqtt.Client()

# Whenwver a message is published, run func on_message
client.on_message = on_message

client.connect(broker, 1883, 60)
client.subscribe("drone/all/commands")
client.loop_start()

# Get drone telemetry
client.publish("drone/all/commands", "send_telemetry")

time.sleep(5)

for drone_id, battery in drone_telemetry.items():

    # if battery is acceptable, assign drone and break
    if battery >= 80:

        client.publish(f"drone/{drone_id}/commands", "request_assign")
        print(f"Assigned {drone_id} with {battery}% battery")
        break

    else:
    
        print("No suitable drone found")

time.sleep(1)
client.loop_stop()
client.disconnect()