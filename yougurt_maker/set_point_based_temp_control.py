import network
import socket
import machine
import onewire
import ds18x20
import utime
import select
import secrets

# Pins
led_buildin = machine.Pin("LED", machine.Pin.OUT)
relay_3 = machine.Pin(15, machine.Pin.OUT)
relay_3.off()
led_buildin.off()

TEST_PIN = 3
dat = machine.Pin(TEST_PIN)
ds = ds18x20.DS18X20(onewire.OneWire(dat))




def scan_sensors():
    print("Waiting for DS18B20 to stabilize...")
    utime.sleep(2) # Add delay before scanning
    scanned_roms = ds.scan()
    if not scanned_roms:
        print("No DS18B20 sensors found! Please check wiring.")
    else:
        print("Found DS18B20:", scanned_roms)
    return scanned_roms



def connect_wifi():
    wlan = network.WLAN(network.STA_IF)
    wlan.active(True)
    
    for network_info in secrets.WIFI_NETWORKS:
        ssid = network_info['ssid']
        password = network_info['password']
        print(f"Trying to connect to {ssid}...")
        wlan.connect(ssid, password)
        
        connected = False
        for _ in range(20): # wait up to 20 seconds per network
            if wlan.isconnected():
                connected = True
                break
            print('Waiting for connection...')
            utime.sleep(1)
        
        if connected:
            ip = wlan.ifconfig()[0]
            print(wlan.ifconfig())
            print(f'Connected on {ip}')
            return ip
        else:
            print(f"Failed to connect to {ssid}")
            utime.sleep(30) # Retry delay before trying next network
    
    raise RuntimeError("Could not connect to any configured WiFi networks")

def start_server(ip):
    if not ip:
        return None
    addr = socket.getaddrinfo('0.0.0.0', 80)[0][-1]
    s = socket.socket()
    s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    s.bind(addr)
    s.listen(1)
    s.setblocking(False) # Non-blocking socket
    print('Listening on http://' + ip)
    return s

def get_html(temp, relay_state):
    state_str = "ON (Heating)" if relay_state else "OFF"
    html = f"""<!DOCTYPE html>
<html>
<head>
    <title>Yogurt Maker Controller</title>
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <meta http-equiv="refresh" content="5">
    <style>
        body {{ font-family: Arial, sans-serif; margin: 20px; text-align: center; }}
        .card {{ border: 1px solid #ddd; padding: 20px; border-radius: 10px; box-shadow: 2px 2px 10px rgba(0,0,0,0.1); max-width: 400px; margin: auto; }}
        .temp {{ font-size: 48px; font-weight: bold; color: #ff5722; }}
        .status {{ font-size: 24px; color: #4caf50; }}
        .status.off {{ color: #9e9e9e; }}
    </style>
</head>
<body>
    <div class="card">
        <h2>Yogurt Maker Controller</h2>
        <p>Current Temperature:</p>
        <p class="temp">{temp:.2f} &deg;C</p>
        <p>Heater Relay:</p>
        <p class="status {'off' if not relay_state else ''}">{state_str}</p>
        <p><small>Target: 41.5&deg;C - 42.5&deg;C</small></p>
    </div>
</body>
</html>
"""
    return html

def main():
    ip = connect_wifi()
    server_socket = start_server(ip)

    # Scan for DS18B20
    roms = scan_sensors()

    # Control parameters
    TARGET_TEMP_LOW = 41.5
    TARGET_TEMP_HIGH = 42.5
    current_temp = 0.0

    last_temp_read_time = utime.ticks_ms()
    temp_convert_started = False

    print("Starting control loop...")

    while True:
        # 1. Temperature reading state machine (non-blocking)
        now = utime.ticks_ms()
        
        if roms:
            if not temp_convert_started:
                if utime.ticks_diff(now, last_temp_read_time) > 2000: # Read every 2 seconds
                    try:
                        ds.convert_temp()
                        temp_convert_started = True
                        last_temp_read_time = now
                    except Exception as e:
                        print("Error starting temp conversion:", e)
            else:
                if utime.ticks_diff(now, last_temp_read_time) > 750: # Conversion takes ~750ms
                    try:
                        current_temp = ds.read_temp(roms[0])
                        temp_convert_started = False
                        
                        # 2. Control Logic
                        if current_temp < TARGET_TEMP_LOW:
                            relay_3.on()
                            led_buildin.on()
                        elif current_temp > TARGET_TEMP_HIGH:
                            relay_3.off()
                            led_buildin.off()
                            
                        print(f"Temp: {current_temp:.2f}C, Relay: {'ON' if relay_3.value() else 'OFF'}")
                    except Exception as e:
                        print("Error reading temp:", e)
                        temp_convert_started = False

        # 3. Web Server handling (non-blocking)
        if server_socket:
            try:
                client, addr = server_socket.accept()
                print('Client connected from', addr)
                client.settimeout(1.0) # short timeout for reading request
                try:
                    request = client.recv(1024)
                    # Send HTML response
                    html = get_html(current_temp, relay_3.value() == 1)
                    response = 'HTTP/1.0 200 OK\r\nContent-type: text/html\r\n\r\n' + html
                    client.send(response.encode('utf-8'))
                except Exception as e:
                    print("Error handling client:", e)
                finally:
                    client.close()
            except OSError as e:
                # EAGAIN or EWOULDBLOCK expected when no client is waiting
                pass

        utime.sleep_ms(10) # Small delay to prevent tight loop overhead

if __name__ == '__main__':
    main()