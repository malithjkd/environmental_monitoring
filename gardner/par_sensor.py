import minimalmodbus
import serial
import time

# --- CONFIGURATION ---
# Sensor: DFRobot SEN0641 (RS485 Photosynthetically Active Radiation Sensor)
# The Seeed Studio RS-485 Shield uses the Raspberry Pi hardware UART (/dev/serial0)
SERIAL_PORT = '/dev/serial0' 
SLAVE_ID = 1          # Default Modbus ID for most sensors
BAUD_RATE = 9600      # Default baud rate for SEN0641
REGISTER_ADDRESS = 0  # Replace with the exact register address from the SEN0641 datasheet if different
# ---------------------

def test_par_sensor():
    try:
        # Initialize the Modbus instrument
        sensor = minimalmodbus.Instrument(SERIAL_PORT, SLAVE_ID)
        
        # Configure serial communication parameters
        sensor.serial.baudrate = BAUD_RATE
        sensor.serial.bytesize = 8
        sensor.serial.parity   = serial.PARITY_NONE
        sensor.serial.stopbits = 1
        sensor.serial.timeout  = 1.0  # 1 second timeout

        print(f"Connecting to PAR Sensor on {SERIAL_PORT}...")
        print("Starting data read. Press Ctrl+C to stop.\n")

        while True:
            try:
                # Read 1 register (16-bit integer). 
                # Function code 3 (Holding Register) or 4 (Input Register) is standard.
                par_value = sensor.read_register(registeraddress=REGISTER_ADDRESS, number_of_decimals=0, functioncode=3)
                
                print(f"PAR Value: {par_value} μmol/m²/s")
                
            except IOError:
                print("Failed to read from sensor. Check wiring, power, and configuration.")
            except Exception as e:
                print(f"Unexpected error: {e}")
                
            time.sleep(1)

    except Exception as e:
        print(f"Initialization error: {e}")
        print("Ensure the USB-RS485 adapter is plugged in and the port name is correct.")

if __name__ == '__main__':
    test_par_sensor()
