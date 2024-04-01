from machine import Pin
import utime
from machine import UART



uart = UART(1,baudrate=9600,tx=4,rx=5)
uart.init(9600,bits=8, parity = None, stop=1)

led_buildin = Pin("LED", Pin.OUT)	# they recoment to use inbuild LED 
utime.sleep_ms(500)

while True:
    #led_buildin.on()
    #utime.sleep_ms(200)
    #led_buildin.off()
    #utime.sleep_ms(200)
    uart.write(b"\xFE\x44\x00\x08\x02\x9F\x25")
    utime.sleep_ms(3000)
    data = uart.read(7)
    
    byte_3 = data[3]
    byte_4 = data[4]
    
    #print(byte_3,byte_4)
    #high = ord(data[3])
    #low = ord(data[4])
    value = (byte_3*256)+byte_4    
    #decoded_data = data.decode("utf-8")
    print(value)
    
    
    # readline part also waorks
    #uart.write(b"\xFE\x44\x00\x08\x02\x9F\x25")
    #data_line = uart.readline()
    #utime.sleep_ms(1000)
    #print(data_line)
    