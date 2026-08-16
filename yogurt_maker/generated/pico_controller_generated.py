"""Smart Yogurt Maker — Autonomous Pico W Controller Template

This file is a template. The server reads it, replaces the CONFIG section
between __CONFIG_START__ and __CONFIG_END__ with actual values, then deploys
the generated script to the Pico W via mpremote.

The controller implements:
  - Physics-informed feedforward + PID feedback control
  - Slow PWM (time-proportional) relay output via SSR
  - Multi-stage state machine: PASTEURIZE → HOLD_85 → COOL_DOWN → FERMENT → DONE
  - JSON status output via serial (for monitoring by Pi Zero 2W)
  - Safety watchdog and temperature limits
"""

import machine
import onewire
import ds18x20
import utime
import ujson

# __CONFIG_START__
CONFIG = {
    "machine_name": "800W Multi Cooker",
    "power_watts": 800,
    "water_mass_kg": 1.5,
    "k_cool": 0.839,
    "ambient_temp": 27,
    "kp": 0.001048,
    "ki": 3e-08,
    "kd": 0.0,
    "pwm_window_s": 30,
    "pasteurize_temp": 88,
    "pasteurize_tolerance": 1.0,
    "hold_85_duration_s": 720,
    "ferment_temp": 43,
    "ferment_tolerance": 0.5,
    "ferment_duration_s": 32400,
    "safety_max_temp": 95.0,
    "sensor_pin": 3,
    "relay_pin": 12
}
# __CONFIG_END__

# ============================================================
# Constants
# ============================================================
WATER_SPECIFIC_HEAT = 4186.0  # J/(kg·°C)

# ============================================================
# Hardware Setup
# ============================================================
relay = machine.Pin(CONFIG["relay_pin"], machine.Pin.OUT)
relay.off()
led = machine.Pin("LED", machine.Pin.OUT)
led.off()

dat = machine.Pin(CONFIG["sensor_pin"])
ds = ds18x20.DS18X20(onewire.OneWire(dat))


def scan_sensors():
    """Scan for DS18B20 sensors with retries."""
    for attempt in range(3):
        utime.sleep(2)
        roms = ds.scan()
        if roms:
            print(ujson.dumps({"msg": "sensor_found", "count": len(roms)}))
            return roms
        print(ujson.dumps({"msg": "sensor_retry", "attempt": attempt + 1}))
    print(ujson.dumps({"msg": "sensor_not_found"}))
    return []


# ============================================================
# PID Controller
# ============================================================
class PID:
    """Discrete PID controller with anti-windup clamping.

    Operates in 'duty-cycle' units: output is a correction to be
    added to the feedforward duty (0.0–1.0 range).
    """

    def __init__(self, kp, ki, kd):
        self.kp = kp
        self.ki = ki
        self.kd = kd
        self.integral = 0.0
        self.prev_error = 0.0
        self.first_call = True

    def compute(self, error, dt):
        """Compute PID correction.

        Args:
            error: setpoint − measured (°C). Positive = below target.
            dt: time since last call (seconds).

        Returns:
            Duty cycle correction (unbounded, caller must clamp).
        """
        if dt <= 0:
            return 0.0

        # Proportional
        p = self.kp * error

        # Integral with anti-windup clamp
        self.integral += error * dt
        max_i = 1.0 / max(self.ki, 1e-10)
        if self.integral > max_i:
            self.integral = max_i
        elif self.integral < -max_i:
            self.integral = -max_i
        i = self.ki * self.integral

        # Derivative (skip on first call to avoid spike)
        if self.first_call:
            d = 0.0
            self.first_call = False
        else:
            d = self.kd * (error - self.prev_error) / dt

        self.prev_error = error
        return p + i + d

    def reset(self):
        """Reset integral and derivative state."""
        self.integral = 0.0
        self.prev_error = 0.0
        self.first_call = True


