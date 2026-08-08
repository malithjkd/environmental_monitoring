#!/usr/bin/env python3
"""
Focused timing fix for DFRobot SEN0641 PAR Sensor.
The sensor responds VERY quickly after our TX, so we need to
switch to RX as fast as possible after the last byte is sent.
"""
import time
import struct
import warnings
import sys

# Robust pyserial import - avoids conflicts with other 'serial' modules
try:
    from serial import Serial, PARITY_NONE
except (ImportError, AttributeError):
    print("ERROR: pyserial not installed. Run: pip install pyserial")
    sys.exit(1)

warnings.filterwarnings("ignore", module="gpiozero")
from gpiozero import OutputDevice


SERIAL_PORT = '/dev/serial0'
BAUD = 4800
SLAVE_ID = 1
GPIO_PIN = 18


def crc16_modbus(data):
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


def try_read(post_tx_us, label=""):
    """Try reading with a specific post-TX delay in microseconds."""
    request = struct.pack('>BBHH', SLAVE_ID, 0x03, 0x0000, 0x0001)
    crc = crc16_modbus(request)
    request += struct.pack('<H', crc)
    
    tx_en = OutputDevice(GPIO_PIN)
    tx_en.off()
    time.sleep(0.05)
    
    try:
        ser = Serial(
            port=SERIAL_PORT, baudrate=BAUD,
            bytesize=8, parity=PARITY_NONE, stopbits=1,
            timeout=2.0
        )
        
        # Drain old data
        ser.reset_input_buffer()
        time.sleep(0.05)
        ser.reset_input_buffer()
        
        # === TX PHASE ===
        tx_en.on()
        time.sleep(0.003)  # Let transceiver settle in TX mode
        
        t_start = time.monotonic()
        ser.write(request)
        ser.flush()  # tcdrain - wait for OS buffer to empty
        t_flush = time.monotonic()
        
        # Wait just enough for UART shift register to clear the last byte
        if post_tx_us > 0:
            time.sleep(post_tx_us / 1_000_000.0)
        
        # === RX PHASE ===
        tx_en.off()
        t_rx = time.monotonic()
        
        # DO NOT reset_input_buffer here - response may already be arriving!
        # Read with generous timeout
        response = ser.read(32)
        t_done = time.monotonic()
        
        ser.close()
        
        flush_ms = (t_flush - t_start) * 1000
        rx_ms = (t_rx - t_start) * 1000
        total_ms = (t_done - t_start) * 1000
        
        hex_str = response.hex(' ') if response else '(none)'
        print(f"  {label}: [{len(response):2d} bytes] {hex_str}")
        print(f"           flush={flush_ms:.1f}ms, rx_switch={rx_ms:.1f}ms, total={total_ms:.1f}ms", end="")
        
        if len(response) >= 7:
            # Try to find a valid 7-byte Modbus response anywhere in the data
            for i in range(len(response) - 6):
                frame = response[i:i+7]
                if frame[0] == SLAVE_ID and frame[1] == 0x03 and frame[2] == 0x02:
                    rx_crc = int.from_bytes(frame[5:7], 'little')
                    calc_crc = crc16_modbus(frame[:5])
                    if rx_crc == calc_crc:
                        par_value = int.from_bytes(frame[3:5], 'big')
                        print(f"\n  ✅ SUCCESS! PAR = {par_value} μmol/m²/s (found at offset {i})")
                        return par_value
            
            # Also check if the full response is valid
            rx_crc = int.from_bytes(response[-2:], 'little')
            calc_crc = crc16_modbus(response[:-2])
            if rx_crc == calc_crc:
                par_value = int.from_bytes(response[3:5], 'big')
                print(f"\n  ✅ SUCCESS! PAR = {par_value} μmol/m²/s")
                return par_value
            print(f"  ✗ CRC mismatch")
        elif len(response) >= 5:
            # Check for Modbus error response (5 bytes)
            if response[1] & 0x80:
                print(f"  ⚠ Modbus error response: code 0x{response[2]:02x}")
            else:
                print(f"  ✗ Too short")
        else:
            print(f"  ✗ {'No data' if not response else 'Too short'}")
        
        return None
    except Exception as e:
        print(f"  {label}: ERROR - {e}")
        return None
    finally:
        tx_en.off()
        tx_en.close()


