import csv
import sys

def analyze():
    filepath = 'data/2026_08_10_15_54_10/temperature_log.csv'
    
    manual_temps = []
    
    with open(filepath, 'r') as f:
        reader = csv.DictReader(f)
        for row in reader:
            if 'Manual_Temp_C' in row and row['Manual_Temp_C']:
                manual_temps.append({
                    'elapsed_s': float(row['Elapsed_s']),
                    'bath_temp': float(row['Temperature_C']),
                    'pot_temp': float(row['Manual_Temp_C']),
                    'stage': row['Stage']
                })
                
    if not manual_temps:
        print("No manual temperatures found in the CSV.")
        return
        
    print(f"Found {len(manual_temps)} manual temperature readings:")
    for mt in manual_temps:
        print(f"Elapsed: {mt['elapsed_s']:.1f}s | Stage: {mt['stage']} | Bath: {mt['bath_temp']:.1f}C | Pot: {mt['pot_temp']:.1f}C")

if __name__ == "__main__":
    analyze()
