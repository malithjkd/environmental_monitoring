# Smart Yogurt Maker - Project Log & Testing

## Overview
This logbook is maintained for AI agents and the user to understand the physical dynamics of the yogurt maker setup and to document the history of experimental tests.

## Physics Insights (800W Multi-Cooker, 2L Water Setup)
From the first calibration test (`800w_multi_cooker_2026_08_02_22_27_43`), we derived the following characteristics of the system:
- **Total Energy to reach ~75°C**: ~384.4 kJ
- **Heating Time**: ~514 seconds (8.5 minutes)
- **Effective Power Output**: ~748 Watts (Highly efficient transfer into the 2L water volume).
- **Thermal Soak**: When heating stops, the residual heat from the cooker plate causes the water temperature to continue rising for several minutes.
- **Cooling Rate (Lid Closed)**: -0.24 °C/min (Measured *after* peak thermal soak).
- **Cooling Rate (Lid Open)**: -0.74 °C/min.

## Test History

### Test 1: Baseline Physics Calibration
- **Folder**: `data/calibration/800w_multi_cooker_2026_08_02_22_27_43`
- **Setup**: 2L water bath, no pot. Sensor in the bath. Lid closed for the first 10 minutes of cooling, then open.
- **Purpose**: Calculate baseline energy requirements, heating rate, thermal soak delay, and two cooling profiles.

### Test 2: Milk/Pot Calibration
- **Folder**: `data/calibration/800w_multi_cooker_2026_08_07_19_06_32`
- **Setup**: 1.75L water bath + 0.25L milk inside a porcelain pot. Sensor in the surrounding water bath.
- **Purpose**: Understand the thermal mass of the combined pot+milk system when controlling via the water bath. 

### Test 3: First Yogurt Making Attempt
- **Folder**: `data/2026_08_08_08_13_46`
- **Setup**: Full yogurt process run.
- **Outcome**: Good temperature accuracy, but the total process time exceeded 12 hours due to the extremely slow initial heating and cooling phases.

---

## Next Steps: Process Time Optimization

### Proposed Test 4: Rapid Heating & Manual Cooling Dynamics
To reduce the 12-hour cycle time, we need to determine how fast the milk responds to extreme transients (rapid heating and rapid manual cooling) without destabilizing the PID controller.

**Setup**:
1. 1.75L water in the bath, 0.25L water in the porcelain pot (simulating milk).
2. The DS18B20 sensor stays in the **water bath** for the PID controller. 
3. Use a **separate manual kitchen thermometer** to check the temperature inside the porcelain pot.
4. **Log your readings**: Whenever you measure the pot temperature, type it into the **"Log Manual Pot Temp (°C)"** box on the web dashboard and click **"Log to CSV"**. This ensures your manual readings are perfectly synced with the automated sensor data.

**Procedure**:
1. **Rapid Heating**: Start the pasteurization phase (target 85°C). 
   - *Schedule*: Measure the pot temperature every 2 minutes while heating.
   - *Critical Measurement*: The moment the dashboard indicates the water bath has reached 85°C, measure the pot temperature immediately. Then measure the pot temperature every 1 minute until the pot also reaches 85°C.
2. **Hold Phase**: Keep the bath at 85°C for 10 minutes.
   - *Schedule*: Measure the pot temperature at the 5-minute mark and the 10-minute mark to check if it stabilizes.
3. **Rapid Cooling (Manual Water Swap)**: 
   - Set the dashboard target to 42°C (FERMENT).
   - Manually scoop out the hot water bath and pour in cold tap water until the bath hits ~42°C.
   - *Schedule*: Measure the pot temperature every 2 minutes. Record exactly how many minutes it takes for the pot to drop from 85°C to 45°C.

*Agent Note: Do not write logic that asks the user to move the PID sensor during a run, as this disrupts the controller's PWM cycle.*
