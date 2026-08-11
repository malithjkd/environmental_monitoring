import csv

filepath = 'data/calibration/800w_multi_cooker_2026_08_02_22_27_43/calibration_data.csv'
max_temp = 0
off_temp = 0
heater_on = True

with open(filepath, 'r') as f:
    reader = csv.DictReader(f)
    for row in reader:
        temp = float(row['temperature_c'])
        # In Test 1, relay was likely '1' or '0' as strings
        relay = int(float(row.get('relay_state', 1)))
        if heater_on and relay == 0:
            heater_on = False
            off_temp = temp
            print(f'Heater turned off at {off_temp}C')
        if temp > max_temp:
            max_temp = temp

print(f'Max temp reached: {max_temp}C')
print(f'Thermal soak overshoot: {max_temp - off_temp}C')
