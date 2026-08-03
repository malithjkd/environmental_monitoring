from flask import Flask, render_template, jsonify
import serial
import serial.tools.list_ports
import threading
import time
from data_logger import DataLogger

app = Flask(__name__)
logger = DataLogger()

# Serial reading thread control
serial_thread = None
running = True
current_co2 = None

def find_pico_port():
    """Find the serial port for the Raspberry Pi Pico"""
    ports = serial.tools.list_ports.comports()
    for port, desc, hwid in sorted(ports):
        # Common identifiers for Raspberry Pi Pico
        if "Board in FS mode" in desc or "Pico" in desc or "2E8A" in hwid:
            return port
    
    # Fallback common Linux ports
    for p in ['/dev/ttyACM0', '/dev/ttyACM1', '/dev/ttyUSB0']:
        try:
            # Just check if it exists
            serial.Serial(p).close()
            return p
        except:
            pass
    return None

def read_serial_data():
    global current_co2
    port_name = find_pico_port()
    
    if not port_name:
        print("Warning: Could not find Pico serial port.")
        return

    try:
        print(f"Connecting to Pico on {port_name}...")
        with serial.Serial(port_name, 9600, timeout=1) as ser:
            print("Connected. Listening for CO2 data...")
            while running:
                if ser.in_waiting > 0:
                    try:
                        line = ser.readline().decode('utf-8', errors='ignore').strip()
                        if line:
                            print(f"Pico says: {line}")
                        if line.startswith("CO2:"):
                            val_str = line.split(":")[1]
                            if val_str != "ERROR":
                                current_co2 = int(val_str)
                                logger.log_reading(current_co2)
                                print(f"Logged CO2: {current_co2} ppm")
                    except Exception as e:
                        print(f"Error parsing serial data: {e}")
                time.sleep(0.1)
    except Exception as e:
        print(f"Serial port error: {e}")

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/data')
def get_data():
    history = logger.get_history()
    return jsonify({
        'current_co2': current_co2,
        'history': history,
        'alert_threshold': 800
    })

if __name__ == '__main__':
    # Start the serial reader in a background thread
    serial_thread = threading.Thread(target=read_serial_data, daemon=True)
    serial_thread.start()
    
    try:
        # Run the Flask app on all interfaces, port 5000
        app.run(host='0.0.0.0', port=5000, debug=False)
    finally:
        running = False
        if serial_thread:
            serial_thread.join(timeout=2)
