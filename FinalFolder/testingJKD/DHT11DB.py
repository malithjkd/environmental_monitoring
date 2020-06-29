
import MySQLdb

import Adafruit_DHT
import time

sensor = Adafruit_DHT.DHT11

pin = 4

db = MySQLdb.connect("localhost","root","1234","serverroom" )
cursor = db.cursor()

count = 0
while count <= 50:
    time.sleep(.1)
    humidity, temperature = Adafruit_DHT.read_retry(sensor, pin)

    if humidity is not None and temperature is not None:
        sq1 = "INSERT INTO sensordata(sensorId,sensorValue, time) VALUES (1, %s, now())"
        sq2 = "INSERT INTO sensordata(sensorId,sensorValue, time) VALUES (2, %s, now())"
        print "%d | %d | %d" %(count, temperature, humidity)
        count = count +1
        time.sleep(1)    

    try:
       cursor.execute(sq1,temperature)
       cursor.execute(sq2,humidity)
       db.commit()
    except:
       db.rollback()

db.close()





    
