"""Standalone DHT22 test — run this to diagnose wiring issues."""
from machine import Pin
import dht
import utime

# Try GPIO2 first (your current wiring)
TEST_PIN = 2

print(f"=== DHT22 Test on GPIO{TEST_PIN} ===")
print("Waiting 2s for sensor warm-up...")
utime.sleep_ms(2000)

sensor = dht.DHT22(Pin(TEST_PIN, Pin.IN, Pin.PULL_UP))

for i in range(5):
    try:
        sensor.measure()
        temp = sensor.temperature()
        hum = sensor.humidity()
        print(f"  Read {i+1}: Temp={temp}°C, Humidity={hum}%")
    except Exception as e:
        print(f"  Read {i+1}: FAILED — {e}")
    utime.sleep_ms(2500)

print("\nDone. If all reads failed, check:")
print("  1. Black wire must be on GND (not 3.3V)")
print("  2. Data wire is on GPIO2 (physical pin 4)")
print("  3. 4.7k resistor between data and 3.3V")
print("  4. Try moving data wire to GPIO22 (physical pin 29)")
