"""Smart Yogurt Maker — FastAPI Server (Pi Zero 2W)

Runs on the Raspberry Pi Zero 2W. Provides:
  1. Web dashboard for controlling the yogurt-making process
  2. Script generator: fills pico_template.py with user config
  3. Deployment engine: pushes generated script to Pico via mpremote
  4. Serial monitor: reads Pico output for live dashboard + CSV logging

Usage:
    cd ~/environmental_monitoring/yogurt_maker
    source ../.venv/bin/activate
    uvicorn server:app --host 0.0.0.0 --port 8000

Or simply:
    python server.py
"""

import asyncio
import json
import os
import re
import subprocess
import sys
import threading
import time
from collections import deque
from datetime import datetime
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles

# ============================================================
# App & Config
# ============================================================
BASE_DIR = Path(__file__).parent
DATA_DIR = BASE_DIR / "data"
TEMPLATE_PATH = BASE_DIR / "pico_template.py"
CONFIG_PATH = BASE_DIR / "config.json"
STATIC_DIR = BASE_DIR / "static"
GENERATED_DIR = BASE_DIR / "generated"

app = FastAPI(title="Smart Yogurt Maker", version="1.0.0")

# Serve static files
if STATIC_DIR.exists():
    app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")


# ============================================================
# Pico Manager — handles deployment, monitoring, and logging
# ============================================================
class PicoManager:
    def __init__(self):
        self.process = None
        self.monitor_thread = None
        self.running = False
        self.lock = threading.Lock()

        # Live data
        self.current_status = {
            "t": 0, "sp": 0, "duty": 0, "relay": 0,
            "stage": "IDLE", "elapsed": 0, "stage_elapsed": 0,
            "connected": False
        }
        self.history = deque(maxlen=21600)  # 12 hours at 2s intervals

        # Logging
        self.csv_file = None
        self.raw_log_file = None
        self.run_dir = None
        self.active_config = None
        self.manual_temp = None

        # Sensor placement & CSV control
        self.sensor_location = "water_bath"  # or "inside_pot"
        self.csv_paused = False
        self.water_swap_logged = False

    def generate_script(self, user_config: dict) -> str:
        """Read pico_template.py and inject the CONFIG block."""
        template = TEMPLATE_PATH.read_text()

        # Build the CONFIG dict for the Pico
        pico_config = {
            "machine_name": user_config.get("machine_name", "Unknown"),
            "power_watts": user_config["power_watts"],
            "water_mass_kg": user_config["water_volume_liters"],  # 1L ≈ 1kg
            "k_cool": user_config["k_cool"],
            "ambient_temp": user_config.get("ambient_temp", 25.0),
            "kp": user_config["kp"],
            "ki": user_config["ki"],
            "kd": user_config["kd"],
            "pwm_window_s": user_config.get("pwm_window_s", 30),
            "rapid_heat_duty": user_config.get("rapid_heat_duty", 0.80),
            "rapid_heat_cutoff_temp": user_config.get("rapid_heat_cutoff_temp", 70.0),
            "pasteurize_temp": user_config.get("pasteurize_temp", 85.0),
            "pasteurize_tolerance": user_config.get("pasteurize_tolerance", 1.0),
            "hold_85_duration_s": user_config.get("hold_85_duration_s", 1200),
            "ferment_temp": user_config.get("ferment_temp", 42.0),
            "ferment_tolerance": user_config.get("ferment_tolerance", 0.5),
            "ferment_duration_s": user_config.get("ferment_duration_s", 28800),
            "safety_max_temp": user_config.get("safety_max_temp", 95.0),
            "sensor_pin": user_config.get("sensor_pin", 3),
            "relay_pin": user_config.get("relay_pin", 12),
        }

        # Replace the CONFIG block between markers
        config_str = f"CONFIG = {json.dumps(pico_config, indent=4)}"
        pattern = r"# __CONFIG_START__\n.*?# __CONFIG_END__"
        replacement = f"# __CONFIG_START__\n{config_str}\n# __CONFIG_END__"
        generated = re.sub(pattern, replacement, template, flags=re.DOTALL)

        # Save generated script
        GENERATED_DIR.mkdir(exist_ok=True)
        output_path = GENERATED_DIR / "pico_controller_generated.py"
        output_path.write_text(generated)

        return str(output_path)

    def deploy_and_start(self, user_config: dict):
        """Generate script, deploy to Pico, and start monitoring."""
        # Stop any existing process
        self.stop()

        # Generate the script
        script_path = self.generate_script(user_config)
        self.active_config = user_config

        # Create logging directory
        timestamp = datetime.now().strftime("%Y_%m_%d_%H_%M_%S")
        self.run_dir = DATA_DIR / timestamp
        self.run_dir.mkdir(parents=True, exist_ok=True)

        # Save metadata
        metadata = {
            "test_name": "Smart Yogurt Maker Run",
            "timestamp": timestamp,
            "machine": user_config.get("machine_name", "Unknown"),
            "machine_id": user_config.get("machine_id", ""),
            "power_watts": user_config["power_watts"],
            "water_volume_liters": user_config["water_volume_liters"],
            "target_temperature_C": user_config.get("ferment_temp", 42.0),
            "pasteurize_temp_C": user_config.get("pasteurize_temp", 85.0),
            "hold_85_duration_s": user_config.get("hold_85_duration_s", 300),
            "ferment_duration_s": user_config.get("ferment_duration_s", 28800),
            "sensor_type": "DS18B20",
            "control_method": "Physics-Informed PID + Slow PWM",
            "pid": {
                "kp": user_config["kp"],
                "ki": user_config["ki"],
                "kd": user_config["kd"],
            },
            "k_cool": user_config["k_cool"],
        }
        with open(self.run_dir / "metadata.json", "w") as f:
            json.dump(metadata, f, indent=4)

        # Save a copy of the generated Pico controller script for debugging/tracking
        generated_script_dest = self.run_dir / "pico_controller_generated.py"
        try:
            generated_script_dest.write_text(generated_script)
        except Exception as e:
            print(f"Warning: Failed to save generated script to run directory: {e}")

        # Open log files
        csv_path = self.run_dir / "temperature_log.csv"
        self.csv_file = open(csv_path, "w")
        self.csv_file.write(
            "Timestamp,Temperature_C,Setpoint_C,Duty_Cycle,Relay_State,Stage,Elapsed_s,Stage_Elapsed_s,Manual_Temp_C,Sensor_Location,Event,PID_P,PID_I,PID_D,PID_Integral\n"
        )

        raw_log_path = self.run_dir / "raw_output.log"
        self.raw_log_file = open(raw_log_path, "w")

        # Clear history and reset sensor state for new run
        self.history.clear()
        self.sensor_location = "water_bath"
        self.csv_paused = False
        self.water_swap_logged = False

        # Reset Pico before deploying
        try:
            subprocess.run(
                ["mpremote", "reset"],
                timeout=5,
                capture_output=True,
                text=True,
            )
            time.sleep(2)  # Wait for Pico to reboot
        except Exception as e:
            print(f"Warning: Could not reset Pico: {e}")

        # Start mpremote run with the generated script
        self.process = subprocess.Popen(
            ["mpremote", "run", script_path],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,
        )

        self.running = True
        with self.lock:
            self.current_status["connected"] = True
            self.current_status["stage"] = "STARTING"

        # Start monitor thread
        self.monitor_thread = threading.Thread(
            target=self._monitor_serial, daemon=True
        )
        self.monitor_thread.start()
        print(f"✓ Deployed and monitoring. Data → {self.run_dir}")

    def stop(self):
        """Stop the current process and clean up."""
        self.running = False

        if self.process:
            try:
                self.process.terminate()
                self.process.wait(timeout=5)
            except Exception:
                try:
                    self.process.kill()
                except Exception:
                    pass
            self.process = None

        # Reset Pico (ensures relay is off)
        try:
            subprocess.run(
                ["mpremote", "reset"],
                timeout=5,
                capture_output=True,
                text=True,
            )
        except Exception:
            pass

        # Close log files
        if self.csv_file:
            self.csv_file.close()
            self.csv_file = None
        if self.raw_log_file:
            self.raw_log_file.close()
            self.raw_log_file = None

        with self.lock:
            self.current_status["connected"] = False
            self.current_status["stage"] = "IDLE"
            self.current_status["relay"] = 0
            self.current_status["duty"] = 0

    def _monitor_serial(self):
        """Background thread: read serial output from mpremote."""
        while self.running and self.process:
            try:
                line = self.process.stdout.readline()
            except Exception:
                break

            if not line:
                break

            line = line.strip()
            if not line:
                continue

            # Log raw output
            if self.raw_log_file:
                self.raw_log_file.write(line + "\n")
                self.raw_log_file.flush()

            # Try to parse JSON status
            if line.startswith("{"):
                try:
                    data = json.loads(line)
                except json.JSONDecodeError:
                    continue

                # Check if this is a status update (has "t" key)
                if "t" in data:
                    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

                    with self.lock:
                        self.current_status.update({
                            "t": data.get("t", 0),
                            "sp": data.get("sp", 0),
                            "duty": data.get("duty", 0),
                            "relay": data.get("relay", 0),
                            "stage": data.get("stage", "?"),
                            "elapsed": data.get("elapsed", 0),
                            "stage_elapsed": data.get("stage_elapsed", 0),
                            "pid_p": data.get("pid_p", 0),
                            "pid_i": data.get("pid_i", 0),
                            "pid_int": data.get("pid_int", 0),
                            "connected": True,
                            "timestamp": now_str,
                        })

                    # Append to history
                    history_point = {"timestamp": now_str, **data}
                    self.history.append(history_point)

                    # Write to CSV (respects pause state)
                    if self.csv_file and not self.csv_paused:
                        mt_str = str(self.manual_temp) if self.manual_temp is not None else ""
                        event_str = ""
                        if self.water_swap_logged:
                            event_str = "water_swap"
                            self.water_swap_logged = False
                        self.csv_file.write(
                            f"{now_str},"
                            f"{data.get('t', 0)},"
                            f"{data.get('sp', 0)},"
                            f"{data.get('duty', 0)},"
                            f"{data.get('relay', 0)},"
                            f"{data.get('stage', '')},"
                            f"{data.get('elapsed', 0)},"
                            f"{data.get('stage_elapsed', 0)},"
                            f"{mt_str},"
                            f"{self.sensor_location},"
                            f"{event_str},"
                            f"{data.get('pid_p', '')},"
                            f"{data.get('pid_i', '')},"
                            f"{data.get('pid_d', '')},"
                            f"{data.get('pid_int', '')}\n"
                        )
                        self.csv_file.flush()
                        self.manual_temp = None

                # Print messages to server console
                if "msg" in data:
                    print(f"[Pico] {data['msg']}: {data}")

        # Process ended
        with self.lock:
            self.current_status["connected"] = False
        print("Serial monitor ended.")

    def get_status(self) -> dict:
        with self.lock:
            status = dict(self.current_status)
            status["sensor_location"] = self.sensor_location
            status["csv_paused"] = self.csv_paused
            return status

    def get_history(self, minutes: int = 60) -> list:
        """Return recent history points."""
        # At 2s intervals, minutes * 30 = number of points
        max_points = minutes * 30
        with self.lock:
            items = list(self.history)
        return items[-max_points:]


