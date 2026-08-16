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
- **Cooling Rate (Water Swap)**: ~-15 to -30 °C/min during active swapping.
- **Thermal Lag (Porcelain Pot)**: The thick porcelain pot creates a massive thermal time constant (tau = ~2.8 hours). The temperature inside the pot lags the water bath temperature by approximately **10 minutes**.

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
- **Outcome**: Good temperature accuracy, but the total process time exceeded 12 hours due to the extremely slow initial heating and cooling phases.

### Test 5: Successful Yogurt Production & Manual Cooling Analysis
- **Folder**: `data/2026_08_11_20_50_28`
- **Setup**: Full yogurt process run with actual milk.
- **Outcome**: Successfully created yogurt! However, heating took ~3.8 hours using the standard PID feedforward. 
- **Cooling Analysis**: User performed manual water swaps. The temperature dropped from 87°C to 45°C in **41 minutes** through a series of water swaps. Key finding: The pot re-heats the new cold water very quickly (bouncing from 70°C up to 71°C) due to thermal lag, requiring multiple small water swaps rather than one big one.

---

## Next Steps: Rapid Heat Testing

The system has been upgraded to a 6-stage process to eliminate the 3.8-hour heat-up time:
`RAPID_HEAT` → `PASTEURIZE` → `HOLD_85` → `COOL_DOWN` → `FERMENT` → `DONE`

**Test 6 Objectives**:
1. Verify the `RAPID_HEAT` phase (runs at 80% duty cycle until 70°C) correctly hands over to PID control for the final 15°C climb to 85°C without dangerous overshoot.
2. Verify the dashboard features: Sensor Location logging, CSV Pause/Resume (for moving the sensor safely), and Water Swap logging.

**Procedure for Test 6**:
1. Set sensor location to `water_bath` on the dashboard.
2. Start the process. The system should rapidly heat to 70°C, then gracefully approach 85°C.
3. Hold for 20 minutes (now configurable on the dashboard).
4. When `COOL_DOWN` starts, the "Water Swapped" button will pulse. Perform manual water swaps to bring the temp down to ~45°C, clicking the button when you do.
5. If you want to check the milk temperature, click "Pause Logging", move the sensor into the pot, change the location dropdown to `inside_pot`, and click "Resume Logging".
