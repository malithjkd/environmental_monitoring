# Guide: Accessing and Managing Raspberry Pi Pico from Raspberry Pi 5 Terminal

This guide explains how to connect to, upload code to, and run programs on your **Raspberry Pi Pico** (running MicroPython) using the terminal on your **Raspberry Pi 5**.

---

## 1. Setting Up a Python Virtual Environment (`.venv`)

Modern Raspberry Pi OS releases (based on Debian Bookworm) block global `pip install` commands by default to protect the operating system. You should install command-line tools like `mpremote` and `rshell` inside a virtual environment.

Run the following commands in your project folder (`/Users/malithjkd1/Documents/environmental_monitoring`) on your Raspberry Pi 5 terminal:

1. **Create the virtual environment** (named `.venv`):
   ```bash
   python3 -m venv .venv
   ```

2. **Activate the virtual environment**:
   ```bash
   source .venv/bin/activate
   ```
   *(Your terminal prompt will now show `(.venv)` at the beginning, indicating that any `pip` installs will stay isolated within this folder.)*

3. **Install the dependencies from `requirements.txt`**:
   ```bash
   pip install --upgrade pip
   pip install -r requirements.txt
   ```

> [!TIP]
> Whenever you open a new terminal window to work on your Pico, remember to navigate to this folder and reactivate the environment using:
> ```bash
> cd /Users/malithjkd1/Documents/environmental_monitoring
> source .venv/bin/activate
> ```

   ```bash
   pip freeze > requirements.txt
   ```

---

## 2. Troubleshooting & Finding the Pico's Serial Port

If the serial port doesn't show up with `ls /dev/ttyACM*`, or if you get permission/access errors, follow these troubleshooting steps:

### Step 1: Grant Serial Port Permissions
By default, standard users do not have permissions to read/write to USB serial devices. Run the following command to add your user to the `dialout` group:
```bash
sudo usermod -a -G dialout $USER
```
* **IMPORTANT:** To apply this change immediately without rebooting, run:
  ```bash
  newgrp dialout
  ```

### Step 2: Dynamically Find the Port
If the Pico is connected but `ls /dev/ttyACM*` returns nothing:
1. Unplug the USB cable from the Pico.
2. Run this command to watch system logs:
   ```bash
   dmesg -w
   ```
3. Plug the Pico back in.
4. Watch the terminal for new lines. You should see text like:
   `cdc_acm 1-1.3:1.0: ttyACM0: USB ACM device`
5. Press `Ctrl + C` to stop the log viewer and check the port name mentioned in the output.

If it lists `/dev/ttyACM10` (or any other port), make sure to pass that port explicitly to your tools (e.g., `rshell -p /dev/ttyACM10`).

### Step 3: Fixing "Device or Resource Busy" (Port Locked)
If you get a "device busy" or "port locked" error when running `mpremote` or `rshell`, it means **another process is actively holding the serial connection open** (only one program can talk to `/dev/ttyACM0` at a time).

1. **Kill all background terminal/monitor sessions** instantly:
   ```bash
   sudo fuser -k /dev/ttyACM0
   ```
   *(This terminates any process currently locking `/dev/ttyACM0`.)*

2. **Alternatively, terminate common culprits manually**:
   ```bash
   pkill -f mpremote
   pkill -f rshell
   pkill -f screen
   pkill -f minicom
   ```
   *(Also make sure Thonny IDE or any other MicroPython GUI is completely closed.)*

3. **Disable ModemManager (If it keeps locking the port)**:
   ModemManager in Linux automatically scans new USB serial ports to check if they are cell modems, locking the device for 5–10 seconds. You can safely disable it:
   ```bash
   sudo systemctl stop ModemManager
   sudo systemctl disable ModemManager
   ```

4. **Pico is stuck in a tight loop**:
   If the Pico's current `main.py` is in an infinite loop without sleeping or is blocked in a network socket connect call, the serial driver on the board might hang.
   * *Fix:* Unplug the Pico, plug it back in, and immediately run `mpremote connect /dev/ttyACM0 repl` and press `Ctrl + C` repeatedly to halt execution before `main.py` blocks the serial bus.

---


## 3. Option A: Using `mpremote` (Highly Recommended)

Once your `.venv` is activated and permissions are configured:

### Step 1: Open the Interactive REPL (Python Console)
To access the live MicroPython terminal on the Pico:
```bash
# It automatically detects the Pico's port
mpremote repl
```
* **To exit the REPL:** Press `Ctrl + ]`
* **To soft-reboot the Pico:** Press `Ctrl + D` inside the REPL.

*If you need to specify a non-standard port like `/dev/ttyACM10` explicitly, run:*
```bash
mpremote connect /dev/ttyACM10 repl
```

