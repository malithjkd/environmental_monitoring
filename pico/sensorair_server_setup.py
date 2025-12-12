# cd ..  && cd .. && source py313/bin/activate && cd environmental_monitoring/pico/ &&  python sensorair_server_setup.py



import requests
import pandas as pd
import matplotlib.pyplot as plt
import time
from datetime import datetime

# --- Configuration ---
# IMPORTANT: Replace with the actual IP address of your Pico W
PICO_W_IP = '192.168.1.200' 
API_URL = f"http://{PICO_W_IP}/"
DATA_FILE = 'co2_data.csv'
SAMPLE_INTERVAL_SECONDS = 30 # How often to poll the sensor

# --- Initialize or Load Data ---
try:
    # Load existing data if the file exists
    df = pd.read_csv(DATA_FILE)
    print(f"Loaded {len(df)} existing data points.")
except FileNotFoundError:
    # Create a new DataFrame if the file doesn't exist
    df = pd.DataFrame(columns=['Timestamp', 'CO2_PPM'])
    print("Created new data file.")

# --- Functions ---

def fetch_co2_data():
    """Fetches CO2 data from the Pico W HTTP server."""
    try:
        response = requests.get(API_URL, timeout=5)
        # The Pico W returns a simple string (e.g., "450")
        co2_ppm = int(response.text.strip())
        timestamp = datetime.now()
        print(f"[{timestamp.strftime('%Y-%m-%d %H:%M:%S')}] Fetched CO2: {co2_ppm} PPM")
        return timestamp, co2_ppm
    except requests.exceptions.RequestException as e:
        print(f"Error fetching data from Pico W: {e}")
        return None, None
    except ValueError:
        print("Error: Received non-integer CO2 data.")
        return None, None

def store_data(timestamp, co2_ppm):
    """Adds new data to the DataFrame and saves it to CSV."""
    global df
    # Create a new row
    new_data = pd.DataFrame([{'Timestamp': timestamp, 'CO2_PPM': co2_ppm}])
    # Append the new data
    df = pd.concat([df, new_data], ignore_index=True)
    # Save the updated DataFrame to the CSV file
    df.to_csv(DATA_FILE, index=False)

def plot_data():
    """Plots the last hour of CO2 data."""
    if df.empty:
        print("No data to plot.")
        return

    # Convert Timestamp column to datetime objects
    df['Timestamp'] = pd.to_datetime(df['Timestamp'])
    
    # Filter for the last hour of data for plotting
    one_hour_ago = datetime.now() - pd.Timedelta(hours=1)
    df_plot = df[df['Timestamp'] > one_hour_ago]

    if df_plot.empty:
        print("No data in the last hour to plot.")
        return

    plt.figure(figsize=(10, 6))
    plt.plot(df_plot['Timestamp'], df_plot['CO2_PPM'], marker='o', linestyle='-', markersize=2)
    plt.xlabel('Time')
    plt.ylabel('CO2 Concentration (PPM)')
    plt.title('Real-time CO2 Measurement')
    plt.grid(True)
    plt.xticks(rotation=45)
    plt.tight_layout()
    plt.savefig('co2_plot.png')
    plt.close() # Close the figure to free memory
    print("Plot saved to co2_plot.png")

# --- Main Loop ---
try:
    while True:
        timestamp, co2_ppm = fetch_co2_data()

        if timestamp and co2_ppm is not None:
            store_data(timestamp, co2_ppm)
            # Re-plot every 5 minutes (300 seconds) or adjust as needed
            if len(df) % (300 // SAMPLE_INTERVAL_SECONDS) == 0:
                 plot_data()

        time.sleep(SAMPLE_INTERVAL_SECONDS)

except KeyboardInterrupt:
    print("\nData collection stopped by user.")
    plot_data() # Final plot