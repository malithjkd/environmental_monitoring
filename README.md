# Open-Source Industrial IoT Environmental Monitoring

## Project Vision
This project provides an open-source, low-cost, yet highly reliable alternative to expensive, closed-source industrial monitoring solutions. 

Originally designed for home use, the project has evolved into a versatile Industrial IoT (IIoT) platform capable of serving:
- Server Rooms (incorporating features from `projectRakitha`)
- Warehouses and Office Spaces
- Car Parks
- Indoor Gardening, Hydroponics, and Aquaponics
- Security and Fire Safety (integrating camera systems)

By combining robust 24V industrial hardware with intelligent cloud analysis, the system moves beyond simple rule-based alerts to leverage Machine Learning (ML), Large Language Models (LLMs), and Vision-Language Models (VLMs) for physics-aware reasoning and predictive maintenance.

---

## Hardware: 24V Digital I/O Expansion Board

To ensure industrial-grade reliability and noise immunity, the system relies on a custom 24V Digital I/O Expansion Board for the Raspberry Pi Pico W.

**Key Hardware Specifications:**
- **Power Options**: 110-240Vac mains input or isolated 24Vdc.
- **Digital Outputs**: 9x 24Vdc outputs (100mA load).
- **Digital Inputs**: 6x 24Vdc isolated inputs.
- **Analog Inputs**: 3x 3.3Vdc analog inputs.
- **Communication**: UART/I2C/SPI on 3.3V logic.

*For full schematic and connector pinouts, refer to the [Hardware Datasheet](docs/hardware_desing/EAI0001_datasheet.md).*

---

## Cloud Architecture: AWS IoT Device Shadow & AI Reasoning

The system uses **AWS IoT Core** as the primary data backbone, communicating securely via MQTT over TLS. 

**Modern Digital Twin Architecture (Device Shadow):**
Rather than relying on fragile, raw two-way messaging, the system implements the **AWS IoT Device Shadow** pattern.
- The cloud maintains a JSON "Shadow" of the Pico W's state (e.g., all 9 digital outputs).
- The Pico W simply syncs its local state with the cloud's "desired" state. If the Wi-Fi drops, the cloud retains the command, and the Pico W catches up the instant it reconnects, ensuring enterprise-grade reliability without polling overhead.

**Open Hybrid Edge AI Strategy:**
We are pursuing a step-by-step hybrid approach to intelligence, focusing first on **Predictive Maintenance**. The data processing and AI reasoning will be rolled out in three phases:
1. **Gateway AI (Raspberry Pi 5)**: Initial heavy lifting and predictive models will run on a local Raspberry Pi 5 gateway to ensure privacy and low latency without internet dependence.
2. **Cloud AI (AWS IoT Core)**: Advanced analytics, LLMs, and fleet-wide data retention will be handled by AWS IoT Core and its Device Shadow service.
3. **True TinyML (Pico W Edge)**: Highly optimized neural networks (TinyML) will eventually be pushed directly down to the Pico W for instant, disconnected inference.

**Intelligent Pipeline:**
1. **Edge**: Pico W reads sensor data (vibration, acoustics, CO2, temp) and syncs state. 
2. **Ingestion**: Telemetry is published securely to the local RPi5 Gateway (and later AWS IoT Core).
3. **Reasoning**: AI models process the data to predict anomalies (e.g., motor bearing failure) and update the "desired" state of the system to trigger 24V actions automatically.
4. **OTA Upgrades**: The Pico W's features and TinyML models can be seamlessly upgraded via the remote OTA mechanism.

---

## Firmware & Over-The-Air (OTA) Updates

Due to the nature of continuous IoT loops, connecting to the Pico W via USB while it is running can lock the serial port, requiring a flash wipe. To solve this, the firmware implements two key features:

### 1. Safe Boot Mode
The `main.py` script checks for a specific hardware button press (or a configuration flag) at boot. If triggered, it bypasses the main execution loop, allowing safe USB/`mpremote` access.

### 2. OTA Updates via GitHub
To simplify fleet management, the Pico W supports fetching Over-The-Air firmware updates directly from this GitHub repository.
- The Pico W periodically checks the repository for newer versions of its `.py` files.
- If an update is found, it downloads the files over Wi-Fi and triggers a soft reboot.
- *Note: Future iterations may migrate this secure fetch mechanism to AWS S3, but GitHub provides excellent convenience for rapid prototyping.*

---

## Local Development Setup

If you need to program the device locally using a Raspberry Pi 5 terminal:

1. **Virtual Environment**:
   ```bash
   python3 -m venv .venv
   source .venv/bin/activate
   pip install --upgrade pip
   pip install -r requirements.txt
   ```
2. **Accessing the Pico W (`mpremote`)**:
   ```bash
   mpremote repl
   ```
3. **Uploading Code**:
   ```bash
   mpremote cp pico/air_quality_control.py :main.py
   ```

---

## Roadmap & Future Development

To view our detailed system design requirements, user stories, and phased implementation roadmap (including AWS IoT Core integration and AI analytics features), please read our [Future Development Plan](docs/future_development.md).
