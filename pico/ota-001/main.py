from machine import Pin
import utime
import network
import machine

led_onboard = machine.Pin("LED",machine.Pin.OUT)

while True:
    led_onboard.on()
    utime.sleep_ms(500)
    led_onboard.off()
    utime.sleep_ms(500)
