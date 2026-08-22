from machine import Pin
import dht
import time

# DHT22 data pin connected to GPIO3
sensor = dht.DHT22(Pin(3))

while True:
    try:
        sensor.measure()
        temp = sensor.temperature()
        hum = sensor.humidity()
        print("Temperature: {}°C  Humidity: {}%".format(temp, hum))
    except OSError as e:
        print("Failed to read sensor:", e)
    
    time.sleep(2)  # DHT22 needs at least 2 sec between reads