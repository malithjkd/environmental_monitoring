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
mpremote dev /dev/ttyACM10 repl
```

### Step 2: Copy and Update Files
You can upload files from your Raspberry Pi 5 to the Pico:
* **Upload a file** (e.g., upload `air_quality_control.py` as `main.py` so it runs at boot):
  ```bash
  mpremote cp pico/air_quality_control.py :main.py
  ```
  *(Or explicitly on a specific port: `mpremote dev /dev/ttyACM10 cp pico/air_quality_control.py :main.py`)*

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
   mpremote dev /dev/ttyACM10 cp pico/air_quality_control.py :main.py
   ```
3. **Reset and monitor live console output**:
   ```bash
   mpremote dev /dev/ttyACM10 reset repl
   ```
