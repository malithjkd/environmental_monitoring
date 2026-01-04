# still got bugs but connection is robust.

import network
import socket
from time import sleep
import machine
import sys

pico_led = machine.Pin("LED",machine.Pin.OUT)
#pico_led = machine.Pin(15,machine.Pin.OUT)

adcpin = 4
sensor = machine.ADC(adcpin)

ssid = 'NinjaWarriers'
password = 'Boys1234'

MAX_WIFI_RETRY = 5  # Maximum retry attempts for initial connection
WIFI_RETRY_DELAY = 5 # Delay in seconds between WiFi retry attempts
WIFI_CHECK_INTERVAL = 10 # Interval to check WiFi connection in seconds
RETRY_CONNECT_AFTER_FAILURE = 60 # Wait time after multiple connection failures before retrying again


def read_temperature():
    """Reads temperature from ADC sensor."""
    adc_value = sensor.read_u16()
    volt = (3.3/65535) * adc_value
    temperature = 27 - (volt - 0.706)/0.001721
    return round(temperature, 1)

def connect_wifi(max_retries=MAX_WIFI_RETRY, retry_delay=WIFI_RETRY_DELAY):
    """
    Connects to Wi-Fi with retry mechanism.

    Args:
        max_retries (int): Maximum number of connection attempts.
        retry_delay (int): Delay in seconds between retries.

    Returns:
        str or None: IP address if connection is successful, None otherwise.
    """
    wlan = network.WLAN(network.STA_IF)
    wlan.active(True)
    if not wlan.isconnected():
        print('Connecting to Wi-Fi...')
        wlan.connect(ssid, password)
        retry_count = 0
        while retry_count < max_retries:
            if wlan.isconnected():
                print('Wi-Fi connected')
                ip = wlan.ifconfig()[0]
                print(f'Connected on IP address: {ip}')
                pico_led.off()  # Turn off LED on successful connection
                return ip
            else:
                retry_count += 1
                print(f'Connection attempt {retry_count}/{max_retries} failed. Retrying in {retry_delay} seconds...')
                pico_led.on() # Turn on LED during connection attempts
                sleep(retry_delay)

        print('Wi-Fi connection failed after multiple attempts.')
        pico_led.off() # Turn off LED after failed attempts
        return None
    else:
        ip = wlan.ifconfig()[0]
        print('Wi-Fi already connected.')
        print(f'Connected on IP address: {ip}')
        return ip


def open_socket(ip):
    """Opens a socket for web server."""
    try:
        address = (ip, 80)
        connection = socket.socket()
        connection.bind(address)
        connection.listen(1)
        print(f"Listening on IP: {ip}, Port: 80")
        return connection
    except OSError as e:
        print(f"Socket creation failed: {e}")
        return None

def webpage(temperature, state):
    """Generates HTML webpage."""
    html = f"""<!DOCTYPE html>
<html>
<head>
    <title>Pico W Web Server</title>
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <style>
        body {{ font-family: Arial, Helvetica, sans-serif; }}
        .button {{
            background-color: #4CAF50; /* Green */
            border: none;
            color: white;
            padding: 15px 32px;
            text-align: center;
            text-decoration: none;
            display: inline-block;
            font-size: 16px;
            margin: 4px 2px;
            cursor: pointer;
        }}
        .buttonOff {{
            background-color: #f44336; /* Red */
        }}
    </style>
</head>
<body>
    <h1>Pico W Web Server</h1>
    <p>Temperature: <strong>{temperature}°C</strong></p>
    <p>LED Status: <strong>{state}</strong></p>
    <p><a href="./lighton"><button class="button">Light ON</button></a></p>
    <p><a href="./lightoff"><button class="button buttonOff">Light OFF</button></a></p>
</body>
</html>"""
    return html

def serve_client(connection):
    """Handles client requests to the web server."""
    state = 'OFF'
    pico_led.off()
    temperature = 0
    try:
        client, addr = connection.accept()
        print(f'Client connected from {addr}')
        request = client.recv(1024)
        request = request.decode('utf-8') # Decode bytes to string
        #print('Request:') # Optionally print the full request for debugging
        #print(request)

        if request.find('/lighton') != -1:
            pico_led.on()
            state = 'ON'
            print('LED turned ON')
        elif request.find('/lightoff') != -1:
            pico_led.off()
            state = 'OFF'
            print('LED turned OFF')

        temperature = read_temperature()
        html = webpage(temperature, state)
        client.send('HTTP/1.1 200 OK\n')
        client.send('Content-Type: text/html\n')
        client.send('Connection: close\n\n')
        client.sendall(html.encode('utf-8')) # Encode string to bytes
        client.close()

    except OSError as e:
        client.close()
        print('Client connection error:', e)


def main():
    """Main function to handle Wi-Fi connection, web server, and reconnection."""
    ip_address = connect_wifi() # Initial Wi-Fi connection

    if ip_address is None:
        print(f"Failed to connect to Wi-Fi initially. Restarting in {RETRY_CONNECT_AFTER_FAILURE} seconds...")
        sleep(RETRY_CONNECT_AFTER_FAILURE)
        machine.reset() # Reset Pico if initial connection fails

    connection_socket = open_socket(ip_address)
    if connection_socket is None:
        print(f"Failed to open socket. Restarting in {RETRY_CONNECT_AFTER_FAILURE} seconds...")
        sleep(RETRY_CONNECT_AFTER_FAILURE)
        machine.reset() # Reset Pico if socket fails

    while True:
        if network.WLAN(network.STA_IF).isconnected(): # Check Wi-Fi connection periodically
            try:
                if connection_socket:
                    serve_client(connection_socket)
                else:
                    print("Socket is not valid, attempting to reopen...")
                    connection_socket = open_socket(ip_address) # Try to reopen socket if it's closed unexpectedly
                    if connection_socket is None:
                        print(f"Failed to reopen socket. Restarting in {RETRY_CONNECT_AFTER_FAILURE} seconds...")
                        sleep(RETRY_CONNECT_AFTER_FAILURE)
                        machine.reset()

            except OSError as e:
                print("Error during server loop:", e)
                if e.args[0] == 113: # Check for specific error (e.g., ECONNABORTED) which might indicate connection issues
                    print("Possible Wi-Fi disconnection during server operation.")
                    # Wi-Fi might have disconnected during operation, reconnection will be handled in the next loop iteration
        else:
            print('Wi-Fi connection lost!')
            if connection_socket: # Close existing socket if Wi-Fi is down
                connection_socket.close()
                connection_socket = None
            ip_address = connect_wifi() # Attempt to reconnect Wi-Fi
            if ip_address:
                connection_socket = open_socket(ip_address) # Reopen socket if Wi-Fi reconnects
                if connection_socket is None:
                    print("Failed to reopen socket after reconnection. Restarting in {RETRY_CONNECT_AFTER_FAILURE} seconds...")
                    sleep(RETRY_CONNECT_AFTER_FAILURE)
                    machine.reset()
            else:
                print(f"Failed to reconnect to Wi-Fi. Retrying in {RETRY_CONNECT_AFTER_FAILURE} seconds...")
                sleep(RETRY_CONNECT_AFTER_FAILURE)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("Server stopped by user.")
    except Exception as e:
        sys.print_exception(e) # Print full exception details for debugging
        print("Fatal error occurred. Restarting in {RETRY_CONNECT_AFTER_FAILURE} seconds...")
        sleep(RETRY_CONNECT_AFTER_FAILURE)
        machine.reset()

