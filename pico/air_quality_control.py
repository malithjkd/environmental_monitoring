import network
import socket
from time import sleep
import machine
import utime
import dht
from machine import UART

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



pico_led.off()
relay_1.off()
relay_2.off()
#ssid = 'Guests'
#password = 'Welcome2PBA'

ssid = 'NinjaWarriers'
password = 'Boys1234'

#ssid = 'Pixel_7461'
#password = 'nevergiveup154'

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
    byte_3 = data[3]
    byte_4 = data[4]
    
    value = (byte_3*256)+byte_4    
#    print(value)
    return(value)

def connect(ssid, password): # Connect to network
    wlan = network.WLAN(network.STA_IF)
    wlan.active(True)

    wlan.connect(ssid, password)

    for x in range(1,70):
        if wlan.isconnected() == False:
            print('Waiting for connection...')
            sleep(1)
            pico_led.on()
        else:
            ip = wlan.ifconfig()[0]
            print(wlan.ifconfig())
            print(f'Connected on {ip}')
            pico_led.off()
            utime.sleep_ms(300)
            pico_led.on()
            utime.sleep_ms(300)
            pico_led.off()
            break
        x = x+1
    
    return ip

def open_socket(ip):
    # Open a socket
    address = (ip, 80)
    connection = socket.socket()
    connection.bind(address)
    connection.listen(1)
    #print(connection)
    return connection


def webpage(temperature, state,co2_value):
    #Template HTML
    html = f"""
            <!DOCTYPE html>
            <html>
            <form action="./lighton">
            <input type="submit" value="Light on" />
            </form>
            <form action="./lightoff">
            <input type="submit" value="Light off" />
            </form>
            <form action="./lightblink">
            <input type="submit" value="Light Blink" />
            </form>
            <p>LED is {state}</p>
            
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
            
           <p>Temperature is {temperature}</p>
           <p>CO2 value is {co2_value}</p>
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
        html = webpage(temperature, state,co2_value)
        client.send(html)
        client.close()


# main

try: 
    ip = connect(ssid, password)
    connection = open_socket(ip)
    print("connection is finished")
    serve(connection)
except KeyboardInterrupt:
    machine.reset()


