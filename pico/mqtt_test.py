# Raspberry pi pico w (micropython) UART communication with Sensorair S8
# 2024.04.02
# Malithjkd

# https://forums.raspberrypi.com/viewtopic.php?t=344546
# import packages
import network
from machine import Pin
import utime
from machine import UART
from umqtt.simple import MQTTClient    # for mqtt


# wifi user access
ssid = 'NinjaWarriers'
password = 'Boys1234'

# Pins used
uart = UART(1,baudrate=9600,tx=4,rx=5)
uart.init(9600,bits=8, parity = None, stop=1)

led_buildin = Pin("LED", Pin.OUT)	# they recoment to use inbuild LED 
utime.sleep_ms(500)


# MQTT user

mqtt_server = '192.168.1.126'
client_id = 'pico1'
topic_pub = b'co2value'
topic_msg = b'Testmessage'



def connect(ssid, password): # Connect to network
    wlan = network.WLAN(network.STA_IF)
    wlan.active(True)

    wlan.connect(ssid, password)

    for x in range(1,70):
        if wlan.isconnected() == False:
            print('Waiting for connection...')
            utime.sleep_ms(300)
            led_buildin.on()
        else:
            ip = wlan.ifconfig()[0]
            print(wlan.ifconfig())
            print(f'Connected on {ip}')
            led_buildin.off()
            utime.sleep_ms(300)
            led_buildin.on()
            utime.sleep_ms(300)
            led_buildin.off()
            break
        x = x+1
    
    return ip



def mqtt_connect():
    client = MQTTClient(client_id, mqtt_server, keepalive=3600)
    client.connect()
    print('Connected to %s MQTT Broker'%(mqtt_server))
    return client





ip=connect(ssid, password)
print(ip)

utime.sleep_ms(500)

client = mqtt_connect()


while True:

    uart.write(b"\xFE\x44\x00\x08\x02\x9F\x25")
    utime.sleep_ms(3000)
    data = uart.read(7)
    #print(data)
    byte_3 = data[3]
    byte_4 = data[4]
    
    value = (byte_3*256)+byte_4    
    print(value)
    client.publish(topic_pub,str(value))
    
    
    