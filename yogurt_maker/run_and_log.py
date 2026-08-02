import subprocess
import datetime
import sys
import re

csv_filename = 'temperature_log.csv'

print(f"Starting Pico and logging data to {csv_filename}...")

# Open the CSV file in append mode
with open(csv_filename, 'a') as f:
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
        print("\nStopping logger...")
        process.terminate()
        sys.exit(0)
