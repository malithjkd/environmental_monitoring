from machine import Pin
import ntptime
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


    def control_relay_based_on_time(self):
        try:
            # Sync time with NTP server
            ntptime.settime()
            
            # Get the current time
            current_time = utime.localtime()
            print("Current time:", current_time)
            
            hour = current_time[3] + 8  # Extract the hour from the time tuple and convert it to singapore time
            hour = hour % 24 
            # Check if the current time is between 21:00 and 11:00
            if 9 <= hour < 10 or 6 <= hour < 9:
                relay_1.on()  # Turn on relay_1
                print("Relay 1 is ON")
            #elif 6 <= hour < 8:
            #    relay_1.on()  # Turn on relay_1
            #    print("Relay 1 is ON")
            else:
                relay_1.off()  # Turn off relay_1
                print("Relay 1 is OFF")
        except Exception as e:
            print("Failed to control relay based on time:", e)
            

    def controller_start(self):
        # Initialize the controller
        print("Controller initialized")
        timer1.init(freq=1, mode=machine.Timer.PERIODIC, callback=self.blink)
        self.control_relay_based_on_time()
    
    def controller_stop(self):
        # Stop the controller
        print("Controller stopped")
        timer1.deinit()
        
        



# test code 
#test_controller = controller()
#test_controller.controller_start()

