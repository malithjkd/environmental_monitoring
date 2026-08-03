from machine import UART, Pin
import utime

# Initialize UART for CO2 sensor (using the same pins as air_quality_control.py)
uart = UART(1, baudrate=9600, tx=4, rx=5)
uart.init(9600, bits=8, parity=None, stop=1)

# Status LED
pico_led = Pin("LED", Pin.OUT)

def read_co2_value():
    # Send command to read CO2
    uart.write(b"\xFE\x44\x00\x08\x02\x9F\x25")
    
    # Wait for sensor to respond
    utime.sleep_ms(3000)
    
    # Read 7 bytes of data
    data = uart.read(7)
    
    if data is not None and len(data) >= 5:
        byte_3 = data[3]
        byte_4 = data[4]
        value = (byte_3 * 256) + byte_4    
        return value
    else:
        return -1

def main():
    print("CO2 USB Sender started.")
    print("Waiting for sensor to warm up...")
    utime.sleep(7)
    
    while True:
        pico_led.on()
        co2_val = read_co2_value()
        pico_led.off()
        
        if co2_val != -1:
            # Output in a structured format so Pi 5 can parse it easily
            print(f"CO2:{co2_val}")
        else:
            print("CO2:ERROR")
            
        utime.sleep(12) # 2 seconds between readings, +3s reading time = ~15s total loop

if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print("Program stopped.")
