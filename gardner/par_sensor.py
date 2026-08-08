import os
import minimalmodbus
import serial
import time
import struct
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
        time.sleep(0.005)    # Brief pause to ensure the transceiver has switched
        res = super().write(b)
        self.flush()         # Wait until all data is written to OS buffer
        self.tx_enable.off() # Switch back to RX IMMEDIATELY
        return res


# --- CONFIGURATION ---
# Sensor: DFRobot SEN0641 (RS485 Photosynthetically Active Radiation Sensor)
SERIAL_PORT = '/dev/serial0' 
SLAVE_ID = 1          # Default Modbus ID for most sensors (factory default 0x01)
REGISTER_ADDRESS = 0  # Register 0x0000 = PAR value (from datasheet)
# ---------------------


def crc16_modbus(data):
    """Calculate Modbus CRC16 for a byte sequence."""
    crc = 0xFFFF
    for byte in data:
        crc ^= byte
        for _ in range(8):
            if crc & 0x0001:
                crc >>= 1
                crc ^= 0xA001
            else:
                crc >>= 1
    return crc


def raw_serial_test(port, baud, slave_id=1):
    """
    Send a raw Modbus RTU request and inspect the response bytes directly.
    This bypasses minimalmodbus to help diagnose timing and wiring issues.
    
    Request: Read 1 register starting at address 0x0000
    Frame:   [addr] [func=0x03] [reg_hi] [reg_lo] [count_hi] [count_lo] [crc_lo] [crc_hi]
    """
    # Build the Modbus request frame
    request = struct.pack('>BBHH', slave_id, 0x03, 0x0000, 0x0001)
    crc = crc16_modbus(request)
    request += struct.pack('<H', crc)  # CRC is little-endian in Modbus
    
    tx_enable = OutputDevice(18)
    tx_enable.off()
    
    try:
        ser = serial.Serial(
            port=port,
            baudrate=baud,
            bytesize=8,
            parity=serial.PARITY_NONE,
            stopbits=1,
            timeout=1.5
        )
        
        # Drain any stale data
        ser.reset_input_buffer()
        time.sleep(0.05)
        ser.reset_input_buffer()
        
        # TX: Enable driver, send frame, wait for completion, then switch to RX
        tx_enable.on()
        time.sleep(0.005)
        
        ser.write(request)
        ser.flush()
        tx_enable.off() # IMMEDIATELY switch to RX
        
        # RX: Wait for response. Expected 7 bytes for a single register read.
        # Give the sensor plenty of time to respond.
        time.sleep(0.1)
        response = ser.read(32)  # Read up to 32 bytes
        
        ser.close()
        
        print(f"  TX frame : {request.hex(' ')}")
        print(f"  RX bytes : {response.hex(' ') if response else '(no data)'}")
        print(f"  RX length: {len(response)} bytes")
        
        if len(response) >= 7:
            addr = response[0]
            func = response[1]
            byte_count = response[2]
            data = int.from_bytes(response[3:3+byte_count], 'big')
            rx_crc = int.from_bytes(response[-2:], 'little')
            calc_crc = crc16_modbus(response[:-2])
            
            print(f"  Parsed => addr={addr}, func=0x{func:02x}, byte_count={byte_count}, data={data}")
            print(f"  CRC rx=0x{rx_crc:04x}, calc=0x{calc_crc:04x} => {'OK ✓' if rx_crc == calc_crc else 'MISMATCH ✗'}")
            
            if rx_crc == calc_crc:
                return data
        elif len(response) > 0:
            print(f"  ⚠ Received only {len(response)} bytes — possible timing or wiring issue.")
            print(f"  Hint: Check that A/B wires are not swapped, and that the serial console is disabled.")
        else:
            print(f"  ⚠ No response received.")
            
        return None
        
    except Exception as e:
        print(f"  Error: {e}")
        return None
    finally:
        tx_enable.off()
        tx_enable.close()


