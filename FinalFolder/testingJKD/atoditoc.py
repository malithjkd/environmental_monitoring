#!/usr/bin/python

import smbus
import time
 
bus = smbus.SMBus(1)

aout = 0

while True:
 
   for a in range(0,4):
      aout = aout + 1
      bus.write_byte_data(0x48,0x40 | ((a+1) & 0x03), aout)
      v = bus.read_byte(0x48)
      print v,
      time.sleep(0.1)
      #int(v)

   print