### Step 2: Copy and Update Files
You can upload files from your Raspberry Pi 5 to the Pico:
* **Upload a file** (e.g., upload `air_quality_control.py` as `main.py` so it runs at boot):
  ```bash
  mpremote cp pico/air_quality_control.py :main.py
  ```
  *(Or explicitly on a specific port: `mpremote connect /dev/ttyACM0 cp pico/air_quality_control.py :main.py`)*

* **List files on the Pico:**
  ```bash
  mpremote ls
  ```

* **Remove a file from the Pico:**
  ```bash
  mpremote rm main.py
  ```

### Step 3: Run a Program on the Pico
To run a Python file immediately on the Pico without saving it permanently:
```bash
mpremote run pico/air_quality_control.py
```
```bash
mpremote run pico/CO2_data_host_sensorair_http.py
```

---

## 4. Option B: Using `rshell` (Interactive Remote Shell)

`rshell` provides an interactive prompt to manage the Pico's filesystem.

### Step 1: Connect to the Pico
```bash
rshell -p /dev/ttyACM10
```
This opens the custom shell prompt (`/board>`).

### Step 2: Manage Files inside `rshell`
* **The Pico's storage** is mapped to `/pyboard/`.
* **Your Raspberry Pi 5's storage** is mapped to your local path.

* **List files on the Pico:**
  ```bash
  ls /pyboard
  ```

* **Upload a file to the Pico:**
  ```bash
  cp pico/air_quality_control.py /pyboard/main.py
  ```

* **Enter the REPL from `rshell`:**
  ```bash
  repl
  ```
  * **To exit the REPL and return to `rshell`:** Press `Ctrl + x`.
  * **To exit `rshell` completely:** Press `Ctrl + d` or type `exit`.

---

## 5. Workflow Example for Your Project

To deploy your active file [air_quality_control.py](file:///Users/malithjkd1/Documents/environmental_monitoring/pico/air_quality_control.py) to your Pico:

1. **Activate the environment**:
   ```bash
   cd /Users/malithjkd1/Documents/environmental_monitoring
   source .venv/bin/activate
   ```
2. **Upload the script as `main.py`**:
   ```bash
   mpremote connect /dev/ttyACM0 cp pico/air_quality_control.py :main.py
   ```
3. **Reset and monitor live console output**:
   ```bash
   mpremote connect /dev/ttyACM0 reset repl
   ```

---

## 6. Nuking (Erasing) and Flashing MicroPython

If your Pico is behaving strangely or you want a completely clean slate, you can erase the entire flash memory (nuke it) and reinstall the MicroPython firmware.

### Step 1: Put the Pico into BOOTSEL Mode
You can do this either via software or hardware.

* **Method A (Software - Fast):** If MicroPython is currently running on `/dev/ttyACM0`, execute:
  ```bash
  mpremote connect /dev/ttyACM0 bootloader
  ```
  *(This will immediately reboot the Pico into BOOTSEL mode and disconnect `/dev/ttyACM0`.)*

* **Method B (Hardware):** 
  1. Unplug the USB cable from the Pico.
  2. Press and hold down the white **BOOTSEL** button on the Pico board.
  3. While holding the button, plug the USB cable back into the Raspberry Pi 5.
  4. Release the **BOOTSEL** button.

### Step 2: Verify the Pico is Mounted as a USB Drive
When the Pico is in BOOTSEL mode, it identifies as a USB mass storage device named **`RPI-RP2`**.
* In Raspberry Pi OS, it usually auto-mounts at:
  `/media/$USER/RPI-RP2/`
* You can verify its mount point by running:
  ```bash
  lsblk
  ```

### Step 3: Erase the Flash (Nuke)
Copy the `flash_nuke.uf2` file to the mounted Pico drive:
```bash
cp pico/flash_nuke.uf2 /media/$USER/RPI-RP2/
```
*The Pico's onboard LED will blink, it will erase the flash, and automatically reboot back into BOOTSEL mode (appearing as `RPI-RP2` again).*

### Step 4: Flash MicroPython (for Pico W)
Since your project uses `network` for Wi-Fi, you have a **Raspberry Pi Pico W**. 

1. **Download the latest Pico W firmware**:
   ```bash
   wget https://micropython.org/resources/firmware/RPI_PICO_W-20241129-v1.24.1.uf2 -O pico/micropython_pico_w.uf2
   ```

2. **Copy the firmware to flash the Pico W**:
   ```bash
   cp pico/micropython_pico_w.uf2 /media/$USER/RPI-RP2/
   ```

*The Pico W will automatically reboot. Within a few seconds, it will start up running MicroPython and will reappear as `/dev/ttyACM0`!*
