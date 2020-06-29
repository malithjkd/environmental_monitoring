

#!/usr/bin/python

import MySQLdb

# Open database connection
db = MySQLdb.connect("localhost","root","1234","serverroom" )

# prepare a cursor object using cursor() method
cursor = db.cursor()

# Prepare SQL query to INSERT a record into the database.






sq1 = """INSERT INTO sensordata(sensorId,sensorValue, time) VALUES (1, 23, now())"""

try:
   # Execute the SQL command

   # Commit your changes in the database
   db.commit()
except:
   # Rollback in case there is any error
   db.rollback()

# disconnect from server
db.close()

