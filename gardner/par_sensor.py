import os
import minimalmodbus
import serial
import time
import warnings

# Suppress the gpiozero fallback warnings for a cleaner output
warnings.filterwarnings("ignore", module="gpiozero")
from gpiozero import OutputDevice

class RS485Serial(serial.Serial):
    """
    Custom serial wrapper that toggles a GPIO pin for RS-485 flow control.
    The Seeed Studio shield requires GPIO 18 to be HIGH for TX and LOW for RX.
    """
    def __init__(self, *args, **kwargs):
        self.tx_enable_pin = kwargs.pop('tx_enable_pin', 18)
        self.tx_enable = OutputDevice(self.tx_enable_pin)
        self.tx_enable.off() # Start in RX mode
        super().__init__(*args, **kwargs)
        
    def write(self, b):
        self.reset_input_buffer() # Clear any junk bytes before we transmit
        self.tx_enable.on()  # Enable TX
        time.sleep(0.002)    # Brief pause to ensure line is ready
        res = super().write(b)
        self.flush()         # Wait until all data is written to OS buffer
        # Flush returns when the OS buffer is empty, but the UART shift register 
        # might still be sending the last byte. At 4800 baud, 1 byte takes ~2ms.
        time.sleep(0.005)    # Wait 5ms to ensure the last byte is fully on the wire
        self.tx_enable.off() # Switch back to RX
        return res

# --- CONFIGURATION ---
# Sensor: DFRobot SEN0641 (RS485 Photosynthetically Active Radiation Sensor)
SERIAL_PORT = '/dev/serial0' 
SLAVE_ID = 1          # Default Modbus ID for most sensors
REGISTER_ADDRESS = 0  # Replace with the exact register address from the SEN0641 datasheet if different
# ---------------------

def test_par_sensor():
    print(f"Testing connection to PAR Sensor on {SERIAL_PORT}...")
    baud_rates = [4800, 9600, 19200, 115200]
    
    for baud in baud_rates:
        print(f"\n--- Trying {baud} baud ---")
        try:
            sensor = minimalmodbus.Instrument(SERIAL_PORT, SLAVE_ID)
            sensor.serial.close() # Close the default serial connection
            
            # Replace with our custom RS-485 serial that toggles GPIO 18
            sensor.serial = RS485Serial(SERIAL_PORT)
            
            # Configure serial communication parameters
            sensor.serial.baudrate = baud
            sensor.serial.bytesize = 8
            sensor.serial.parity   = serial.PARITY_NONE
            sensor.serial.stopbits = 1
            sensor.serial.timeout  = 1.0  # 1 second timeout

            # Attempt to read 1 register (16-bit integer). 
            par_value = sensor.read_register(registeraddress=REGISTER_ADDRESS, number_of_decimals=0, functioncode=3)
            
            print(f"SUCCESS! PAR Value: {par_value} μmol/m²/s at {baud} baud.")
            
            print("\nContinuous read mode. Press Ctrl+C to stop.")
            while True:
                par_value = sensor.read_register(registeraddress=REGISTER_ADDRESS, number_of_decimals=0, functioncode=3)
                print(f"PAR Value: {par_value} μmol/m²/s")
                time.sleep(1)
                
        except IOError as e:
            print(f"Failed at {baud} baud: {e}")
        except Exception as e:
            print(f"Unexpected error at {baud} baud: {e}")
            
    print("\nCould not connect to sensor on any standard baud rate.")
    print("If you see 'returned no data (device disconnected or multiple access on port)'")
    print("Please make sure you have DISABLED the Serial Console via `sudo raspi-config`!")

if __name__ == '__main__':
    test_par_sensor()
