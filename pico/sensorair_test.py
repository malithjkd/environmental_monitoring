# Raspberry pi pico w (micropython) UART communication with Sensorair S8
# 2024.04.02
# Malithjkd

# import packages
from machine import Pin
import utime
from machine import UART

# Pins used
uart = UART(1,baudrate=9600,tx=4,rx=5)
uart.init(9600,bits=8, parity = None, stop=1)

led_buildin = Pin("LED", Pin.OUT)	# they recoment to use inbuild LED 
utime.sleep_ms(500)

while True:

    uart.write(b"\xFE\x44\x00\x08\x02\x9F\x25")
    utime.sleep_ms(3000)
    data = uart.read(7)
    #print(data)
    byte_3 = data[3]
    byte_4 = data[4]
    
    value = (byte_3*256)+byte_4    
    print(value)
    