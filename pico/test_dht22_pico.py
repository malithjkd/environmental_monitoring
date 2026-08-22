import machine
import utime
import dht

# The user mentioned GPIO3 for the data pin
DATA_PIN = 3

print(f"Initializing DHT22 on GPIO{DATA_PIN}...")

# Initialize the DHT22 sensor on GPIO3.
# Since you mentioned "no resistor", we will try enabling the Pico's internal pull-up resistor.
# Note: The internal pull-up is weak (~50k) so an external 4.7k-10k resistor is still highly recommended if this fails.
try:
    sensor = dht.DHT22(machine.Pin(DATA_PIN, machine.Pin.IN, machine.Pin.PULL_UP))
except Exception as e:
    print(f"Error initializing sensor: {e}")

print("Starting readings. Press stop in your IDE (like Thonny) to exit.\n")

while True:
    try:
        # Trigger the sensor to take a measurement
        sensor.measure()
        
        # Read the values
        temp = sensor.temperature()
        humidity = sensor.humidity()
        
        print(f"Temperature: {temp:.1f}°C   |   Humidity: {humidity:.1f}%")
        
    except OSError as e:
        print("Failed to read sensor.")
    
    # DHT22 needs at least 2 seconds between readings
    utime.sleep(2)