# Global Pico manager
pico = PicoManager()


# ============================================================
# API Endpoints
# ============================================================
@app.get("/", response_class=HTMLResponse)
async def root():
    """Serve the web dashboard."""
    index_path = STATIC_DIR / "index.html"
    if not index_path.exists():
        return HTMLResponse("<h1>Dashboard not found. Place index.html in static/</h1>")
    return HTMLResponse(index_path.read_text())


@app.get("/api/status")
async def api_status():
    """Get current Pico status."""
    return pico.get_status()


@app.get("/api/history")
async def api_history(minutes: int = 60):
    """Get temperature history for charting."""
    return pico.get_history(minutes)


@app.get("/api/machines")
async def api_machines():
    """Get available machine profiles from config.json."""
    try:
        with open(CONFIG_PATH) as f:
            return json.load(f)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="config.json not found")


@app.post("/api/start")
async def api_start(request: dict):
    """Start a yogurt-making process.

    Expected body:
    {
        "machine": "800w_multi_cooker",
        "water_volume_liters": 1.5,
        "pasteurize_temp": 85.0,
        "hold_85_duration_min": 5,
        "ferment_temp": 42.0,
        "ferment_duration_hours": 8,
        "ambient_temp": 25.0
    }
    """
    machine_id = request.get("machine")
    if not machine_id:
        raise HTTPException(status_code=400, detail="Missing 'machine' field")

    # Load machine profile
    with open(CONFIG_PATH) as f:
        config = json.load(f)

    machine = config["machines"].get(machine_id)
    if not machine:
        raise HTTPException(
            status_code=404,
            detail=f"Machine '{machine_id}' not found in config.json"
        )

    defaults = config.get("defaults", {})

    # Build the full config for the Pico
    user_config = {
        "machine_id": machine_id,
        "machine_name": machine["name"],
        "power_watts": machine["power_watts"],
        "k_cool": machine["k_cool"],
        "kp": machine["pid"]["kp"],
        "ki": machine["pid"]["ki"],
        "kd": machine["pid"]["kd"],
        "pwm_window_s": machine.get("pwm_window_s", 30),
        "water_volume_liters": request.get("water_volume_liters", 1.0),
        "ambient_temp": request.get("ambient_temp", defaults.get("ambient_temp", 25.0)),
        "pasteurize_temp": request.get("pasteurize_temp", defaults.get("pasteurize_temp", 85.0)),
        "rapid_heat_duty": machine.get("rapid_heat_duty", defaults.get("rapid_heat_duty", 0.80)),
        "rapid_heat_cutoff_temp": machine.get("rapid_heat_cutoff_temp", defaults.get("rapid_heat_cutoff_temp", 70.0)),
        "pasteurize_tolerance": defaults.get("pasteurize_tolerance", 1.0),
        "hold_85_duration_s": request.get("hold_85_duration_min", 20) * 60,
        "ferment_temp": request.get("ferment_temp", defaults.get("ferment_temp", 42.0)),
        "ferment_tolerance": defaults.get("ferment_tolerance", 0.5),
        "ferment_duration_s": request.get("ferment_duration_hours", 8) * 3600,
        "safety_max_temp": defaults.get("safety_max_temp", 95.0),
        "sensor_pin": defaults.get("sensor_pin", 3),
        "relay_pin": defaults.get("relay_pin", 15),
    }

    pico.deploy_and_start(user_config)

    return {
        "status": "started",
        "machine": machine["name"],
        "data_dir": str(pico.run_dir),
    }


