from machine import Pin
from machine import Timer
import utime
from time import sleep
import network
import socket
from controller import blink # import blink function from OTA update file

led = Pin("LED", Pin.OUT)
timer1 = Timer()
timer2 = Timer()

def blink(timer1):
    led.toggle()

#timer.init(freq=0.1, mode=Timer.PERIODIC, callback=blink)


def blink2():
    # check WIFI is connected
    wlan = network.WLAN(network.STA_IF)
    wlan.active(True)

    for x in range (0,10):
        led.on()
        utime.sleep_ms(100)
        led.off()
        utime.sleep_ms(100)



def interrupt_controller(timer2):
    timer1.deinit()
    blink2()
    timer1.init(freq=1, mode=Timer.PERIODIC, callback=blink)
   
timer2.init(freq=0.01, mode=Timer.PERIODIC, callback=interrupt_controller)

