# Centella Asiatica Environmental Monitoring

This project contains tools and scripts for monitoring the growing environment of Centella asiatica (Gotu Kola) on a balcony in Singapore. It includes monitoring for artificial lighting (when sunlight is insufficient) as well as temperature and humidity.

## Hardware Components

1. **Light Sensor (PAR)**: 
   - Model: [DFRobot SEN0641](https://wiki.dfrobot.com/sen0641/)
   - Type: RS485 Photosynthetically Active Radiation (PAR) Sensor (400-700nm)
   - Interface: [Seeed Studio RS-485 Shield for Raspberry Pi](https://www.mouser.com/en/ProductDetail/Seeed-Studio/103030295?qs=u16ybLDytRY8GQs97CR9LA%3D%3D&countryCode=SG&currencyCode=SGD)
2. **Temperature & Humidity Sensor**:
   - Details to be integrated.

## Project Structure

- `par_sensor.py`: Script to connect to and read data from the DFRobot SEN0641 PAR sensor via Modbus RTU.
- `requirements.txt`: Python dependencies required to run the scripts.

## Setup Instructions

### 1. Hardware Setup

- Mount the **Seeed Studio RS-485 Shield** onto your Raspberry Pi 3B+.
- Connect the **SEN0641 PAR Sensor** wires to the shield and Pi:
  - **Brown (VCC)**: Connect to a **5V pin** on the Raspberry Pi GPIO or Shield. (Sensor supports DC 5~30V)
  - **Black (GND)**: Connect to a **GND pin** on the shield/Pi.
  - **Yellow (485-A)**: Connect to the **A terminal** on the RS-485 Shield.
  - **Blue (485-B)**: Connect to the **B terminal** on the RS-485 Shield.
- By default, the RS-485 shield uses the Pi's hardware serial port (`/dev/serial0`). Make sure you have enabled the serial port and disabled the serial console using `sudo raspi-config`.
- Update the `SERIAL_PORT` variable in `par_sensor.py` if necessary.

### 2. Software Installation

Ensure you have Python installed. Then, install the required dependencies:

```bash
pip install -r requirements.txt
```

### 3. Running the Sensor Script

To test the PAR sensor and read light intensity (μmol/m²/s):

```bash
python par_sensor.py
```

## Future Enhancements

- Integrate the Temperature and Humidity sensor reading script.
- Combine readings into a single data logger (saving to CSV or a database).
- Implement automated lighting control based on the PAR readings (to trigger grow lights when natural sunlight is low).