#!/usr/bin/python

import smbus
import time
 
bus = smbus.SMBus(1)

aout = 0
count = 0
while count <=10:

    aout = aout +1
    bus.write_byte_data(0x48,0x40 | (0 & 0x03), aout)
    v1 = bus.read_byte(0x48)
    bus.write_byte_data(0x48,0x40 | (2 & 0x03), aout)
    v2 = bus.read_byte(0x48)
    print "%d |%d" %(v2,v2)
    
    time.sleep(0.5)

