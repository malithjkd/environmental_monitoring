# Content: 
# Pico tents to disconnect after ideling if its disconnected we have to reconnect automatically
# Code is trying to check the connection status and tryied to reconnect it if its not connected
# 
# 2025.02.24
# Malithkd


import network
import socket
from time import sleep
import machine

pico_led = machine.Pin("LED",machine.Pin.OUT)
adcpin = 4
sensor = machine.ADC(adcpin)

ssid = 'NinjaWarriers'
password = 'Boys1234'

def ReadTemperature():
    adc_value = sensor.read_u16()
    volt = (3.3/65535) * adc_value
    temperature = 27 - (volt - 0.706)/0.001721
    return round(temperature, 1)

def connect():
    #Connect to WLAN
    wlan = network.WLAN(network.STA_IF)
    wlan.active(True)
    count = 0 
    while count < 30:
        wlan.connect(ssid, password)
        if wlan.isconnected() == False:
            print(f"Attempt {count} to connect... ")
            sleep(1)
            pico_led.on()
            count  = count +1
        else:
            count = 60
    
    if count == 30:
        print("Connection apptemp failed")
        ip = 0
        pico_led.off()
        sleep(60)
        ip = connect()
    else:
        ip = wlan.ifconfig()[0]
        print("Connection Successfull !")
        print(f'Connected on {ip}')
        pico_led.off()
        
    return ip

def open_socket(ip):
    # Open a socket
    address = (ip, 80)
    connection = socket.socket()
    connection.bind(address)
    connection.listen(1)
    return connection


def webpage(temperature, state):
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
            <p>LED is {state}</p>
           <p>Temperature is {temperature}</p>
            </body>
            </html>
            """
    return str(html)


def serve(connection):
    #Start a web server
    state = 'OFF'
    pico_led.off()
    temperature = 0
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
        temperature = ReadTemperature() 
        html = webpage(temperature, state)
        client.send(html)
        client.close()


# main function
wlan = network.WLAN(network.STA_IF)
wlan.active(True)
while True:
    try:
        if wlan.isconnected() == False:
            ip = connect()
        else:
            connection = open_socket(ip)
            serve(connection)
    except KeyboardInterrupt:
        machine.reset()
    
    

