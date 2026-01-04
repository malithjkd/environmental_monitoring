import machine
import utime

led_onboard = machine.Pin("LED",machine.Pin.OUT)

print("hello")

while True:
    led_onboard.off()
    utime.sleep_ms(150)
    led_onboard.on()
    utime.sleep_ms(150)
