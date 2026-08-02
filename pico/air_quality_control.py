import network
import socket
from time import sleep
import machine
import utime
import dht
from machine import UART
import secrets

#pico inbuild 
pico_led = machine.Pin("LED",machine.Pin.OUT)
adcpin = 4
sensor = machine.ADC(adcpin)

# Pins used
uart = UART(1,baudrate=9600,tx=4,rx=5)
uart.init(9600,bits=8, parity = None, stop=1)

# relays
relay_1 = machine.Pin(12,machine.Pin.OUT)
relay_2 = machine.Pin(13,machine.Pin.OUT)

# DHT22 sensor on GPIO2 (data pin) with internal pull-up
dht22_pin = machine.Pin(2, machine.Pin.IN, machine.Pin.PULL_UP)
dht22_sensor = dht.DHT22(dht22_pin)




pico_led.off()
relay_1.off()
relay_2.off()

# DHT22 needs ~2 seconds after power-on before first read
print("Waiting for DHT22 warm-up...")
utime.sleep_ms(2000)

def read_temperature_value():
    adc_value = sensor.read_u16()
    volt = (3.3/65535) * adc_value
    temperature = 27 - (volt - 0.706)/0.001721
    return round(temperature, 1)


def read_co2_value():
    uart.write(b"\xFE\x44\x00\x08\x02\x9F\x25")
    utime.sleep_ms(3000)
    data = uart.read(7)
    #print(data)
    
    # Check if data is valid before parsing
    if data is not None and len(data) >= 5:
        byte_3 = data[3]
        byte_4 = data[4]
        
        value = (byte_3*256)+byte_4    
    #    print(value)
        return(value)
    else:
        print("Warning: CO2 sensor returned no data (is it connected?)")
        return -1

def connect(): # Connect to network
    wlan = network.WLAN(network.STA_IF)
    wlan.active(True)

    for network_info in secrets.WIFI_NETWORKS:
        ssid = network_info['ssid']
        password = network_info['password']
        print(f"Trying to connect to {ssid}...")
        wlan.connect(ssid, password)

        connected = False
        for x in range(1, 20): # wait up to 20 seconds per network
            if wlan.isconnected():
                connected = True
                break
            print('Waiting for connection...')
            sleep(1)
            pico_led.on()
            
        if connected:
            ip = wlan.ifconfig()[0]
            print(wlan.ifconfig())
            print(f'Connected on {ip}')
            pico_led.off()
            utime.sleep_ms(500)
            pico_led.on()
            utime.sleep_ms(500)
            pico_led.off()
            return ip
        else:
            print(f"Failed to connect to {ssid}")

        # Reconnect after 5 seconds

        pico_led.on()
        utime.sleep_ms(100)
        pico_led.off()
        utime.sleep_ms(100)
        pico_led.on()
        sleep(50)
        pico_led.off()
    
    raise RuntimeError("Could not connect to any configured WiFi networks")

def open_socket(ip):
    # Open a socket
    address = (ip, 80)
    connection = socket.socket()
    connection.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    connection.bind(address)
    connection.listen(1)
    #print(connection)
    return connection


def webpage(temperature, state, co2_value):
    #Template HTML
    
    # Format DHT22 values (handle None when sensor fails)
    # dht_temp_str = f"{dht22_temp} &deg;C" if dht22_temp is not None else "Sensor Error"
    # dht_hum_str = f"{dht22_hum} %" if dht22_hum is not None else "Sensor Error"
    
    html = f"""
            <!DOCTYPE html>
            <html>
            <head>
            <title>Pico Environmental Monitor</title>
            <meta name="viewport" content="width=device-width, initial-scale=1">
            </head>
            <body>
            <h2>Environmental Monitor</h2>
            <h3>Sensor Readings</h3>
            <p><b>Pico Internal Temp:</b> {temperature} &deg;C</p>
            <p><b>CO2 Value:</b> {co2_value} ppm</p>
            <hr>
            <h3>Controls</h3>
            <p>LED is {state}</p>
            
            <form action="./lighton">
            <input type="submit" value="Light on" />
            </form>
            <form action="./lightoff">
            <input type="submit" value="Light off" />
            </form>
            <form action="./lightblink">
            <input type="submit" value="Light Blink" />
            </form>
            
            <form action="./led2on">
            <input type="submit" value="Light2 on" />
            </form>
            <form action="./led2off">
            <input type="submit" value="Light2 off" />
            </form>
            <form action="./led2blink">
            <input type="submit" value="Light2 Blink" />
            </form>
            
            <form action="./led3on">
            <input type="submit" value="Light3 on" />
            </form>
            <form action="./led3off">
            <input type="submit" value="Light3 off" />
            </form>
           <form action="./led3blink">
            <input type="submit" value="Light3 Blink" />
            </form> 
            
            </body>
            </html>
            """
    return str(html)


def serve(connection):
    #Start a web server
    state = 'OFF'
    pico_led.off()
    temperature = 0
    print("server is on ")
    while True:
        client = connection.accept()[0]
        request = client.recv(1024)
        request = str(request)
        try:
            request = request.split()[1]
        except IndexError:
            pass
        if request == '/lighton?':
            pico_led.on()
            state = 'ON'  
        elif request =='/lightoff?':
            pico_led.off()
            state = 'OFF'
        elif request =='/lightblink?':
            pico_led.on()
            utime.sleep_ms(500)
            pico_led.off()
            state = 'LED 0 Blinked'
            
        elif request == '/led2on?':
            relay_1.on()
            state = 'DIO 1 ON'
        elif request =='/led2off?':
            relay_1.off()
            state = 'DIO 1 OFF'
        elif request =='/led2blink?':
            relay_1.on()
            utime.sleep_ms(500)
            relay_1.off()
            state = 'DIO 1 Blinked'
            
        elif request == '/led3on?':
            relay_2.on()
            state = 'DIO 2 ON'
        elif request =='/led3off?':
            relay_2.off()
            state = 'DIO 2 OFF'
        elif request =='/led3blink?':
            relay_2.on()
            utime.sleep_ms(500)
            relay_2.off()
            state = 'DIO 2 Blinked'
        temperature = read_temperature_value()
        co2_value = read_co2_value()
        html = webpage(temperature, state, co2_value)
        client.send(html)
        client.close()


# main

try: 
    ip = connect()
    connection = open_socket(ip)
    print("connection is finished")
    serve(connection)
except KeyboardInterrupt:
    machine.reset()


