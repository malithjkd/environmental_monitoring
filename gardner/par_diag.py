#!/usr/bin/env python3
"""
Diagnostic script for DFRobot SEN0641 PAR Sensor + Seeed RS-485 Shield.
Tests multiple GPIO pins, timing values, and no-GPIO mode to find the
working configuration.
"""
import serial
import time
import struct
import warnings

warnings.filterwarnings("ignore", module="gpiozero")
from gpiozero import OutputDevice


SERIAL_PORT = '/dev/serial0'
BAUD = 4800  # Factory default for SEN0641
SLAVE_ID = 1


def crc16_modbus(data):
    """Calculate Modbus CRC16."""
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


def build_read_request(slave_id, register, count=1):
    """Build a Modbus RTU read holding registers request."""
    request = struct.pack('>BBHH', slave_id, 0x03, register, count)
    crc = crc16_modbus(request)
    request += struct.pack('<H', crc)
    return request


def test_with_gpio(port, baud, gpio_pin, pre_tx_ms, post_tx_ms, post_rx_ms, label=""):
    """Test communication with a specific GPIO pin for TX/RX direction control."""
    request = build_read_request(SLAVE_ID, 0x0000, 1)
    
    tx_enable = OutputDevice(gpio_pin)
    tx_enable.off()
    time.sleep(0.05)
    
    try:
        ser = serial.Serial(
            port=port, baudrate=baud,
            bytesize=8, parity=serial.PARITY_NONE, stopbits=1,
            timeout=2.0
        )
        
        ser.reset_input_buffer()
        time.sleep(0.05)
        ser.reset_input_buffer()
        
        # TX phase
        tx_enable.on()
        time.sleep(pre_tx_ms / 1000.0)
        
        ser.write(request)
        ser.flush()
        
        time.sleep(post_tx_ms / 1000.0)
        
        # Switch to RX
        tx_enable.off()
        time.sleep(post_rx_ms / 1000.0)
        
        # Read response
        response = ser.read(32)
        ser.close()
        
        return parse_response(response, label)
    except Exception as e:
        print(f"  {label}: ERROR - {e}")
        return False
    finally:
        tx_enable.off()
        tx_enable.close()


def test_no_gpio(port, baud, label=""):
    """Test communication WITHOUT any GPIO toggling (auto-direction shield)."""
    request = build_read_request(SLAVE_ID, 0x0000, 1)
    
    try:
        ser = serial.Serial(
            port=port, baudrate=baud,
            bytesize=8, parity=serial.PARITY_NONE, stopbits=1,
            timeout=2.0
        )
        
        ser.reset_input_buffer()
        time.sleep(0.05)
        ser.reset_input_buffer()
        
        ser.write(request)
        ser.flush()
        
        # At 4800 baud, 8 bytes takes ~16.7ms to send, then sensor needs time to respond
        time.sleep(0.1)
        
        response = ser.read(32)
        ser.close()
        
        return parse_response(response, label)
    except Exception as e:
        print(f"  {label}: ERROR - {e}")
        return False


def test_inverted_gpio(port, baud, gpio_pin, label=""):
    """
    Test with INVERTED GPIO logic (LOW=TX, HIGH=RX).
    Some RS-485 boards invert the enable pin.
    """
    request = build_read_request(SLAVE_ID, 0x0000, 1)
    
    tx_enable = OutputDevice(gpio_pin)
    tx_enable.on()  # Start in RX mode (inverted!)
    time.sleep(0.05)
    
    try:
        ser = serial.Serial(
            port=port, baudrate=baud,
            bytesize=8, parity=serial.PARITY_NONE, stopbits=1,
            timeout=2.0
        )
        
        ser.reset_input_buffer()
        time.sleep(0.05)
        ser.reset_input_buffer()
        
        # TX phase (inverted: LOW = transmit)
        tx_enable.off()
        time.sleep(0.005)
        
        ser.write(request)
        ser.flush()
        
        bits_per_byte = 10
        byte_time = bits_per_byte / baud
        time.sleep(byte_time * 5)
        
        # RX phase (inverted: HIGH = receive)
        tx_enable.on()
        time.sleep(0.002)
        
        response = ser.read(32)
        ser.close()
        
        return parse_response(response, label)
    except Exception as e:
        print(f"  {label}: ERROR - {e}")
        return False
    finally:
        tx_enable.on()  # Back to RX (inverted)
        tx_enable.close()