# ============================================================
# Slow PWM — Time-Proportional Relay Control
# ============================================================
class SlowPWM:
    """Converts a 0.0–1.0 duty cycle to ON/OFF switching within a
    fixed time window.  Suitable for SSR control.

    Example: window=30s, duty=0.10 → ON 3s, OFF 27s.
    """

    def __init__(self, pin, window_ms):
        self.pin = pin
        self.window_ms = window_ms
        self.duty = 0.0
        self.window_start = utime.ticks_ms()

    def set_duty(self, duty):
        """Set duty cycle (clamped 0.0–1.0)."""
        if duty < 0.0:
            self.duty = 0.0
        elif duty > 1.0:
            self.duty = 1.0
        else:
            self.duty = duty

    def update(self, now_ms):
        """Call frequently. Toggles pin based on position in window."""
        elapsed = utime.ticks_diff(now_ms, self.window_start)

        # New window
        if elapsed >= self.window_ms:
            self.window_start = now_ms
            elapsed = 0

        on_time_ms = int(self.duty * self.window_ms)

        if on_time_ms <= 0:
            self.pin.off()
        elif elapsed < on_time_ms:
            self.pin.on()
        else:
            self.pin.off()

    def force_off(self):
        """Immediately turn off, regardless of duty."""
        self.duty = 0.0
        self.pin.off()


# ============================================================
# Yogurt Process State Machine
# ============================================================
class YogurtProcess:
    """Multi-stage state machine for yogurt production.

    Stages:
        PASTEURIZE → heat milk to 85°C (controlled ramp)
        HOLD_85    → hold at 85°C for configurable duration
        COOL_DOWN  → heater OFF, passive cooling to ~43°C
        FERMENT    → hold at 42°C ± 0.5°C for hours
        DONE       → heater OFF, process complete
    """

    def __init__(self, config):
        self.config = config
        self.stage = "PASTEURIZE"
        now = utime.ticks_ms()
        self.stage_start_ms = now
        self.process_start_ms = now

    def update(self, temp, now_ms):
        """Advance state machine based on temperature and time."""
        stage_elapsed_s = utime.ticks_diff(now_ms, self.stage_start_ms) / 1000.0

        if self.stage == "PASTEURIZE":
            if temp >= self.config["pasteurize_temp"]:
                self._transition("HOLD_85", now_ms)

        elif self.stage == "HOLD_85":
            if stage_elapsed_s >= self.config["hold_85_duration_s"]:
                self._transition("COOL_DOWN", now_ms)

        elif self.stage == "COOL_DOWN":
            # Transition when cooled to slightly above ferment target
            if temp <= self.config["ferment_temp"] + 1.0:
                self._transition("FERMENT", now_ms)

        elif self.stage == "FERMENT":
            if stage_elapsed_s >= self.config["ferment_duration_s"]:
                self._transition("DONE", now_ms)

        elif self.stage == "DONE":
            pass  # Terminal state

        # Safety override
        if temp > self.config["safety_max_temp"]:
            if self.stage not in ("COOL_DOWN", "DONE"):
                print(ujson.dumps({
                    "msg": "safety_triggered",
                    "temp": round(temp, 2),
                    "limit": self.config["safety_max_temp"]
                }))
                self._transition("DONE", now_ms)

    def _transition(self, new_stage, now_ms):
        """Transition to a new stage."""
        print(ujson.dumps({
            "msg": "stage_change",
            "from": self.stage,
            "to": new_stage
        }))
        self.stage = new_stage
        self.stage_start_ms = now_ms

    def get_target(self):
        """Return the temperature setpoint for the current stage, or None."""
        if self.stage == "PASTEURIZE":
            return self.config["pasteurize_temp"]
        elif self.stage == "HOLD_85":
            return self.config["pasteurize_temp"]
        elif self.stage == "FERMENT":
            return self.config["ferment_temp"]
        return None

    def needs_heating(self):
        """Return True if the current stage uses the heater."""
        return self.stage in ("PASTEURIZE", "HOLD_85", "FERMENT")

    def get_elapsed_s(self, now_ms):
        """Total process elapsed time in seconds."""
        return utime.ticks_diff(now_ms, self.process_start_ms) / 1000.0

    def get_stage_elapsed_s(self, now_ms):
        """Current stage elapsed time in seconds."""
        return utime.ticks_diff(now_ms, self.stage_start_ms) / 1000.0


# ============================================================
# Physics-Informed Feedforward
# ============================================================
def compute_feedforward(target, ambient, power_watts, k_cool):
    """Compute the steady-state duty cycle from the thermal energy balance.

    At steady state: P × duty = k_cool × (T_target − T_ambient)
    Therefore:       duty = k_cool × ΔT / P

    This tells the controller the baseline power needed to maintain
    the target temperature, so the PID only handles corrections.
    """
    if power_watts <= 0:
        return 0.0
    delta_t = target - ambient
    if delta_t <= 0:
        return 0.0
    duty = k_cool * delta_t / power_watts
    return min(duty, 1.0)


