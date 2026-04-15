from stmpy import Driver, Machine
import paho.mqtt.client as mqtt
import json
import time
import threading
# from sense_hat import SenseHat

MQTT_HOST = "localhost"
class fake_sense_hat:
    def get_pressure(self):
        return 1013.25 - (time.time()/10 % 10)

class Drone:



    def __init__(self):
        self.t_0 =    {'source':'initial', 'trigger':'t', 'target':'idle'}

        #STATES
        self.s_0 =  {'name': 'idle', 'do': 'send_battery_telemetry'}
        self.s_1 =  {'name': 'loading',
                'entry':'set_nav_target',
                'do': 'send_battery_telemetry',
                'exit': 'set_phase("delivery")'}
        self.s_2 = {'name': 'lift_off', 'entry':'ascend_to_cruise_height'}
        self.s_3 =  {'name': 'transit',
                'do': 'navigation_loop; send_full_telemetry',
                'low_battery': 'set_nav_target; report_order_failed; set_phase("return")'}
        self.s_4 =  {'name': 'aquire_target',
                'entry': 'enable_camera; start_timer("t0", "10000")',
                'do': 'target_detection'}
        self.s_5 =  {'name': 'land',
                'entry': 'land',
                'do': 'play_noise'}
        self.s_6 =  {'name': 'dispense_medicine',
                'entry': 'open_container; play_instructions',
                'exit': 'report_order_complete; set_phase("return"); set_nav_target'}
        self.s_7 =  {'name': 'landing_return',
                'entry': 'land'}
        self.s_8 =  {'name': 'emergency_landing',
                'entry': 'land',
                'exit': 'report_position'}
        self.s_9 =  {'name': 'unassignable', 'entry': 'low_power_mode'}

        #TRANSITIONS
        self.t_1 = {'source':'idle', 'target':'loading', 'trigger': 'request_assign'}
        self.t_2 = {'source':'loading', 'target':'liftoff', 'trigger': 'start_delivery'}
        self.t_3 = {'source':'liftoff', 'target': 'transit', 'trigger': 'at_cruising_altitude'}
        self.t_4 = {'source':'transit', 
              'function': lambda: "aquire_target" if self.phase == "delivery" else "landing_return", 
              'trigger': 'at_destination', 
              'targets': 'delivery landing_return'}
        self.t_5 = {'source': 'aquire_target', 'target':'land', 'trigger':'target_found', 'effect': 'set_nav_target; stop_timer("t0")'}
        self.t_6 = {'source': 'aquire_target', 'target':'land', 'trigger':'t0'}
        self.t_7 = {'source': 'land', 'target': 'dispense_medicine', 'trigger': 'landed'}
        self.t_8 = {'source': 'dispense_medicine', 'target':'liftoff', 'trigger': 'return_signal'}
        self.t_9 = {'source': 'dispense_medicine', 'target':'unassignable', 'trigger': 'unassign_signal'}
        self.t_10= {'source': 'transit', 'target':'emergency_landing', 'trigger':'battery_critical'}
        self.t_11= {'source': 'emergency_landing', 'target':'unassignable', 'trigger':'landed'}
        self.t_12= {'source': 'unassignable', 'target': 'idle', 'trigger':'drone_recovered'}
        self.t_13= {'source': 'landing_return', 'target':'idle', 'trigger':'landed'}

        self.phase = "delivery"
        self.battery = 100
        self.client = mqtt.Client()
        self.client.connect(MQTT_HOST)
        self.client.subscribe("drone/commands/#")
        self.client.on_message = self.on_message
        self.client.loop_start()
        self.sense = fake_sense_hat()
        # self.sense = SenseHat()
        self.machine = None
        self.nav_target = None


        self.battery_thread = threading.Thread(target=self.battery_drain)
        self.battery_thread.daemon = True
        self.battery_thread.start()

    def on_message(self, client, userdata, msg):
        payload = msg.payload.decode()
        server_commands = ["request_assign", "start_delivery", "return_signal", "unassign_signal", "drone_recovered"]
        if not self.machine:
            return
        if payload in server_commands:
            self.machine.send(payload)
        elif payload == "send_telemetry":
            self.send_full_telemetry()
        elif payload == "recharge":
            self.battery = 100
        else:
            print("Unknown command received:", payload)

    def battery_drain(self):
        while True:
            time.sleep(1)
            if not self.machine:
                continue
            if self.machine.state in ["lift_off", "transit", "aquire_target", "land", "landing_return", "emergency_landing"]:
                self.battery -= 1
            elif self.machine.state == "unassignable":
                self.battery -= 0.02
            else:            
                self.battery -= 0.1
            self.battery = max(self.battery, 0)
            if self.battery <= 10:
                self.machine.send("battery_critical")
            elif self.battery <= 30:
                self.machine.send("battery_low")

    def set_nav_target(self):
        self.nav_target={"NorthSouth": 63.4180, "EastWest": 10.4026} #la bere inn realfagsbygget som eksempel
        print("navigation target set:", self.nav_target)

    def send_battery_telemetry(self):
        payload = {"battery": self.battery}
        self.client.publish("drone/telemetry/battery", json.dumps(payload))

    def set_phase(self, phase):
        self.phase = phase
        print(f"Phase set to {phase}")

    def get_altitude(self):
        pressure = self.sense.get_pressure()
        pressure_sea_level = 1013.25 
        altitude = 44330.0 * (1.0 - pow(pressure / pressure_sea_level, 1.0 / 5.255))
        return altitude

    def ascend_to_cruise_height(self):
        altitude=self.get_altitude()
        payload={"altitude": altitude}
        self.client.publish("drone/telemetry/altitude", json.dumps(payload))
    
    #to do navigation loop?

    def send_full_telemetry(self):
        altitude = self.get_altitude()
        pressure = self.sense.get_pressure()
        payload={
            "battery": self.battery, 
            "altitude": altitude, 
            "pressure":pressure, 
            "phase": self.phase,
            "target": self.nav_target,
            "state": self.machine and self.machine.state}
        self.client.publish("drone/telemetry", json.dumps(payload))
    
    def target_detection(self): #???
        pass

    def play_noise(self):
        pass

    def fly(self):
        pass

    def land(self):
        pass

    def charge(self):
        pass





"""
from sense_hat import SenseHat

sense = SenseHat()

# Get pressure in Millibars/hPa
pressure = sense.get_pressure()

# Standard sea-level pressure in hPa is 1013.25
# Replace 1013.25 with current local QNH for better accuracy
pressure_sea_level = 1013.25 

# Calculate altitude in meters
altitude = 44330.0 * (1.0 - pow(pressure / pressure_sea_level, 1.0 / 5.255))

print("Pressure: %.2f hPa" % pressure)
print("Altitude: %.2f meters" % altitude)

"""

if __name__ == "__main__":
    drone = Drone()
    stm = Machine(name='drone_fsm', states=[drone.s_0, drone.s_1, drone.s_2, drone.s_3, drone.s_4, drone.s_5, drone.s_6, drone.s_7, drone.s_8, drone.s_9], transitions=[drone.t_0, drone.t_1, drone.t_2, drone.t_3, drone.t_4, drone.t_5, drone.t_6, drone.t_7, drone.t_8, drone.t_9, drone.t_10, drone.t_11, drone.t_12, drone.t_13], obj=drone)
    drone.machine = stm
    driver = Driver()
    driver.add_machine(stm)
    driver.start()