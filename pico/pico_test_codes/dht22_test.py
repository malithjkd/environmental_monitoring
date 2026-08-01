"""Standalone DHT22 test — tries multiple GPIOs to find the sensor."""
from machine import Pin
import dht
import utime

for TEST_PIN in [2, 22]:
    print(f"\n=== Testing GPIO{TEST_PIN} ===")
    utime.sleep_ms(2000)
    sensor = dht.DHT22(Pin(TEST_PIN, Pin.IN, Pin.PULL_UP))

    for i in range(3):
        try:
            sensor.measure()
            temp = sensor.temperature()
            hum = sensor.humidity()
            print(f"  Read {i+1}: Temp={temp}°C, Humidity={hum}%  ✓ WORKING!")
        except Exception as e:
            print(f"  Read {i+1}: FAILED — {e}")
        utime.sleep_ms(2500)

print("\n=== Summary ===")
print("If GPIO22 worked: your data wire is on GPIO22, not GPIO2")
print("If both failed: check black wire is on GND (not 3.3V)")
