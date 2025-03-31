from machine import Pin
import utime
import network
import machine

class controller():
    def __init__(self):
        #led_pin = Pin('WL_GPIO0',machine.Pin.OUT) # Inbuild LED pin number name
        led_buildin = Pin("LED", Pin.OUT)	# they recoment to use inbuild LED 
        relay_1 = Pin(15,Pin.OUT)
        relay_2 = Pin(16,Pin.OUT)
        

    #def blink(timer1):
    #    led.toggle()

    def blink(self):
        led.toggle()
        utime.sleep_ms(1000)
        led.toggle()
        utime.sleep_ms(1000)


    def IO_Control(self):
        while True:
            led_buildin.on()
            #relay_1.on()
            utime.sleep_ms(500)
    
            led_buildin.off()
            #relay_1.off()
            utime.sleep_ms(500)
        