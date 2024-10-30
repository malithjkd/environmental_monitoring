from machine import Pin
import utime
import network
import machine


while True:
    led_buildin.on()
    relay_2.on()
    utime.sleep_ms(500)
    led_buildin.off()
    relay_2.off()
    utime.sleep_ms(500)
