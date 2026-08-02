# Yogurt Maker Temperature Controller

This project is a temperature control system designed for making yogurt. It uses a Raspberry Pi Pico W to monitor the temperature using a DS18B20 sensor and controls a heating element via a relay. It also features a web interface for remote monitoring and a logging script to record temperature variations over time.

## Hardware Requirements
- **Microcontroller**: Raspberry Pi Pico 2 W
- **Temperature Sensor**: DS18B20 (connected to GPIO 3)
- **Relay Module**: Connected to GPIO 15 (controls the heater)
- **Host Machine**: Raspberry Pi Zero 2 W

## Target Temperature
The controller is programmed to maintain the yogurt incubation temperature between **41.5°C and 42.5°C**.
- If the temperature drops below 41.5°C, the heater turns ON.
- If the temperature exceeds 42.5°C, the heater turns OFF.

## Features
1. **Automated Heating**: Maintains optimal temperature range for yogurt fermentation.
2. **Web Dashboard**: Hosts a lightweight web server on the Pico W to display real-time temperature and relay status.
3. **Data Logging**: Includes a host-side Python script to capture and log temperature variations with timestamps into a CSV file.

## Files
- `temperature_controller.py`: The main MicroPython script that runs on the Raspberry Pi Pico W. Handles sensor reading, relay control, and the web server.
- `secrets.py`: Stores the WiFi SSID and password for the Pico W.
- `run_and_log.py`: A Python script intended to be run on the host machine (e.g., Raspberry Pi Zero). It starts the Pico via `mpremote` and logs the serial output (with generated timestamps) to `temperature_log.csv`.

## Usage

### 1. Setup WiFi
Ensure your `secrets.py` file is configured with your local WiFi credentials:
```python
WIFI_NETWORKS = [
    {'ssid': 'YOUR_WIFI_NAME', 'password': 'YOUR_WIFI_PASSWORD'}
]
```

### 2. Running and Logging
To start the controller and begin logging data to a CSV file, connect the Pico to your Raspberry Pi Zero via USB, navigate to this directory, and run the wrapper script:

```bash
cd ~/environmental_monitoring/yogurt_maker
python run_and_log.py
```

*Note: Do not run `mpremote run temperature_controller.py` in a separate terminal while the logger is running, as they will conflict over the USB serial port.*

### 3. Web Monitoring
When the script starts, it will print an IP address to the terminal (e.g., `Listening on http://192.168.1.x`). Open this IP address in any web browser on the same network to view the live dashboard.



#### Copy log file

scp malithjkd@pizero2:~/environmental_monitoring/pico/temperature_log.csv /Users/malithjkd1/Documents/environmental_monitoring/pico/