def test_with_minimalmodbus(port, baud, slave_id=1):
    """Test using minimalmodbus library (standard Modbus RTU)."""
    sensor = minimalmodbus.Instrument(port, slave_id)
    sensor.serial.close()  # Close the default serial connection
    
    # Replace with our custom RS-485 serial that toggles GPIO 18
    sensor.serial = RS485Serial(port)
    
    # Configure serial communication parameters (from SEN0641 datasheet)
    sensor.serial.baudrate = baud
    sensor.serial.bytesize = 8
    sensor.serial.parity   = serial.PARITY_NONE
    sensor.serial.stopbits = 1
    sensor.serial.timeout  = 1.5  # generous timeout
    
    # Configure minimalmodbus
    sensor.mode = minimalmodbus.MODE_RTU
    sensor.clear_buffers_before_each_transaction = True
    sensor.close_port_after_each_call = False
    
    # Attempt to read 1 register (16-bit integer)
    par_value = sensor.read_register(
        registeraddress=REGISTER_ADDRESS, 
        number_of_decimals=0, 
        functioncode=3
    )
    return sensor, par_value


def test_par_sensor():
    print(f"Testing connection to PAR Sensor (DFRobot SEN0641) on {SERIAL_PORT}...")
    print(f"Slave ID: {SLAVE_ID}, Register: 0x{REGISTER_ADDRESS:04X}\n")
    
    # Only try baud rates the sensor actually supports (from datasheet)
    baud_rates = [4800, 9600, 2400]
    
    for baud in baud_rates:
        print(f"--- Trying {baud} baud ---")
        
        # Phase 1: Raw serial test to see exactly what bytes we get back
        print(f"[1/2] Raw serial test:")
        raw_result = raw_serial_test(SERIAL_PORT, baud, SLAVE_ID)
        
        if raw_result is not None:
            print(f"\n✅ Raw test PASSED! PAR Value: {raw_result} μmol/m²/s at {baud} baud")
            
            # Phase 2: Now try with minimalmodbus for the real reading
            print(f"\n[2/2] Verifying with minimalmodbus library:")
            try:
                sensor, par_value = test_with_minimalmodbus(SERIAL_PORT, baud, SLAVE_ID)
                print(f"✅ SUCCESS! PAR Value: {par_value} μmol/m²/s at {baud} baud\n")
                
                print("Continuous read mode. Press Ctrl+C to stop.")
                while True:
                    par_value = sensor.read_register(
                        registeraddress=REGISTER_ADDRESS,
                        number_of_decimals=0,
                        functioncode=3
                    )
                    print(f"PAR Value: {par_value} μmol/m²/s")
                    time.sleep(1)
                    
            except IOError as e:
                print(f"  minimalmodbus failed: {e}")
                print(f"  But raw test worked — this may be a minimalmodbus timing issue.")
                print(f"  Try using the raw_serial_test() function directly.\n")
            except KeyboardInterrupt:
                print("\nStopped by user.")
                return
        else:
            print(f"  ✗ No valid response at {baud} baud\n")

        # Small delay between baud rate attempts
        time.sleep(0.5)
    
    print("\n" + "="*60)
    print("Could not connect to sensor on any supported baud rate.")
    print("="*60)
    print("\nTroubleshooting checklist:")
    print("  1. Is the serial console DISABLED? Run: sudo raspi-config")
    print("     → Interface Options → Serial Port → Login shell: NO, Hardware: YES")
    print("  2. Are A and B wires correct? (Yellow=A, Blue=B)")
    print("     Try SWAPPING A and B if you get no response.")
    print("  3. Is the sensor powered? (Brown=VCC 5-30V, Black=GND)")
    print("  4. Is the Seeed RS-485 shield properly seated on the Pi?")
    print("  5. Check: ls -la /dev/serial0  (should point to /dev/ttyS0 or /dev/ttyAMA0)")
    print("  6. Try: sudo dmesg | grep -i serial")


if __name__ == '__main__':
    test_par_sensor()
