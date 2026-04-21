
# send message "send_telemetry" to make pi2 publish battery to the "all" topic.

# this will publish the telemetry of 2 units. the server should check in order:

# if battery < 80, check next unit

# else: send message "request_assign" and request assign the first that has enough battery.

import paho.mqtt.client as mqtt
import json
import time
import threading
from simple_term_menu import TerminalMenu

broker = "localhost"
drone_telemetry = {}

def on_message(client, userdata, msg):

    global drone_telemetry

    # Retrieve and decode data
    data = json.loads(msg.payload.decode())
    data["last_update"] = time.time()

    # Get drone id and battery from payload
    drone_id = data.get("id")
    
    # if drone_id and battery is not None:
    #     # Save id and battery in dict, then print it
    #     drone_telemetry[drone_id] = battery
    #     print(f"{drone_id}: {battery}%")
    drone_telemetry[drone_id] = data


client = mqtt.Client()

# Whenwver a message is published, run func on_message
client.on_message = on_message

client.connect(broker, 1883, 60)
client.subscribe("drone/+/telemetry")
client.loop_start()

# Get drone telemetry

selected_drone = None

while True:
    if not selected_drone:
        client.publish("drone/all/commands", "send_telemetry")
        print("Please select a drone to command:")
        for i in range(20):
            time.sleep(0.1)
            if drone_telemetry:
                break
        else:
            print("No telemetry received yet. Waiting...")
            continue
        options = [f"{drone['id']} ({drone['battery']}%) ({'available' if drone['state'] == 'idle' else drone['state']})" for drone in drone_telemetry.values()]
        terminal_menu = TerminalMenu(options)
        menu_entry_index = terminal_menu.show()
        selected_drone = options[menu_entry_index].split()[0]
        print(f"Selected drone: {selected_drone}")
        print(drone_telemetry[selected_drone])
    
    print("Select a command to send:")
    commands = ["request_assign", "start_delivery", "return_signal", "unassign_signal", "drone_recovered", "recharge", "print_status", "deselect_drone"]
    terminal_menu = TerminalMenu(commands)
    menu_entry_index = terminal_menu.show()
    selected_command = commands[menu_entry_index]
    if selected_command == "deselect_drone":
        selected_drone = None
        continue
    elif selected_command == "print_status":
        client.publish(f"drone/{selected_drone}/commands", "send_telemetry")
        if selected_drone in drone_telemetry:
            print(f"Status of {selected_drone}:")
            print(json.dumps(drone_telemetry[selected_drone], indent=2))
        continue
    else:
        client.publish(f"drone/{selected_drone}/commands", selected_command)
    

    

    time.sleep(1)

client.loop_stop()
client.disconnect()