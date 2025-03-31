from machine import Pin
import utime
import network
import machine

led_buildin = Pin("LED", Pin.OUT)
relay_1 = Pin(15,Pin.OUT)
relay_2 = Pin(16,Pin.OUT)
        

class controller():
    def __init__(self):
        print("Controller initialized")
        pass
 
        

    #def blink(timer1):
    #    led.toggle()

    def blink(self):
        led_buildin.toggle()
        utime.sleep_ms(1000)
        led_buildin.toggle()
        utime.sleep_ms(1000)


    def IO_Control(self):
        while True:
            led_buildin.on()
            #relay_1.on()
            utime.sleep_ms(200)
    
            led_buildin.off()
            #relay_1.off()
            utime.sleep_ms(200)
        
