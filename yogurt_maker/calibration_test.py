"""Smart Yogurt Maker — Calibration Test (MicroPython)

Runs on the Raspberry Pi Pico W. Performs a two-phase test:
  1. HEATING: Relay ON at 100% until target temp or timeout
  2. COOLING: Relay OFF until target temp or timeout

Prints CSV-formatted data via serial for the host to capture.
The host-side analyzer uses this data to compute:
  - k_cool (cooling coefficient, W/°C)
  - Effective heating power delivered to the water
  - Suggested PID constants
"""

import machine
import onewire
import ds18x20
import utime

# ===== CALIBRATION PARAMETERS =====
# These can be adjusted by the calibration_runner before deployment
HEATING_TARGET_C = 55.0       # Stop heating at this temperature (lowered for porcelain lag)
HEATING_TIMEOUT_S = 2400      # Max 40 minutes heating (porcelain heats slower)
COOLING_TARGET_C = 40.0       # Stop cooling at this temperature
COOLING_TIMEOUT_S = 7200      # Max 2 hours cooling (porcelain retains heat)
SAMPLE_INTERVAL_MS = 2000     # Sample every 2 seconds
SENSOR_PIN = 3
RELAY_PIN = 13
# ===== END PARAMETERS =====

# Hardware setup
relay = machine.Pin(RELAY_PIN, machine.Pin.OUT)
relay.off()
led = machine.Pin("LED", machine.Pin.OUT)
led.off()

dat = machine.Pin(SENSOR_PIN)
ds = ds18x20.DS18X20(onewire.OneWire(dat))


def scan_sensors():
    """Scan for DS18B20 with retries."""
    for attempt in range(3):
        print(f"Scanning for sensor (attempt {attempt + 1})...")
        utime.sleep(2)
        roms = ds.scan()
        if roms:
            print(f"Found DS18B20: {roms}")
            return roms
    print("ERROR: No DS18B20 sensor found!")
    return []


def read_temp_blocking(roms):
    """Blocking temperature read (simpler for calibration)."""
    ds.convert_temp()
    utime.sleep_ms(750)
    return ds.read_temp(roms[0])


def main():
    roms = scan_sensors()
    if not roms:
        relay.off()
        led.off()
        return

    # Read initial temperature
    initial_temp = read_temp_blocking(roms)
    print(f"Initial temperature: {initial_temp:.2f}C")

    # Print CSV header
    print("CSV_START")
    print("elapsed_s,temperature_c,phase,relay_state")

    start_ms = utime.ticks_ms()
    phase = "HEATING"
    relay.on()
    led.on()

    try:
        while True:
            temp = read_temp_blocking(roms)
            elapsed_ms = utime.ticks_diff(utime.ticks_ms(), start_ms)
            elapsed_s = elapsed_ms / 1000.0
            relay_val = relay.value()

            # Print data point
            print(f"{elapsed_s:.1f},{temp:.2f},{phase},{relay_val}")

            # Phase logic
            if phase == "HEATING":
                if temp >= HEATING_TARGET_C:
                    print(f"# HEATING complete: reached {temp:.2f}C")
                    phase = "COOLING"
                    relay.off()
                    led.off()
                elif elapsed_s >= HEATING_TIMEOUT_S:
                    print(f"# HEATING timeout at {temp:.2f}C")
                    phase = "COOLING"
                    relay.off()
                    led.off()

            elif phase == "COOLING":
                cooling_elapsed = elapsed_s - HEATING_TIMEOUT_S  # Approximate
                if temp <= COOLING_TARGET_C:
                    print(f"# COOLING complete: reached {temp:.2f}C")
                    break
                elif elapsed_s >= (HEATING_TIMEOUT_S + COOLING_TIMEOUT_S):
                    print(f"# COOLING timeout at {temp:.2f}C")
                    break

            # Wait for next sample (subtract conversion time)
            wait_ms = SAMPLE_INTERVAL_MS - 750
            if wait_ms > 0:
                utime.sleep_ms(wait_ms)

    except KeyboardInterrupt:
        print("# Calibration interrupted by user")
    finally:
        relay.off()
        led.off()
        print("CSV_END")
        print("Calibration test complete. Relay OFF.")


main()
