import RPi.GPIO as GPIO
import time

# Use BCM GPIO references instead of physical pin numbers
GPIO.setmode(GPIO.BCM)

# Set up GPIO pins
output_pins = [17, 18, 27]  # List of GPIO pin numbers to be used as outputs

# Set all pins as output and initialize to LOW
for pin in output_pins:
    GPIO.setup(pin, GPIO.OUT)
    GPIO.output(pin, GPIO.LOW)


for pin in output_pins:
    GPIO.output(pin, GPIO.HIGH)
    print("Pin number: ",pin," is HIGH")
    time.sleep(3)
    GPIO.output(pin, GPIO.LOW)
    print("Pin number: ",pin," is LOW")
    time.sleep(3)


# Clean up GPIO settings before exiting
GPIO.cleanup()
print("GPIO cleanup completed")