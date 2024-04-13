import machine
import utime

led_onboard = machine.Pin("LED",machine.Pin.OUT)

print("hello")

while True:
    led_onboard.off()
<<<<<<< HEAD
    utime.sleep_ms(150)
    led_onboard.on()
=======
    #print("1")
    utime.sleep_ms(150)
    led_onboard.on()
    #print("0")
>>>>>>> refs/remotes/origin/master
    utime.sleep_ms(150)
