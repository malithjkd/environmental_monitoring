import subprocess
import datetime
import sys
import re
import os
import json

# Create data directory if it doesn't exist
data_dir = 'data'
if not os.path.exists(data_dir):
    os.makedirs(data_dir)

# Create a timestamped folder for this specific run
run_timestamp = datetime.datetime.now().strftime('%Y_%m_%d_%H_%M_%S')
run_dir = os.path.join(data_dir, run_timestamp)
os.makedirs(run_dir)

csv_filename = os.path.join(run_dir, 'temperature_log.csv')
connection_log_filename = os.path.join(run_dir, 'connection_status.log')
metadata_filename = os.path.join(run_dir, 'metadata.json')

# Create and write metadata.json with some default test settings
metadata = {
    "test_name": "Yogurt Maker Temperature Run",
    "timestamp": run_timestamp,
    "target_temperature_C": 42.0,  # You can adjust these
    "sensor_type": "DS18B20",
    "relay_pin": 15,
    "sensor_pin": 3
}

with open(metadata_filename, 'w') as mf:
    json.dump(metadata, mf, indent=4)

print(f"Starting Pico and logging data to {run_dir}/...")

# Open the CSV file and Connection log file in append mode
with open(csv_filename, 'a') as f, open(connection_log_filename, 'a') as conn_log:
    # Write CSV header
    f.write("Timestamp,Temperature_C,Relay_State\n") 
    
    # Run the mpremote command
    # bufsize=1 ensures line-buffered output
    process = subprocess.Popen(
        ['mpremote', 'run', 'temperature_controller.py'],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1
    )

    try:
        # Read the output line by line as it comes
        for line in iter(process.stdout.readline, ''):
            # Print the original output to the terminal so you can still see it
            sys.stdout.write(line)
            sys.stdout.flush()
            
            # Log all output to connection status log
            conn_log.write(line)
            conn_log.flush()
            
            # Check if the line contains temperature data
            # Example line from Pico: "Temp: 41.50C, Relay: ON"
            if "Temp:" in line and "Relay:" in line:
                match = re.search(r'Temp:\s*([\d\.]+)C,\s*Relay:\s*(ON|OFF)', line)
                if match:
                    temp = match.group(1)
                    relay = match.group(2)
                    timestamp = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                    
                    # Write clean data to CSV
                    f.write(f"{timestamp},{temp},{relay}\n")
                    f.flush() # Ensure it writes to the file immediately
                    
    except KeyboardInterrupt:
        print(f"\nStopping logger... Data saved in {run_dir}")
        process.terminate()
        sys.exit(0)
