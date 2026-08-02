import csv
import matplotlib.pyplot as plt
from datetime import datetime
import matplotlib.dates as mdates

csv_filename = 'temperature_log.csv'

timestamps = []
temperatures = []
relay_states = []

print(f"Reading data from {csv_filename}...")
try:
    with open(csv_filename, 'r') as f:
        reader = csv.reader(f)
        header = next(reader, None) # Skip header
        for row in reader:
            if len(row) >= 3:
                try:
                    # Expected timestamp format: %Y-%m-%d %H:%M:%S
                    dt = datetime.strptime(row[0], '%Y-%m-%d %H:%M:%S')
                    temp = float(row[1])
                    relay_state = 1 if row[2].strip().upper() == 'ON' else 0
                    
                    timestamps.append(dt)
                    temperatures.append(temp)
                    relay_states.append(relay_state)
                except ValueError:
                    continue # Skip lines with malformed data
except FileNotFoundError:
    print(f"Error: {csv_filename} not found. Please make sure the CSV file is in the same directory.")
    exit(1)

if not timestamps:
    print("No valid data found to plot.")
    exit(1)

print(f"Loaded {len(timestamps)} data points. Generating plot...")

# Create the plot with subplots to access axes
fig, ax1 = plt.subplots(figsize=(10, 6))

# Plot Temperature on primary Y axis
color1 = 'tab:red'
ax1.set_xlabel('Time')
ax1.set_ylabel('Temperature (°C)', color=color1)
ax1.plot(timestamps, temperatures, label='Temperature (°C)', color=color1, linewidth=2)
ax1.tick_params(axis='y', labelcolor=color1)
ax1.grid(True, linestyle='--', alpha=0.7)

# Create a secondary Y axis that shares the same X axis
ax2 = ax1.twinx()

# Plot Relay State on secondary Y axis
color2 = 'tab:blue'

# The user requested the different Y on the left side.
# So we move the primary temperature axis to the right, and put the new relay axis on the left.
ax1.yaxis.tick_right()
ax1.yaxis.set_label_position("right")
ax2.yaxis.tick_left()
ax2.yaxis.set_label_position("left")

ax2.set_ylabel('Relay State', color=color2)
# drawstyle='steps-post' makes it look like a digital signal / switch
ax2.plot(timestamps, relay_states, label='Relay State', color=color2, linewidth=1.5, drawstyle='steps-post', alpha=0.8)
ax2.tick_params(axis='y', labelcolor=color2)
ax2.set_yticks([0, 1])
ax2.set_yticklabels(['OFF', 'ON'])

# Format the x-axis for time
ax1.xaxis.set_major_formatter(mdates.DateFormatter('%H:%M:%S'))
fig.autofmt_xdate() # Rotate dates for better visibility

plt.title('Yogurt Maker Temperature Variation and Relay State')
fig.tight_layout()

# Save plot as simple_plot.png
output_filename = 'simple_plot.png'
plt.savefig(output_filename, dpi=300)
plt.show()
print(f"Plot successfully saved as {output_filename}")

# Uncomment the line below if you want to also display the plot window
# plt.show()