def try_read_split(label=""):
    """
    Alternative approach: calculate TX time precisely and use total elapsed
    time from the start of write rather than relying on flush() timing.
    
    At 4800 baud, 8 bytes = 8 * 10 bits / 4800 = 16.67ms
    Switch to RX at exactly 17ms from start of write.
    """
    request = struct.pack('>BBHH', SLAVE_ID, 0x03, 0x0000, 0x0001)
    crc = crc16_modbus(request)
    request += struct.pack('<H', crc)
    
    tx_en = OutputDevice(GPIO_PIN)
    tx_en.off()
    time.sleep(0.05)
    
    try:
        ser = Serial(
            port=SERIAL_PORT, baudrate=BAUD,
            bytesize=8, parity=PARITY_NONE, stopbits=1,
            timeout=2.0
        )
        
        ser.reset_input_buffer()
        time.sleep(0.05)
        ser.reset_input_buffer()
        
        # Calculate exact TX time
        tx_time_ms = len(request) * 10 * 1000 / BAUD  # 16.67ms for 8 bytes at 4800
        
        tx_en.on()
        time.sleep(0.003)
        
        t_start = time.monotonic()
        ser.write(request)
        # Don't use flush! Instead, busy-wait for the calculated TX time + 1 byte margin
        target_time = t_start + (tx_time_ms + 2.5) / 1000.0  # +2.5ms for shift register + margin
        
        while time.monotonic() < target_time:
            pass  # Busy-wait for precise timing
        
        tx_en.off()  # Switch to RX at precisely the right moment
        t_rx = time.monotonic()
        
        # Read response
        response = ser.read(32)
        ser.close()
        
        rx_ms = (t_rx - t_start) * 1000
        hex_str = response.hex(' ') if response else '(none)'
        print(f"  {label}: [{len(response):2d} bytes] {hex_str}")
        print(f"           rx_switch={rx_ms:.1f}ms after write start (target={tx_time_ms+2.5:.1f}ms)", end="")
        
        if len(response) >= 7:
            for i in range(len(response) - 6):
                frame = response[i:i+7]
                if frame[0] == SLAVE_ID and frame[1] == 0x03 and frame[2] == 0x02:
                    rx_crc = int.from_bytes(frame[5:7], 'little')
                    calc_crc = crc16_modbus(frame[:5])
                    if rx_crc == calc_crc:
                        par_value = int.from_bytes(frame[3:5], 'big')
                        print(f"\n  ✅ SUCCESS! PAR = {par_value} μmol/m²/s (found at offset {i})")
                        return par_value
            print(f"  ✗ No valid frame found")
        else:
            print(f"  ✗ {'No data' if not response else 'Too short'}")
        
        return None
    except Exception as e:
        print(f"  {label}: ERROR - {e}")
        return None
    finally:
        tx_en.off()
        tx_en.close()


def main():
    print("PAR Sensor Timing Fix - Focused Diagnostic")
    print("=" * 55)
    print(f"Port: {SERIAL_PORT}, Baud: {BAUD}, GPIO: {GPIO_PIN}")
    print()
    
    # Test A: Very fine-grained post_tx sweep (0 to 5ms in 0.5ms steps)
    print("TEST A: Fine post_tx sweep (after flush)")
    print("-" * 55)
    for delay_us in [0, 250, 500, 750, 1000, 1500, 2000, 2500, 3000, 4000, 5000]:
        result = try_read(delay_us, f"post_tx={delay_us:5d}μs")
        if result is not None:
            print(f"\n>>> WORKING DELAY FOUND: {delay_us}μs after flush()")
            break
        time.sleep(0.3)
    
    print()
    
    # Test B: Precise timing approach (busy-wait instead of flush)
    print("TEST B: Busy-wait precise timing")
    print("-" * 55)
    result = try_read_split("Busy-wait")
    if result is not None:
        print("\n>>> Busy-wait approach works!")
    
    print()
    
    # Test C: No delay at all, just let everything flow
    print("TEST C: Zero delay (immediate RX switch)")
    print("-" * 55)
    
    tx_en = OutputDevice(GPIO_PIN)
    tx_en.off()
    time.sleep(0.05)
    
    request = struct.pack('>BBHH', SLAVE_ID, 0x03, 0x0000, 0x0001)
    crc = crc16_modbus(request)
    request += struct.pack('<H', crc)
    
    ser = Serial(
        port=SERIAL_PORT, baudrate=BAUD,
        bytesize=8, parity=PARITY_NONE, stopbits=1,
        timeout=2.0
    )
    ser.reset_input_buffer()
    time.sleep(0.05)
    ser.reset_input_buffer()
    
    tx_en.on()
    time.sleep(0.003)
    ser.write(request)
    ser.flush()
    tx_en.off()  # Immediately! No delay at all!
    
    # Wait and read
    response = ser.read(32)
    ser.close()
    tx_en.close()
    
    hex_str = response.hex(' ') if response else '(none)'
    print(f"  Immediate switch: [{len(response):2d} bytes] {hex_str}")
    
    if response:
        # Scan for valid Modbus frame
        for i in range(max(1, len(response) - 6)):
            if i + 7 <= len(response):
                frame = response[i:i+7]
                if frame[1] == 0x03 and frame[2] == 0x02:
                    rx_crc = int.from_bytes(frame[5:7], 'little')
                    calc_crc = crc16_modbus(frame[:5])
                    if rx_crc == calc_crc:
                        par_value = int.from_bytes(frame[3:5], 'big')
                        print(f"  ✅ Found valid frame at offset {i}: PAR = {par_value} μmol/m²/s")
                        return
        
        print(f"  ✗ No valid Modbus frame found in response")
        # Show what we got for analysis
        for i, b in enumerate(response):
            print(f"    byte[{i}] = 0x{b:02X} ({b:3d}) {b:08b}")
    else:
        print(f"  ✗ No data")


if __name__ == '__main__':
    main()
