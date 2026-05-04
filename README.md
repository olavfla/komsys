# Komsys
Komsys drone project repo

## Drone state machine

Code implementation can be found in `drone_state_machine.py`.

[State machine diagram](./drone_state_diagram_v6.png)

## Server software

We have two versions of the server software. server_software_terminal is the first version and runs standalone in the terminal. This version consists only of an MQTT client and a way for the user to interact with it and a simple way to print the raw drone data. To run it, ensure you have installed the python dependencies with `pip install -m requirements.txt` and that you have a broker running on localhost. Then just run `python3 server_software_terminal.py`

The second version has an MQTT client as well as a Web server to mediate the commands. The webserver handles telemetry updates to the UI and commands from the UI, but does not serve the web page itself. To run it, two terminals are required: one for the web dev server and one for the drone server program. 

Terminal 1 (web dev server):
* `cd react-app`
* `npm install`
* `npm run dev`

Terminal 2 (drone server program):
* `pip install -m requirements.txt` (to get the required dependencies)
* `python3 server_software_web.py`

## Other requirements / assumptions
Both server software programs assume that you have an MQTT broker running on localhost. For our project we used mosquitto. To allow for external connections, you might have to edit the config (usually `/etc/mosquitto/mosquitto.conf` on linux):

`listener 1883 0.0.0.0` (bind to 'any' interface)

`allow_anonymous true` (allow connection without auth (unsafe))



The `drone_state_machine.py` attempts to connect to `brick.local` for the broker (__line 9__). It assumes this is where the broker/server is reachable. Either change this value to an appropriate IP address, or make the broker reachable on that address. You can do this by setting the hostname to 'brick' (`sudo hostnamectl set-hostname brick`) and installing avahi-daemon for multicast dns. 
The same goes for the web dev server, which tries to connect with http (__line 17__ and __line 49__).