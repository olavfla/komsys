from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import paho.mqtt.client as mqtt
import json
import time
import threading

test_drone = {
    "id": "TEST_DRONE",
    "battery": 75,
    "phase": "delivery",
    "last_update": time.time()
}

class CustomHandler(BaseHTTPRequestHandler):
    def __init__(self, request, client_address, server):
        super().__init__(request, client_address, server)

    def end_headers(self):
        # Add CORS headers to every response, including errors.
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        super().end_headers()
        
    def do_GET(self):
        if self.path == "/":
            self.send_response(200)
            self.send_header("Content-type", "text/html")
            self.end_headers()
            self.wfile.write(b"Hello, World!")
        elif self.path.startswith("/sse"):
            self.send_response(200)
            self.send_header("Content-Type", "text/event-stream")
            self.send_header("Cache-Control", "no-cache")
            self.send_header("Connection", "keep-alive")
            self.end_headers()
            self.server.sseclients.append(self.wfile)
        else:
            self.send_response(404)
            self.send_header("Content-type", "text/plain")
            self.end_headers()
            self.wfile.write(b"Not Found")

    def do_OPTIONS(self):
        self.send_response(204)
        self.end_headers()

    def do_POST(self):
        if self.path.startswith("/commands/"):
            if len(self.path.split("/")) != 3:
                self.send_response(400)
                self.send_header("Content-type", "application/json")
                self.end_headers()
                response = {"status": "error", "message": "Invalid command endpoint. Use /command/all or /command/<drone_id>."}
                self.wfile.write(json.dumps(response).encode())
                return
            content_length = int(self.headers.get("Content-Length", 0))
            post_data = self.rfile.read(content_length)
            try:
                command = post_data.decode()
            except (json.JSONDecodeError, ValueError) as e:
                self.send_response(400)
                self.send_header("Content-type", "application/json")
                self.end_headers()
                response = {"status": "error", "message": str(e)}
                self.wfile.write(json.dumps(response).encode())
                return
            if self.path == "/commands/all":
                if command == "send_telemetry":
                    self.server.mqtt_client.publish("drone/all/commands", command)
                    self.send_response(200)
                    self.send_header("Content-type", "application/json")
                    self.end_headers()
                    response = {"status": "success", "message": f"Command '{command}' sent to all drones."}
                    self.wfile.write(json.dumps(response).encode())
                else:
                    self.send_response(400)
                    self.send_header("Content-type", "application/json")
                    self.end_headers()
                    response = {"status": "error", "message": "Invalid command for /command/all. Only 'send_telemetry' is allowed."}
                    self.wfile.write(json.dumps(response).encode())
            else:
                drone_id = self.path.split("/")[-1]
                self.server.mqtt_client.publish(f"drone/{drone_id}/commands", command)
                self.send_response(200)
                self.send_header("Content-type", "application/json")
                self.end_headers()
                response = {"status": "success", "message": f"Command '{command}' sent to drone '{drone_id}'."}
                self.wfile.write(json.dumps(response).encode())

        else:
            self.send_response(404)
            self.send_header("Content-type", "text/plain")
            self.end_headers()
            self.wfile.write(b"Not Found")
            

class CustomHTTPServer(ThreadingHTTPServer):
    def __init__(self, server_address, RequestHandlerClass):
        super().__init__(server_address, RequestHandlerClass)
        self.mqtt_client = mqtt.Client()
        self.mqtt_client.connect("localhost", 1883, 60)
        self.mqtt_client.subscribe("drone/+/telemetry")
        self.mqtt_client.on_message = self.on_mqtt_message
        self.mqtt_client.loop_start()
        self.drone_telemetry = {"TEST_DRONE": test_drone}
        self.sseclients = []

    def on_mqtt_message(self, client, userdata, msg):
        data = json.loads(msg.payload.decode())
        drone_id = data.get("id")
        if drone_id:
            self.drone_telemetry[drone_id] = data
            self.broadcast_telemetry()

    def broadcast_telemetry(self):
        i = 0
        while i < len(self.sseclients):
            client = self.sseclients[i]
            try:
                if not client.writable():
                    self.sseclients.pop(i)
                    print("Removed non-writable client")
                    continue
                client.write(b"event: telemetry\n")
                client.write(f"data: {json.dumps(self.drone_telemetry)}\n\n".encode())
                client.flush()
                i += 1
            except Exception as e:
                print(f"Error sending telemetry to client: {e}")
                self.sseclients.pop(i)

    
    def broadcast_loop(self):
        while True:
            self.drone_telemetry["TEST_DRONE"]["last_update"] = time.time()
            print(f"n_clients: {len(self.sseclients)}, telemetry: {self.drone_telemetry}")
            self.broadcast_telemetry()
            time.sleep(1)


if __name__ == "__main__":
    server_address = ("", 8080)
    httpd = CustomHTTPServer(server_address, CustomHandler)
    print("Starting server on port 8080...")

    # Start the broadcast loop in a separate thread
    broadcast_thread = threading.Thread(target=httpd.broadcast_loop)
    broadcast_thread.daemon = True
    broadcast_thread.start()

    httpd.serve_forever()
