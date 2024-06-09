import RPi.GPIO as GPIO
import time

def bin2dec(string_num): # define a function to convert a binary number to a decimal.
    return str(int(string_num, 2)) # return the string representing the integer value of the string passed to this function in base 2 (binary)

data = [] # define a data array

GPIO.setmode(GPIO.BCM) # use the Broadcom numbers instead of the WiringPi numbers

GPIO.setup(4,GPIO.OUT)  # Set it as an output so that we can:
GPIO.output(4,GPIO.HIGH) # write a 1
time.sleep(0.025) # for 25 ms
GPIO.output(4,GPIO.LOW) # then write a 0
time.sleep(0.02) # for 20 ms.
# I assume that the preceding sequence is the method to get the DHT sensor to respond with the current data.

GPIO.setup(4, GPIO.IN, pull_up_down=GPIO.PUD_UP) # Change the pin to read mode, with a pullup resistor

for i in range(0,500): # 501 times
    data.append(GPIO.input(4)) # read a bit from the GPIO, as fast as possible (no wait)

bit_count = 0
tmp = 0
count = 0
HumidityBit = ""
TemperatureBit = ""
crc = ""

try: # do this unless there's an error. If there's an error jump to "Except:"
   while data[count] == 1: # as long as you read a 1
      tmp = 1
      count = count + 1 # count how many 1s have been read

   for i in range(0, 32): # do this 33 times
      bit_count = 0 # reset the bit count each time

      while data[count] == 0: # as long as a 0 is read
         tmp = 1
         count = count + 1 # move on to the next bit

      while data[count] == 1: # as long as a 1 is read
         bit_count = bit_count + 1 # count how many 1s in a row
         count = count + 1 # move on to the next bit

      if bit_count > 3: # if there were mote than 3 * 1-bits in a row
         if i>=0 and i<8: # if we're in the first byte
            HumidityBit = HumidityBit + "1" # append a 1 to the humidity bitstring
         if i>=16 and i<24: # if we're in the 3rd byte
            TemperatureBit = TemperatureBit + "1" # add a 1 to the temperature bitstring
      else: # if there weren't at least 3 * 1-bits
         if i>=0 and i<8: # if we're in the first byte
            HumidityBit = HumidityBit + "0" # append a 0 to the humidity bitstring
         if i>=16 and i<24: # if we're in the 3rd byte
            TemperatureBit = TemperatureBit + "0" # append a 0 to the temperature bitstring

except: # if there was an error in the "try:" block
   print "ERR_RANGE" # report it
   exit(0) # end the program

try: # do this unless there's an error. If there's an error jump to "Except:"
   for i in range(0, 8): # do this 9 times
      bit_count = 0 # reset the bit counter

      while data[count] == 0: # as long as a 0 was read
         tmp = 1
         count = count + 1 # move on to the next bit

      while data[count] == 1: # as long as a 1 was read
         bit_count = bit_count + 1 # count how many 1s
         count = count + 1 # move on to the next bit

      if bit_count > 3: # if there were at least 3 * 1-bits
         crc = crc + "1" # add a 1 to the crc (Cyclic redundancy check) bitstring
      else: # if there were less than 3* 1-bits
         crc = crc + "0" # add a 0 to the crc bitstring
except: # if the "try:" block failed
   print "ERR_RANGE" # report it
   exit(0) # end program

Humidity = bin2dec(HumidityBit) # convert the binary bitstring to a decimal variable for humidity
Temperature = bin2dec(TemperatureBit) # convert the binary bitstring to a decimal variable for temperature

if int(Humidity) + int(Temperature) - int(bin2dec(crc)) == 0: # test whether the CRC indicates that the reading was good
   print Humidity # duh
   print Temperature # duh
else: # if the CRC check was bad
   print "ERR_CRC" # report it
# looks like there should be an "exit (0)" here that's missing. The program ends either way though. Usually the exit value indicates whether the program completed successfully.