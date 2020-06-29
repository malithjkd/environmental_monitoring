
import Adafruit_DHT
import time

sensor = Adafruit_DHT.DHT11

pin = 4



while True:
    time.sleep(1)    

    humidity, temperature = Adafruit_DHT.read_retry(sensor, pin)

    if humidity is not None and temperature is not None:
        #print('Temp={0:0.1f}*C  Humidity={1:0.1f}%'.format(temperature, humidity))
        print "Temperature    = %d c" %int(temperature)
        print "Humidity leval = %d " %int(humidity)
    else:
        print("Failed to get reading. Try again!")
        



print "Malith"
