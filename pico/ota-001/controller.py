from machine import Pin
import utime
import network
import machine
from machine import Timer

led_buildin = Pin("LED", Pin.OUT)
relay_1 = Pin(7,Pin.OUT)
relay_2 = Pin(8,Pin.OUT)

timer1 = machine.Timer()


class controller():
    def __init__(self):
        print("Controller initialized")
        pass
 
        
    def blink(self,timer1):
        led_buildin.toggle()
        relay_1.toggle()
        


    def IO_Control(self):
        while True:
            led_buildin.on()
            #relay_1.on()
            utime.sleep_ms(200)
    
            led_buildin.off()
            #relay_1.off()
            utime.sleep_ms(200)
        


    def controller_start(self):
        # Initialize the controller
        print("Controller initialized")
        timer1.init(freq=1, mode=machine.Timer.PERIODIC, callback=self.blink)
    
    def controller_stop(self):
        # Stop the controller
        print("Controller stopped")
        timer1.deinit()