def parse_response(response, label):
    """Parse and display a Modbus response."""
    if not response:
        print(f"  {label}: No response (0 bytes)")
        return False
    
    hex_str = response.hex(' ')
    print(f"  {label}: [{len(response)} bytes] {hex_str}", end="")
    
    if len(response) >= 7:
        rx_crc = int.from_bytes(response[-2:], 'little')
        calc_crc = crc16_modbus(response[:-2])
        
        if rx_crc == calc_crc:
            addr = response[0]
            func = response[1]
            data = int.from_bytes(response[3:5], 'big')
            print(f"  ✅ CRC OK! addr={addr}, PAR={data}")
            return True
        else:
            print(f"  ✗ CRC mismatch (rx=0x{rx_crc:04x}, calc=0x{calc_crc:04x})")
    else:
        print(f"  ✗ Too short")
    
    return False


def check_config():
    """Check Raspberry Pi configuration for UART/serial setup."""
    print("=" * 60)
    print("SYSTEM CONFIGURATION CHECK")
    print("=" * 60)
    
    import subprocess
    
    # Check serial0 symlink
    try:
        result = subprocess.run(['ls', '-la', '/dev/serial0'], capture_output=True, text=True)
        print(f"  serial0: {result.stdout.strip()}")
    except:
        print("  serial0: NOT FOUND")
    
    # Check /boot/config.txt for UART overlays
    config_paths = ['/boot/config.txt', '/boot/firmware/config.txt']
    for path in config_paths:
        try:
            with open(path) as f:
                lines = f.readlines()
            
            print(f"\n  {path} (UART-related lines):")
            uart_keywords = ['uart', 'serial', 'bluetooth', 'bt', 'miniuart', 'ttyAMA', 'pi3-', 'ama0']
            found = False
            for line in lines:
                line = line.strip()
                if line and not line.startswith('#'):
                    if any(kw in line.lower() for kw in uart_keywords):
                        print(f"    {line}")
                        found = True
            if not found:
                print(f"    (no UART-related config found)")
            break
        except FileNotFoundError:
            continue
    
    # Check cmdline.txt
    cmdline_paths = ['/boot/cmdline.txt', '/boot/firmware/cmdline.txt']
    for path in cmdline_paths:
        try:
            with open(path) as f:
                cmdline = f.read().strip()
            has_console = 'console=serial' in cmdline or 'console=ttyAMA' in cmdline or 'console=ttyS' in cmdline
            print(f"\n  {path}:")
            print(f"    Serial console in cmdline: {'YES ⚠️  (should be removed!)' if has_console else 'NO ✓'}")
            break
        except FileNotFoundError:
            continue
    
    print()


