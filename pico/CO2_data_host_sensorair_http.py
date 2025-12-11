# Raspberry pi pico w (micropython) UART communication with Sensorair S8
# Send data to web server that other people can get the data using http request
# 2025.12.10
# Malithjkd


# Import necessary modules
import network
from machine import Pin, UART
import utime
import socket

# --- Sensor Setup (Keep your existing code) ---
uart = UART(1, baudrate=9600, tx=4, rx=5)
uart.init(9600, bits=8, parity=None, stop=1)
led_buildin = Pin("LED", Pin.OUT)
utime.sleep_ms(500)

# --- Wi-Fi Configuration ---
SSID = 'NinjaWarriers'    # Replace with your Wi-Fi name
PASSWORD = 'Boys1234' # Replace with your Wi-Fi password

wlan = network.WLAN(network.STA_IF)
wlan.active(True)
wlan.connect(SSID, PASSWORD)

# Wait for Wi-Fi connection
while not wlan.isconnected():
    print('Waiting for Wi-Fi connection...')
    led_buildin.value(1)
    utime.sleep(0.5)
    led_buildin.value(0)
    utime.sleep(0.5)

print('Wi-Fi Connected:', wlan.ifconfig())
# The Pico W will now have an IP address, e.g., 192.168.1.XX

# --- Global variable for CO2 value ---
current_co2_value = 0

# Function to read CO2
def read_co2():
    global current_co2_value
    uart.write(b"\xFE\x44\x00\x08\x02\x9F\x25")
    utime.sleep_ms(100) # Short wait for response
    data = uart.read(7)
    
    if data and len(data) == 7:
        byte_3 = data[3]
        byte_4 = data[4]
        current_co2_value = (byte_3 * 256) + byte_4
    else:
        print("Error reading sensor data.")

# Function to handle HTTP requests
def web_page():
    # The API endpoint will be a simple string showing the CO2 value
    html = str(current_co2_value)
    return html

# Set up socket listener
# 0.0.0.0 listens on all available interfaces (including the Wi-Fi one)
addr = socket.getaddrinfo('0.0.0.0', 80)[0][-1]
s = socket.socket()
s.bind(addr)
s.listen(1) # Listen for one incoming connection

print('Listening on:', addr)

while True:
    # 1. Read the sensor data
    read_co2()
    print('Current CO2:', current_co2_value)

    # 2. Handle HTTP request (Non-blocking check)
    try:
        conn, addr = s.accept()
        print('Got a connection from %s' % str(addr))
        request = conn.recv(1024)
        request = str(request)
        print('Content = %s' % request)

        # Send the response back
        response = web_page()
        conn.send('HTTP/1.0 200 OK\r\nContent-type: text/plain\r\n\r\n')
        conn.send(response)
        conn.close()
    except OSError as e:
        # Handle non-blocking socket error (no connection)
        if e.args[0] == 11: # errno 11 is EAGAIN/EWOULDBLOCK
            pass
        else:
            raise

    utime.sleep(2) # Wait 2 seconds before the next sensor read/loop iteration
