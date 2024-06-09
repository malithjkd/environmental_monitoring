# take pic

from time import sleep
from picamera import PiCamera
from datetime import datetime

date = datetime.now()
years = "%04d" % date.year
months = "%02d" % date.month
dates = "%02d" % date.day
hours = "%02d" % date.hour
mint = "%02d" % date.minute
sec = "%02d" % date.second
pic_name = str(years)+str(months)+str(dates)+str(hours)+str(mint)+str(sec)+'.jpg'	# extention .mjpeg or .h264

camera = PiCamera()
camera.rotation = 180
#camera.resolution = (1024,768)
camera.resolution = (2592, 1944)
camera.start_preview()
sleep(2)
#camera.capture(pic_name)
camera.capture('1_1_1.jpg')
