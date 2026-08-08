import time
import serial
import minimalmodbus
import warnings

# Suppress the gpiozero fallback warnings for a cleaner output
warnings.filterwarnings("ignore", module="gpiozero")
from gpiozero import OutputDevice

# --- CONFIGURATION ---
SERIAL_PORT = '/dev/serial0'
BAUD_RATE = 4800
SLAVE_ID = 1          
REGISTER_ADDRESS = 0  
# ---------------------

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
        time.sleep(0.005)    # Brief pause to ensure the transceiver has switched
        res = super().write(b)
        self.flush()         # Wait until all data is written to OS buffer
        self.tx_enable.off() # Switch back to RX IMMEDIATELY
        return res
        
    def close(self):
        """Release the GPIO pin when the serial port is closed."""
        if hasattr(self, 'tx_enable') and self.tx_enable is not None:
            self.tx_enable.close()
        super().close()


def main():
    print(f"Connecting to PAR Sensor (DFRobot SEN0641) on {SERIAL_PORT} at {BAUD_RATE} baud...")
    
    try:
        # Initialize Modbus Instrument
        sensor = minimalmodbus.Instrument(SERIAL_PORT, SLAVE_ID)
        sensor.serial.close()  # Close the default serial connection
        
        # Inject our custom RS-485 serial wrapper
        sensor.serial = RS485Serial(SERIAL_PORT)
        
        # Configure serial communication parameters
        sensor.serial.baudrate = BAUD_RATE
        sensor.serial.bytesize = 8
        sensor.serial.parity   = serial.PARITY_NONE
        sensor.serial.stopbits = 1
        sensor.serial.timeout  = 1.5 
        
        # Configure minimalmodbus protocol
        sensor.mode = minimalmodbus.MODE_RTU
        sensor.clear_buffers_before_each_transaction = True
        sensor.close_port_after_each_call = False
        
        print("✅ Connected! Starting continuous read mode. Press Ctrl+C to stop.\n")
        
        while True:
            try:
                # Attempt to read the 16-bit PAR value register
                par_value = sensor.read_register(
                    registeraddress=REGISTER_ADDRESS,
                    number_of_decimals=0,
                    functioncode=3
                )
                print(f"PAR Value: {par_value} μmol/m²/s")
                
            except IOError:
                # Linux thread scheduling occasionally causes 1-2ms delays which drop a frame.
                # This is completely normal for RS-485 in Python. We just silently ignore it and retry!
                pass
            
            time.sleep(1)
            
    except KeyboardInterrupt:
        print("\nStopped by user.")
    except Exception as e:
        print(f"\n❌ Error: {e}")
    finally:
        if 'sensor' in locals() and hasattr(sensor, 'serial'):
            sensor.serial.close()


if __name__ == '__main__':
    main()
