# Smart Yogurt Maker

A physics-informed temperature control system for making yogurt. Uses a Raspberry Pi Pico 2 W as an autonomous controller and a Raspberry Pi Zero 2W as the host server with a web dashboard.

## Architecture

```
┌─────────────────────────────────────┐
│  Raspberry Pi Zero 2W (Server)      │
│  ┌────────────────────────────────┐ │
│  │ FastAPI Web Server (port 8000) │ │
│  │  - Web Dashboard               │ │
│  │  - Script Generator            │ │
│  │  - Serial Monitor & Logger     │ │
│  └───────────┬────────────────────┘ │
│              │ USB Serial            │
└──────────────┼──────────────────────┘
               │
┌──────────────┼──────────────────────┐
│  Raspberry Pi Pico 2 W (Controller) │
│  ┌───────────┴────────────────────┐ │
│  │ pico_controller.py (autonomous)│ │
│  │  - Physics-Informed PID        │ │
│  │  - Slow PWM via SSR            │ │
│  │  - Multi-stage state machine   │ │
│  └──────┬──────────────┬──────────┘ │
│         │              │             │
│    DS18B20 Sensor   SSR Relay        │
│    (GPIO 3)         (GPIO 15)        │
└──────────────────────────────────────┘
```

## Hardware Requirements
- **Microcontroller**: Raspberry Pi Pico 2 W
- **Temperature Sensor**: DS18B20 (connected to GPIO 3)
- **Relay Module**: SSR (Solid State Relay) on GPIO 15
- **Host Machine**: Raspberry Pi Zero 2 W

## Supported Machines
| Machine | Power | Notes |
|---------|-------|-------|
| 800W Multi Cooker | 800W | High power, requires careful duty control |
| 500W Rice Cooker (Warm Setting) | ~150W effective | Low power, gentle heating |
| 800W Rice Cooker (Cook Setting) | 800W | Can exceed 100°C |

## Yogurt Making Process (Multi-Stage)

1. **PASTEURIZE** — Heat milk to 85°C (controlled ramp)
2. **HOLD_85** — Hold at 85°C for 5 minutes
3. **COOL_DOWN** — Heater OFF, passive cooling to ~43°C
4. **FERMENT** — Hold at 42°C ± 0.5°C for 6–12 hours
5. **DONE** — Heater OFF, process complete

## Control Strategy

The system uses a **physics-informed PID** controller:

- **Feedforward**: Calculates the steady-state duty cycle from the thermal energy balance:
  `duty = k_cool × (T_target − T_ambient) / P`
- **PID Feedback**: Provides correction for disturbances and transients
- **Slow PWM**: Converts the 0–100% duty cycle into ON/OFF switching within a 30-second window via the SSR

The thermal model parameters (`k_cool`, effective power) are determined through calibration tests for each machine and water volume.

## Project Files

### Core
| File | Runs On | Description |
|------|---------|-------------|
| `pico_template.py` | — | MicroPython template with `{{CONFIG}}` markers |
| `server.py` | Pi Zero 2W | FastAPI server, script generator, serial monitor |
| `config.json` | Pi Zero 2W | Machine profiles with PID & thermal constants |

### Calibration
| File | Runs On | Description |
|------|---------|-------------|
| `calibration_test.py` | Pico W | Heating/cooling test for thermal parameter ID |
| `calibration_runner.py` | Pi Zero 2W | Deploys calibration test and captures data |
| `calibration_analyzer.py` | Mac/Pi | Computes `k_cool`, suggests PID constants, plots |

### Dashboard
| File | Description |
|------|-------------|
| `static/index.html` | Web dashboard |
| `static/style.css` | Dark theme with glassmorphism |
| `static/app.js` | SSE real-time updates, Chart.js charting |

### Utilities
| File | Runs On | Description |
|------|---------|-------------|
| `run_and_log.py` | Pi Zero 2W | Standalone logger (mpremote + CSV) |
| `plot_temperature.py` | Mac | Matplotlib plotting |

## Quick Start

### 1. Calibrate a Machine
```bash
# On Pi Zero 2W
cd ~/environmental_monitoring/yogurt_maker
source ../.venv/bin/activate
python calibration_runner.py --machine 800w_multi_cooker --volume 1.5

# On Mac (analysis + plotting)
python calibration_analyzer.py data/calibration/<run_dir>
```

### 2. Update config.json
Copy the `k_cool` and `pid` values from `thermal_parameters.json` into `config.json`.

### 3. Start the Server
```bash
# On Pi Zero 2W
cd ~/environmental_monitoring/yogurt_maker
source ../.venv/bin/activate
pip install -r requirements.txt
python server.py
```

### 4. Open the Dashboard
Navigate to `http://<pi-zero-ip>:8000` in your browser. Select the machine, enter the water volume, and click **Start Process**.

### 5. Copy Data for Analysis
```bash
scp -r malithjkd@pizero2:~/environmental_monitoring/yogurt_maker/data/ \
    /Users/malithjkd1/Documents/environmental_monitoring/yogurt_maker/data/
```

## Yogurt Starter Reference
https://yogourmet.com/en/canada/product-details/mild-yogurt-starter/
