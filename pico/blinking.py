from machine import Pin
import utime
import network
import machine 

#led_pin = Pin('WL_GPIO0',machine.Pin.OUT) # Inbuild LED pin number name
led_buildin = Pin("LED", Pin.OUT)	# they recoment to use inbuild LED 
relay_1 = Pin(15,Pin.OUT)
relay_2 = Pin(16,Pin.OUT)

ssid = 'osiris-sg'
password = 'bbppu35643'

# Connect to network
def connect():
    wlan = network.WLAN(network.STA_IF)
    wlan.active(True)
    wlan.connect(ssid, password)
    utime.sleep_ms(1000)
    for x in range(1,50):
        if wlan.isconnected() == False:
            print('Waiting for connection...')
            utime.sleep_ms(1000)
        else:
            ip = wlan.ifconfig()[0]
            print(f'Connected on {ip}')
            break
        x = x+1
