from machine import Pin
import dht
import time

# Enable internal pull-up on the data pin as a safety net
data_pin = Pin(3, Pin.IN, Pin.PULL_UP)
sensor = dht.DHT22(data_pin)

time.sleep(2)  # let the sensor settle after power-up

while True:
    try:
        sensor.measure()
        temp = sensor.temperature()
        hum = sensor.humidity()
        print("Temperature: {}°C  Humidity: {}%".format(temp, hum))
    except OSError as e:
        print("Failed to read sensor:", e)
    
    time.sleep(2)  # DHT22 needs at least 2 sec between reads