@app.post("/api/stop")
async def api_stop():
    """Emergency stop — terminate process and force relay off."""
    pico.stop()
    return {"status": "stopped"}


@app.post("/api/manual_temp")
async def api_manual_temp(request: dict):
    """Log a manually measured temperature to the CSV file."""
    temp = request.get("temperature")
    if temp is not None:
        with pico.lock:
            pico.manual_temp = float(temp)
    return {"status": "ok"}


@app.post("/api/sensor_location")
async def api_sensor_location(request: dict):
    """Set the sensor placement location (water_bath or inside_pot)."""
    location = request.get("location", "water_bath")
    if location not in ("water_bath", "inside_pot"):
        raise HTTPException(status_code=400, detail="Invalid location. Use 'water_bath' or 'inside_pot'.")
    with pico.lock:
        pico.sensor_location = location
    return {"status": "ok", "sensor_location": location}


@app.post("/api/toggle_csv")
async def api_toggle_csv():
    """Toggle CSV logging on/off (pause/resume)."""
    with pico.lock:
        pico.csv_paused = not pico.csv_paused
        paused = pico.csv_paused
    return {"status": "ok", "csv_paused": paused}


@app.post("/api/water_swap")
async def api_water_swap():
    """Log a water swap event to the CSV."""
    with pico.lock:
        pico.water_swap_logged = True
    return {"status": "ok"}


@app.get("/api/events")
async def api_events():
    """Server-Sent Events stream for real-time dashboard updates."""

    async def event_stream():
        last_data = None
        while True:
            data = pico.get_status()
            data_str = json.dumps(data)
            if data_str != last_data:
                yield f"data: {data_str}\n\n"
                last_data = data_str
            await asyncio.sleep(1)

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
        },
    )


@app.on_event("shutdown")
def shutdown_event():
    """Ensure Pico is stopped on server shutdown."""
    pico.stop()


# ============================================================
# Entry Point
# ============================================================
if __name__ == "__main__":
    import uvicorn

    print("╔══════════════════════════════════════════════════╗")
    print("║  Smart Yogurt Maker — Control Server            ║")
    print("║  Dashboard: http://0.0.0.0:8000                 ║")
    print("╚══════════════════════════════════════════════════╝")

    uvicorn.run(app, host="0.0.0.0", port=8000)
