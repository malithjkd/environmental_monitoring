# CO2 Monitoring System Setup Guide

This guide covers the instructions to set up the CO2 Monitoring System using a Raspberry Pi Pico W (as the sensor node) and a Raspberry Pi 5 (as the web server and data logger).

## 1. Setting up the Raspberry Pi Pico W

First, we need to upload the Python script to the Pico W so it can read the CO2 sensor and send the data over USB.

1. Connect the Pico to your Raspberry Pi 5 via USB.
2. Send the script to the Pico and name it `main.py` so it runs automatically on boot:
   ```bash
   mpremote cp ~/Documents/environmental_monitoring/pico/co2_usb_sender.py :main.py
   ```
3. Restart the Pico to start the program:
   ```bash
   mpremote reset
   ```

## 2. Setting up the Raspberry Pi 5 Server

Next, we'll set up the Python environment for the Flask web server on the Pi 5.

1. Navigate to the project directory:
   ```bash
   cd ~/Documents/environmental_monitoring
   ```
2. Create and activate a virtual environment:
   ```bash
   python3 -m venv venv
   source venv/bin/activate
   ```
3. Install the required dependencies:
   ```bash
   pip install -r requirements.txt
   ```

## 3. Running the Server in the Background (tmux)

To ensure the server keeps running even if your SSH connection drops, you can run it inside a detachable terminal using `tmux`.

1. Create a new `tmux` session named `co2`:
   ```bash
   tmux new -s co2
   ```
2. Start the server (make sure your virtual environment is still activated):
   ```bash
   python app.py
   ```
3. **Detach from the session** (leave it running in the background):
   - Press and hold the **`Ctrl`** key, then press the **`b`** key.
   - Let go of both keys.
   - Press the **`d`** key.

You can now safely close your SSH terminal!

### Reattaching to the Session
If you log back into the Pi 5 later and want to see the server output or stop it, run:
```bash
tmux attach -t co2
```

## 4. Auto-start on Boot

If you want the Raspberry Pi to automatically run these steps every time it powers on, you can set it up using `cron`.

1. Open your user's crontab file:
   ```bash
   crontab -e
   ```
2. If prompted, select your preferred text editor (like `nano`).
3. Scroll to the very bottom of the file and add this exact line:
   ```bash
   @reboot tmux new-session -d -s co2 'bash -c "cd ~/Documents/environmental_monitoring && source .venv/bin/activate && cd co2_monitor && python app.py"'
   ```
4. Save and exit (in `nano`, press `Ctrl+O`, `Enter`, then `Ctrl+X`).

Now, whenever your Raspberry Pi restarts, it will automatically start a detached `tmux` session in the background running your app. You can log in anytime and run `tmux attach -t co2` to check on it.
