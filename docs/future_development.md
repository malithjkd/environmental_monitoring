# Future Development: Design Requirements, User Stories, and Implementation Plan

This document serves as the roadmap for transitioning the environmental monitoring system into a robust Open-Source Industrial IoT (IIoT) product. 

---

## 1. System Design Requirements

### Hardware Requirements
- **Industrial Reliability**: The system must operate continuously in high-noise environments using the custom 24V Digital I/O Expansion Board.
- **Power Flexibility**: Must support both 110-240Vac mains input and isolated 24Vdc.
- **Safe Boot / Recovery**: The hardware must provide a physical switch or jumper that forces the Pico W to bypass its main IoT loop upon boot, ensuring it can always be recovered and programmed locally without wiping the flash.

### Software & Firmware Requirements
- **Over-The-Air (OTA) Updates**: The Pico W must periodically fetch and apply `.py` script updates from a designated GitHub repository over Wi-Fi.
- **Resilience**: The firmware must gracefully handle Wi-Fi disconnections, MQTT broker timeouts, and sensor read errors without crashing.
- **Extensibility**: The codebase must be modular, allowing easy integration of new sensors (CO2, temperature, smoke) via UART/I2C/SPI and digital/analog inputs.

### Cloud & AI Analytics Requirements
- **Secure Telemetry**: Data must be transmitted to AWS IoT Core securely using MQTT over TLS.
- **Device Shadow / Digital Twin**: The system must utilize the AWS IoT Device Shadow pattern for two-way communication, ensuring reliable state synchronization even if the Wi-Fi connection drops.
- **Data Retention**: Cloud infrastructure must log historical data for predictive maintenance and trend analysis.
- **Intelligent Reasoning**: The cloud backend must route data to ML/LLM models for physics-aware reasoning (e.g., predicting thermal runaway in server rooms or identifying anomalies in hydroponic environments).

---

## 2. User Stories

### As a System Administrator...
- I want the devices to update their firmware automatically over the air (OTA) so that I do not have to physically visit each sensor node with a laptop.
- I want a dashboard to view the health, connectivity status, and firmware version of all deployed Pico W modules so that I can easily identify offline devices.

### As an Industrial End-User (e.g., Warehouse Manager, Server Room Admin)...
- I want to receive intelligent alerts that explain *why* an anomaly is happening (e.g., "Airflow is restricted causing a temperature spike") rather than just a raw data threshold alert, so I can take precise action.
- I want the system to integrate camera feeds (VLM) for fire safety so I can visually verify smoke or hazards before triggering a facility-wide alarm.

### As an Open-Source Developer...
- I want clear documentation and modular code so that I can easily adapt the system to new use cases like aquaponics or smart car parks.
- I want a reliable "Safe Boot" mechanism so that if I write a bug that loops indefinitely, I can easily connect via `mpremote` and fix it without nuking the board.

---

## 3. Phased Implementation Plan

### Phase 1: Core Reliability & Developer Experience (Current Priority)
1. **Safe Boot Mechanism**: Implement `main.py` logic to read a digital input pin at boot. If pulled high, bypass the main loop and drop to REPL.
2. **GitHub OTA Updates**: Write a MicroPython module that queries the GitHub API for file hashes, downloads updated `.py` files to local storage, and performs a soft reset.
3. **Hardware Integration**: Port existing Senseair S8 and DHT11 code to interface correctly with the 24V Expansion Board's specific GPIO pins.

### Phase 2: Secure Cloud Ingestion & Device Shadow
1. **AWS IoT Core Setup**: Provision IoT "Things", certificates, and policies in AWS.
2. **MicroPython MQTT-TLS**: Implement secure MQTT publishing on the Pico W using `umqtt.simple` and `ussl`.
3. **Device Shadow Integration**: Implement logic on the Pico W to subscribe to its Shadow delta topic, automatically updating its 24V digital outputs based on the cloud's "desired" state.
4. **Data Routing**: Set up AWS IoT Rules to route incoming telemetry to AWS Timestream (for time-series data) or DynamoDB.

### Phase 3: Advanced Sensor Integration & Use Case Expansion
1. **Camera Integration**: Integrate an ESP32-CAM or Raspberry Pi Camera module as an edge device that sends images to the cloud for VLM processing.
2. **Use Case Modules**: Develop specific firmware modules for Server Rooms, Hydroponics, and Fire Safety.

### Phase 4: Open Hybrid Edge AI Strategy
Our strategy for deploying intelligent reasoning (focusing first on Predictive Maintenance) follows a three-step progression:
1. **Gateway AI (Raspberry Pi 5)**: Deploy open-source Edge AI logic (e.g., Node-RED, local ML models) on the Raspberry Pi 5. This handles the heavy lifting locally for maximum privacy and zero connectivity dependence.
2. **Cloud AI (AWS)**: Connect the local gateway and edge devices to AWS IoT Core. Leverage cloud-based LLM/VLMs for complex physics-aware reasoning and fleet-wide predictive maintenance.
3. **True TinyML (Pico W)**: Train highly efficient neural networks (via Edge Impulse or TFLite Micro) and deploy them directly onto the Pico W for instant, disconnected inference (e.g., analyzing high-frequency vibration signatures locally).
