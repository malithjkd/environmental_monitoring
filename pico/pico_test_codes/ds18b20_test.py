"""Standalone DS18B20 test — run this to test the waterproof temperature sensor."""
import machine
import onewire
import ds18x20
import utime

# DS18B20 data pin is on GPIO3
TEST_PIN = 3

print(f"\n=== DS18B20 Test on GPIO{TEST_PIN} ===")

try:
    # Initialize 1-Wire bus
    dat = machine.Pin(TEST_PIN)
    ds = ds18x20.DS18X20(onewire.OneWire(dat))
    
    # Scan for devices on the bus
    roms = ds.scan()
    print(f"Found {len(roms)} device(s):", roms)

    if not roms:
        print("No DS18B20 sensors found. Check wiring:")
        print("  1. Black wire to GND, Red wire to 3.3V, Data wire to GPIO3")
        print("  2. Needs a 4.7k pull-up resistor between Data and 3.3V")
    else:
        for i in range(5):
            print(f"  Read {i+1}: Converting temperature...")
            ds.convert_temp()
            # The DS18B20 needs at least 750ms to convert the temperature
            utime.sleep_ms(750) 
            
            for rom in roms:
                temp = ds.read_temp(rom)
                print(f"    Sensor {rom}: {temp:.2f}°C  ✓ WORKING!")
            
            utime.sleep_ms(2000)

except Exception as e:
    print("Error initializing or reading DS18B20:", e)

print("\nDone.")
