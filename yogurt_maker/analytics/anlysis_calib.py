import csv
import os

def analyze():
    # Use absolute or relative path that works from the workspace root
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    filepath = os.path.join(base_dir, 'data', 'calibration', '800w_multi_cooker_2026_08_02_22_27_43', 'calibration_data.csv')
    
    if not os.path.exists(filepath):
        print(f"Error: Could not find data file at {filepath}")
        return

    heating = []
    cooling = []
    
    with open(filepath, 'r') as f:
        reader = csv.DictReader(f)
        for row in reader:
            phase = row['phase']
            elapsed = float(row['elapsed_s'])
            temp = float(row['temperature_c'])
            if phase == 'HEATING':
                heating.append({'elapsed_s': elapsed, 'temperature_c': temp})
            elif phase == 'COOLING':
                cooling.append({'elapsed_s': elapsed, 'temperature_c': temp})
                
    if not heating or not cooling:
        print("Missing heating or cooling data in CSV.")
        return
        
    t_start = heating[0]['elapsed_s']
    t_end = heating[-1]['elapsed_s']
    temp_start = heating[0]['temperature_c']
    temp_end = heating[-1]['temperature_c']
    
    # 2L of water = 2kg
    mass = 2.0 
    Cp = 4184 # J/(kg*C)
    
    delta_T = temp_end - temp_start
    total_energy = mass * Cp * delta_T
    
    heating_time = t_end - t_start
    effective_power = total_energy / heating_time if heating_time > 0 else 0
    
    # Find maximum temperature during cooling (thermal soak peak)
    max_temp_entry = max(cooling, key=lambda x: x['temperature_c'])
    t_max = max_temp_entry['elapsed_s']
    
    # Find 10 minutes (600s) from the start of the cooling phase (where lid was opened)
    cool_start = cooling[0]['elapsed_s']
    lid_open_time = cool_start + 600
    
    # Profile 1: from T_max to Lid Open
    cool_phase1 = [r for r in cooling if t_max <= r['elapsed_s'] <= lid_open_time]
    # Profile 2: from Lid Open to end
    cool_phase2 = [r for r in cooling if r['elapsed_s'] > lid_open_time]
    
    rate_1 = (cool_phase1[-1]['temperature_c'] - cool_phase1[0]['temperature_c']) / (cool_phase1[-1]['elapsed_s'] - cool_phase1[0]['elapsed_s']) if len(cool_phase1)>1 else 0
    rate_2 = (cool_phase2[-1]['temperature_c'] - cool_phase2[0]['temperature_c']) / (cool_phase2[-1]['elapsed_s'] - cool_phase2[0]['elapsed_s']) if len(cool_phase2)>1 else 0
    
    print("=== Analysis Results for 800w_multi_cooker_2026_08_02_22_27_43 ===")
    print(f"Total Energy Inserted: {total_energy:.2f} J ({total_energy/1000:.1f} kJ)")
    print(f"Total Heating Time:    {heating_time:.1f} s")
    print(f"Effective Power:       {effective_power:.2f} W")
    print(f"Cooling Rate 1 (T_max to 10 min, lid closed): {rate_1*60:.2f} C/min")
    print(f"Cooling Rate 2 (After 10 min, lid open):      {rate_2*60:.2f} C/min")

if __name__ == "__main__":
    analyze()
