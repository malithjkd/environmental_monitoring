#!/usr/bin/env python3
"""
Read PAR (Photosynthetically Active Radiation) value from DFRobot SEN0641
over RS485 / Modbus-RTU, using the Seeed RS-485 Shield on a Raspberry Pi 3B+.

Wiring:
  Sensor Brown (VCC) -> Pi 5V pin
  Sensor Black (GND) -> Pi GND
  Sensor Yellow (485-A) -> Shield 485-A terminal
  Sensor Blue   (485-B) -> Shield 485-B terminal

Shield uses GPIO14/15 for UART TX/RX (wired internally, no action needed)
and GPIO18 as the transmit/receive enable line (toggled in software below).
"""

import time
import serial
from gpiozero import LED

# ---- Config ----
SERIAL_PORT = "/dev/ttyS0"   # mini-UART on GPIO14/15 (Pi 3B+)
BAUD_RATE = 4800              # sensor factory default
SLAVE_ADDRESS = 0x01          # sensor factory default
PAR_REGISTER = 0x0000         # holding register: PAR value, read-only
DE_RE_PIN = 18                # shield's direction-control GPIO


def crc16_modbus(data: bytes) -> bytes:
    """Compute Modbus RTU CRC16, return as (low_byte, high_byte)."""
    crc = 0xFFFF
    for byte in data:
        crc ^= byte
        for _ in range(8):
            if crc & 0x0001:
                crc >>= 1
                crc ^= 0xA001
            else:
                crc >>= 1
    return bytes([crc & 0xFF, (crc >> 8) & 0xFF])


def build_read_request(slave_addr: int, register: int, count: int = 1) -> bytes:
    """Build a Modbus RTU 'read holding registers' (function 0x03) request."""
    frame = bytes([
        slave_addr,
        0x03,
        (register >> 8) & 0xFF, register & 0xFF,
        (count >> 8) & 0xFF, count & 0xFF,
    ])
    return frame + crc16_modbus(frame)


def read_par_value(ser: serial.Serial, tx_enable: LED) -> int:
    """Send the read request and parse the PAR value (umol/m^2*s) from the response."""
    request = build_read_request(SLAVE_ADDRESS, PAR_REGISTER, 1)

    # Enable transmit, send, then switch to receive
    tx_enable.on()
    time.sleep(0.01)          # small settle time before transmitting
    ser.write(request)
    ser.flush()
    time.sleep(0.01)          # ensure last byte has physically left the line
    tx_enable.off()

    # Expected response: addr(1) + func(1) + bytecount(1) + value(2) + crc(2) = 7 bytes
    response = ser.read(7)

    if len(response) != 7:
        raise IOError(f"Incomplete response ({len(response)} bytes) - check wiring/A-B polarity")

    addr, func, byte_count = response[0], response[1], response[2]
    value = (response[3] << 8) | response[4]
    received_crc = response[5:7]
    expected_crc = crc16_modbus(response[:5])

    if received_crc != expected_crc:
        raise IOError("CRC mismatch - noisy line or wiring issue")

    if addr != SLAVE_ADDRESS or func != 0x03:
        raise IOError(f"Unexpected response header: addr={addr}, func={func}")

    return value  # PAR value in umol/m^2*s, no scaling needed


def main():
    ser = serial.Serial(
        port=SERIAL_PORT,
        baudrate=BAUD_RATE,
        bytesize=serial.EIGHTBITS,
        parity=serial.PARITY_NONE,
        stopbits=serial.STOPBITS_ONE,
        timeout=1,
    )
    tx_enable = LED(DE_RE_PIN)
    tx_enable.off()  # start in receive mode

    try:
        par_value = read_par_value(ser, tx_enable)
        print(f"PAR: {par_value} umol/m^2*s")
    except IOError as e:
        print(f"Read failed: {e}")
    finally:
        ser.close()


if __name__ == "__main__":
    main()