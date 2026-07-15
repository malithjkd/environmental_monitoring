from machine import Pin
import utime
import network
import machine


#led_pin = Pin('WL_GPIO0',machine.Pin.OUT) # Inbuild LED pin number name
led_buildin = Pin("LED", Pin.OUT)	# they recoment to use inbuild LED 
relay_1 = Pin(13,Pin.OUT)
relay_2 = Pin(14,Pin.OUT)
relay_3 = Pin(15,Pin.OUT)


while True:
    led_buildin.on()
    relay_2.on()
    utime.sleep_ms(1500)
    led_buildin.off()
    relay_2.off()
    utime.sleep_ms(1500)