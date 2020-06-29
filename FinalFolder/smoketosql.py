#!/usr/bin/env python

import MySQLdb

db = MySQLdb.connect("localhost","root","1234","serverroom")
cursor = db.cursor()


smoke = 0

from time import sleep           # Allows us to call the sleep function to slow down our loop
import RPi.GPIO as GPIO           # Allows us to call our GPIO pins and names it just GPIO
 
GPIO.setmode(GPIO.BCM)           # Set's GPIO pins to BCM GPIO numbering
INPUT_PIN = 17           # Sets our input pin, in this example I'm connecting our button to pin 4. Pin 0 is the SDA pin so I avoid using it for sensors/buttons
GPIO.setup(INPUT_PIN, GPIO.IN)           # Set our input pin to be an input

# Start a loop that never ends
cycle = 0
while cycle <= 100: 
    if (GPIO.input(INPUT_PIN) == True): 
        smoke = 0
        print "val = %d" %smoke
                    
    else:
        smoke = 1
        print "val = %d" %smoke

    sq1 = """INSERT INTO sensordata(sensorId,sensorValue, time) VALUES (1, smoke, now())"""

    try:
        # Execute the SQL command
        cursor.execute(sq1)
        # Commit your changes in the database
        db.commit()
    except:
        # Rollback in case there is any error
        db.rollback()

    cycle = cycle +1
    sleep(1);
        
#disconnect from the server
db.close()
