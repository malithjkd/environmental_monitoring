import Adafruit_DHT
import time
from datetime import datetime

DHT_SENSOR = Adafruit_DHT.DHT22
DHT_PIN = 4

while True:
	file_name = datetime.now().strftime("%Y%m%d"+".txt")
	file = open(file_name,'a')
	humidity, temparature = Adafruit_DHT.read_retry(DHT_SENSOR,DHT_PIN)
	timestamp = datetime.now().strftime("%Y,%m,%d,%H,%M")
	if humidity is not None and temparature is not None:
		output_string = f'{timestamp},{temparature:.1f},{humidity:.1f}'
		#print("Temp = {0:.1f}*C , Humidity = {1:.1f}% ".format(temparature,humidity))
		print(output_string)
		file.write(output_string + '\n')
	else:
		print("Sensor faliure")

	file.close()
	time.sleep(60)
