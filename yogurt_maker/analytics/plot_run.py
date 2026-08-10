import argparse
import json
import os
from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd
import matplotlib.dates as mdates
from datetime import datetime

def analyze_run(run_dir: str):
    run_path = Path(run_dir)
    csv_file = run_path / "temperature_log.csv"
    meta_file = run_path / "metadata.json"
    
    if not csv_file.exists():
        print(f"Error: {csv_file} not found.")
        return
        
    print(f"Loading data from {csv_file}")
    
    # Read the data
    df = pd.read_csv(csv_file)
    
    # Convert timestamp string to datetime objects
    df['Timestamp'] = pd.to_datetime(df['Timestamp'])
    
    # Read metadata for title
    title = "Yogurt Maker Run Analysis"
    if meta_file.exists():
        with open(meta_file, 'r') as f:
            meta = json.load(f)
            title = f"Run: {meta.get('test_name', 'Unknown')} - {meta.get('machine', 'Unknown')} ({meta.get('timestamp')})"
    
    # Create the plot
    fig, ax1 = plt.subplots(figsize=(12, 6))
    
    # Plot Temperature and Setpoint
    color = 'tab:red'
    ax1.set_xlabel('Time')
    ax1.set_ylabel('Temperature (°C)', color=color)
    ax1.plot(df['Timestamp'], df['Temperature_C'], color=color, label='Actual Temp', linewidth=2)
    ax1.plot(df['Timestamp'], df['Setpoint_C'], color='tab:orange', linestyle='--', label='Setpoint', linewidth=2)
    ax1.tick_params(axis='y', labelcolor=color)
    ax1.grid(True, alpha=0.3)
    
    # Format x-axis to show time properly
    ax1.xaxis.set_major_formatter(mdates.DateFormatter('%H:%M:%S'))
    plt.xticks(rotation=45)
    
    # Plot Duty Cycle on secondary Y axis
    ax2 = ax1.twinx()  
    color = 'tab:blue'
    ax2.set_ylabel('Duty Cycle / Relay State', color=color)  
    ax2.plot(df['Timestamp'], df['Duty_Cycle'], color=color, alpha=0.3, label='Duty Cycle')
    ax2.plot(df['Timestamp'], df['Relay_State'], color='tab:green', alpha=0.3, label='Relay State')
    ax2.tick_params(axis='y', labelcolor=color)
    
    # Combine legends
    lines1, labels1 = ax1.get_legend_handles_labels()
    lines2, labels2 = ax2.get_legend_handles_labels()
    ax1.legend(lines1 + lines2, labels1 + labels2, loc='upper left')
    
    plt.title(title)
    fig.tight_layout()
    
    # Save the plot
    output_img = run_path / "temperature_profile.png"
    plt.savefig(output_img, dpi=300)
    print(f"Plot saved to {output_img}")
    
    # Basic analysis
    print("\n--- Basic Statistics ---")
    print(f"Total Duration: {df['Timestamp'].iloc[-1] - df['Timestamp'].iloc[0]}")
    print(f"Max Temperature: {df['Temperature_C'].max():.2f} °C")
    
    # Analyze stages
    if 'Stage' in df.columns:
        print("\n--- Time spent in stages ---")
        stages = df['Stage'].unique()
        for stage in stages:
            stage_data = df[df['Stage'] == stage]
            if not stage_data.empty:
                duration = stage_data['Timestamp'].iloc[-1] - stage_data['Timestamp'].iloc[0]
                print(f"{stage}: {duration}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Analyze yogurt maker run data')
    parser.add_argument('run_dir', help='Path to the run directory (e.g., data/2026_08_08_...)')
    args = parser.parse_args()
    
    analyze_run(args.run_dir)
