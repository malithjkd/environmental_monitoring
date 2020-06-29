
import MySQLdb
import RPi.GPIO as GPIO 
import Adafruit_DHT
import time
import smbus

sensor = Adafruit_DHT.DHT11
pin = 4

GPIO.setmode(GPIO.BCM)
INPUT_PIN = 17
GPIO.setup(INPUT_PIN, GPIO.IN)

bus = smbus.SMBus(1)

db = MySQLdb.connect("localhost","root","1234","serverroom" )
cursor = db.cursor()

aout = 0
count = 0
while count <= 30:
    time.sleep(.1)
    humidity, temperature = Adafruit_DHT.read_retry(sensor, pin)

    if humidity is not None and temperature is not None:
        sq1 = "INSERT INTO sensordata(sensorId,sensorValue, time) VALUES (1, %s, now())"
        sq2 = "INSERT INTO sensordata(sensorId,sensorValue, time) VALUES (2, %s, now())"
        count = count +1
        

    else:
        print "error on dht11 sensor data"

    if (GPIO.input(INPUT_PIN) == True):
        smoke = 0
        sq3 = "INSERT INTO sensordata(sensorId,sensorValue, time) VALUES (3, %s, now())"
    else:
        smoke = 1
        sq3 = "INSERT INTO sensordata(sensorId,sensorValue, time) VALUES (3, %s, now())"

    aout = aout +1
    bus.write_byte_data(0x48,0x40 | (0 & 0x03), aout)
    light = bus.read_byte(0x48)
    sq4 = "INSERT INTO sensordata(sensorId,sensorValue, time) VALUES (4, %s, now())"
    bus.write_byte_data(0x48,0x40 | (2 & 0x03), aout)
    water = bus.read_byte(0x48)
    sq5 = "INSERT INTO sensordata(sensorId,sensorValue, time) VALUES (5, %s, now())"
    

    print "%d | %d | %d | %d | %d | %d" %(count, temperature, humidity, smoke, light, water)
        
    try:
       cursor.execute(sq1,temperature)
       cursor.execute(sq2,humidity)
       cursor.execute(sq3,smoke)
       cursor.execute(sq4,light)
       cursor.execute(sq5,water)
       
       db.commit()
       time.sleep(.5)
    except:
       db.rollback()

db.close()





    