# ============================================================
# Main Control Loop
# ============================================================
def main():
    print(ujson.dumps({
        "msg": "boot",
        "machine": CONFIG["machine_name"],
        "water_kg": CONFIG["water_mass_kg"],
        "power_w": CONFIG["power_watts"],
    }))

    # --- Sensor init ---
    roms = scan_sensors()
    if not roms:
        relay.off()
        led.off()
        print(ujson.dumps({"msg": "fatal", "detail": "no_sensor"}))
        return

    # --- Controller init ---
    pid = PID(CONFIG["kp"], CONFIG["ki"], CONFIG["kd"])
    pwm = SlowPWM(relay, CONFIG["pwm_window_s"] * 1000)
    process = YogurtProcess(CONFIG)

    current_temp = 0.0
    duty = 0.0
    convert_started = False
    last_read_ms = utime.ticks_ms()
    last_pid_ms = last_read_ms
    last_good_temp_ms = last_read_ms  # Watchdog

    print(ujson.dumps({"msg": "start", "stage": process.stage}))

    try:
        while True:
            now = utime.ticks_ms()
            new_reading = False

            # --- 1. Temperature reading (non-blocking) ---
            if not convert_started:
                if utime.ticks_diff(now, last_read_ms) > 2000:
                    try:
                        ds.convert_temp()
                        convert_started = True
                        last_read_ms = now
                    except Exception as e:
                        print(ujson.dumps({"msg": "err", "detail": str(e)}))
            else:
                if utime.ticks_diff(now, last_read_ms) > 750:
                    try:
                        current_temp = ds.read_temp(roms[0])
                        convert_started = False
                        new_reading = True
                        last_good_temp_ms = now
                    except Exception as e:
                        print(ujson.dumps({"msg": "err", "detail": str(e)}))
                        convert_started = False

            # --- 2. Watchdog: no reading for 30s → emergency off ---
            if utime.ticks_diff(now, last_good_temp_ms) > 30000:
                duty = 0.0
                pwm.force_off()
                led.off()
                if utime.ticks_diff(now, last_good_temp_ms) % 10000 < 50:
                    print(ujson.dumps({"msg": "watchdog", "no_read_s": 30}))

            # --- 3. Control logic (runs on each new temperature reading) ---
            if new_reading:
                # Update state machine
                process.update(current_temp, now)

                target = process.get_target()

                if target is not None and process.needs_heating():
                    # Feedforward: steady-state duty from physics
                    duty_ff = compute_feedforward(
                        target,
                        CONFIG["ambient_temp"],
                        CONFIG["power_watts"],
                        CONFIG["k_cool"]
                    )

                    # PID: feedback correction
                    error = target - current_temp
                    dt = utime.ticks_diff(now, last_pid_ms) / 1000.0
                    last_pid_ms = now
                    duty_pid = pid.compute(error, dt)

                    # Combined duty
                    duty = duty_ff + duty_pid

                    # Clamp to [0, 1]
                    if duty < 0.0:
                        duty = 0.0
                    elif duty > 1.0:
                        duty = 1.0

                else:
                    # No heating needed (COOL_DOWN or DONE)
                    duty = 0.0
                    pid.reset()

                # Safety hard limit
                if current_temp > CONFIG["safety_max_temp"]:
                    duty = 0.0

                # Apply duty
                pwm.set_duty(duty)

                # LED mirrors heating intent
                led.value(1 if duty > 0.01 else 0)

                # --- 4. Serial status output (JSON) ---
                status = {
                    "t": round(current_temp, 2),
                    "sp": round(target, 1) if target else 0,
                    "duty": round(duty, 4),
                    "relay": relay.value(),
                    "stage": process.stage,
                    "elapsed": int(process.get_elapsed_s(now)),
                    "stage_elapsed": int(process.get_stage_elapsed_s(now)),
                }
                print(ujson.dumps(status))

            # --- 5. PWM update (runs every iteration) ---
            pwm.update(now)

            # Small sleep to prevent tight-loop CPU burn
            utime.sleep_ms(10)

    except KeyboardInterrupt:
        print(ujson.dumps({"msg": "interrupted"}))
    finally:
        # Always ensure safe shutdown
        relay.off()
        led.off()
        pwm.force_off()
        print(ujson.dumps({"msg": "shutdown", "relay": "off"}))


# Entry point
main()