def run_diagnostics():
    print("DFRobot SEN0641 PAR Sensor - RS-485 Diagnostic Tool")
    print("=" * 60)
    print(f"Port: {SERIAL_PORT}, Baud: {BAUD}, Slave ID: {SLAVE_ID}")
    print(f"Expected TX frame: {build_read_request(SLAVE_ID, 0x0000).hex(' ')}")
    print()
    
    # Step 0: System config check
    check_config()
    
    # Step 1: No GPIO (auto-direction test)
    print("TEST 1: No GPIO control (auto-direction shield)")
    print("-" * 50)
    if test_no_gpio(SERIAL_PORT, BAUD, "No GPIO"):
        print(">>> Auto-direction works! No GPIO toggling needed.\n")
        return
    print()
    time.sleep(0.3)
    
    # Step 2: Try different GPIO pins with normal polarity (HIGH=TX, LOW=RX)
    print("TEST 2: GPIO direction control (HIGH=TX, LOW=RX)")
    print("-" * 50)
    gpio_pins = [18, 4, 17, 27, 22, 5, 6, 13, 19, 26]
    
    for pin in gpio_pins:
        # Try with different timing values
        timings = [
            (5, 10, 2, f"GPIO {pin:2d} (normal timing)"),
            (5, 20, 5, f"GPIO {pin:2d} (longer delays)"),
        ]
        for pre_tx, post_tx, post_rx, label in timings:
            if test_with_gpio(SERIAL_PORT, BAUD, pin, pre_tx, post_tx, post_rx, label):
                print(f"\n>>> SUCCESS with GPIO {pin}, polarity=NORMAL!")
                print(f"    Timing: pre_tx={pre_tx}ms, post_tx={post_tx}ms, post_rx={post_rx}ms")
                return
        time.sleep(0.2)
    print()
    
    # Step 3: Try inverted GPIO polarity (LOW=TX, HIGH=RX) 
    print("TEST 3: GPIO direction control INVERTED (LOW=TX, HIGH=RX)")
    print("-" * 50)
    for pin in gpio_pins:
        if test_inverted_gpio(SERIAL_PORT, BAUD, pin, f"GPIO {pin:2d} (inverted)"):
            print(f"\n>>> SUCCESS with GPIO {pin}, polarity=INVERTED!")
            return
        time.sleep(0.2)
    print()
    
    # Step 4: Try GPIO 18 with many different timing combos
    print("TEST 4: GPIO 18 - exhaustive timing sweep")
    print("-" * 50)
    for post_tx in [5, 10, 15, 20, 30, 50]:
        for post_rx in [1, 2, 5, 10]:
            label = f"GPIO 18  post_tx={post_tx:2d}ms  post_rx={post_rx:2d}ms"
            if test_with_gpio(SERIAL_PORT, BAUD, 18, 5, post_tx, post_rx, label):
                print(f"\n>>> SUCCESS!")
                return
    time.sleep(0.2)
    print()

    # Step 5: Try broadcast address (0xFF) at 4800
    print("TEST 5: Broadcast address (0xFF) on GPIO 18")
    print("-" * 50)
    # The SEN0641 supports query at address 0xFF to discover device
    request_ff = build_read_request(0xFF, 0x07D0, 2)  # Read address + baud rate registers
    
    tx_enable = OutputDevice(18)
    tx_enable.off()
    time.sleep(0.05)
    
    try:
        ser = serial.Serial(
            port=SERIAL_PORT, baudrate=BAUD,
            bytesize=8, parity=serial.PARITY_NONE, stopbits=1,
            timeout=2.0
        )
        ser.reset_input_buffer()
        time.sleep(0.05)
        ser.reset_input_buffer()
        
        tx_enable.on()
        time.sleep(0.005)
        ser.write(request_ff)
        ser.flush()
        time.sleep(0.02)
        tx_enable.off()
        time.sleep(0.002)
        
        response = ser.read(32)
        ser.close()
        
        parse_response(response, f"Broadcast query (TX: {request_ff.hex(' ')})")
    except Exception as e:
        print(f"  Error: {e}")
    finally:
        tx_enable.off()
        tx_enable.close()
    
    print()
    print("=" * 60)
    print("ALL TESTS FAILED")
    print("=" * 60)
    print()
    print("Next steps:")
    print("  1. SWAP the A and B wires on the RS-485 shield and re-run")
    print("  2. Verify sensor has power (LED indicator on sensor?)")
    print("  3. Confirm exact RS-485 shield model and check its wiki")
    print("     for which GPIO pin it uses for TX/RX direction")
    print("  4. Try running: sudo python3 par_diag.py")
    print("     (in case it's a permissions issue)")


if __name__ == '__main__':
    run_diagnostics()
