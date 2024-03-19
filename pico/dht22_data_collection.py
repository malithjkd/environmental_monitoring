from machine import Pin
import utime
import dht

led = Pin("LED", Pin.OUT)
sensor = dht.DHT22(Pin(22))
while True:
    led.on()
    utime.sleep_ms(100)
    led.off()
    sensor.measure()
    temp = sensor.temperature()
    hum = sensor.humidity()
    #print('Temperature: %.1f C' %temp)
    #print('Humidity: %.1f %%' %hum)
    print(utime.localtime(), 'Humidity: %.1f %%' %hum, 'Temperature: %.1f C' %temp) 
    
    #f = open('data.txt','a+')
    #f.write("%.1f ," %temp +  "%.1f" %hum + "\n")
    #f.close()
    utime.sleep_ms(4900)
    
