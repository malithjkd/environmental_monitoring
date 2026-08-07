"""Smart Yogurt Maker — Calibration Data Analyzer

Post-processes calibration CSV data to compute:
  1. Cooling coefficient (k_cool) from the COOLING phase
  2. Effective heating power from the HEATING phase
  3. Suggested PID constants based on the thermal model
  4. Generates diagnostic plots

Usage:
    python calibration_analyzer.py data/calibration/<run_dir> --ambient 28

Outputs (saved to the same run directory):
  - thermal_parameters.json  (computed k_cool, power, PID constants)
  - calibration_plot.png     (heating + cooling curves with fits)
"""

import argparse
import csv
import json
import os
import sys

import matplotlib.pyplot as plt
import numpy as np


WATER_SPECIFIC_HEAT = 4186.0  # J/(kg·°C)


def load_calibration_data(csv_path):
    """Load calibration CSV into structured arrays."""
    elapsed = []
    temps = []
    phases = []

    with open(csv_path, "r") as f:
        reader = csv.DictReader(f)
        for row in reader:
            try:
                elapsed.append(float(row["elapsed_s"]))
                temps.append(float(row["temperature_c"]))
                phases.append(row["phase"])
            except (ValueError, KeyError):
                continue

    return np.array(elapsed), np.array(temps), phases


def compute_cooling_coefficient(elapsed, temps, phases, water_mass_kg, ambient_temp):
    """Estimate k_cool from the cooling phase using Newton's law of cooling.

    Q_out = k_cool × (T - T_ambient)
    M × C × dT/dt = -k_cool × (T - T_ambient)

    Solution: T(t) = T_ambient + (T0 - T_ambient) × exp(-k_cool × t / (M × C))

    We fit the exponential decay to find k_cool.

    IMPORTANT: After the relay turns off, heat stored in the cooker's heating
    element continues transferring into the water (thermal soak). The
    temperature may RISE for several minutes before true cooling begins.
    We detect the peak temperature and start the fit from there.
    """
    # Extract cooling phase data
    cooling_mask = [p == "COOLING" for p in phases]
    cooling_elapsed = elapsed[cooling_mask]
    cooling_temps = temps[cooling_mask]

    if len(cooling_elapsed) < 10:
        print("Warning: Not enough cooling data points for reliable fit")
        return 5.0, cooling_elapsed, cooling_temps, 0  # Default

    # Shift time to start at 0 for cooling phase
    t_raw = cooling_elapsed - cooling_elapsed[0]
    T_raw = cooling_temps

    # --- Detect and skip thermal soak period ---
    # Find the index of peak temperature (where actual cooling starts)
    peak_idx = int(np.argmax(T_raw))
    peak_temp = T_raw[peak_idx]
    soak_duration_s = t_raw[peak_idx]

    print(f"  Thermal soak detected: temp rose from {T_raw[0]:.1f}°C to "
          f"{peak_temp:.1f}°C (+{peak_temp - T_raw[0]:.1f}°C) over "
          f"{soak_duration_s:.0f}s ({soak_duration_s/60:.1f} min)")
    print(f"  Fitting from peak ({peak_temp:.1f}°C) onwards...")

    # Use data from peak onwards for the fit
    t = t_raw[peak_idx:] - t_raw[peak_idx]  # Reset time to 0 at peak
    T = T_raw[peak_idx:]

    # Newton's law: T(t) = T_amb + (T0 - T_amb) × exp(-t/τ)
    # where τ = M × C / k_cool
    T0 = T[0]
    delta_T = T - ambient_temp

    # Avoid log of non-positive values
    valid = delta_T > 0.5  # At least 0.5°C above ambient
    if np.sum(valid) < 5:
        print("Warning: Temperature too close to ambient for reliable fit")
        return 5.0, t, T, soak_duration_s

    t_valid = t[valid]
    delta_T_valid = delta_T[valid]

    # Linear regression on ln(delta_T) vs t
    # ln(T - T_amb) = ln(T0 - T_amb) - t/τ
    ln_delta = np.log(delta_T_valid)
    coeffs = np.polyfit(t_valid, ln_delta, 1)
    slope = coeffs[0]  # -1/τ

    tau = -1.0 / slope  # Time constant (seconds)
    k_cool = water_mass_kg * WATER_SPECIFIC_HEAT / tau  # W/°C

    print(f"  Thermal time constant (τ): {tau:.1f} s ({tau/60:.1f} min)")
    print(f"  Cooling coefficient (k_cool): {k_cool:.2f} W/°C")
    print(f"  Ambient temp used: {ambient_temp}°C")

    return k_cool, t, T, soak_duration_s


def compute_effective_power(elapsed, temps, phases, water_mass_kg, k_cool, ambient_temp):
    """Estimate effective heating power from the heating phase.

    M × C × dT/dt = P_eff - k_cool × (T - T_ambient)
    P_eff = M × C × dT/dt + k_cool × (T - T_ambient)
    """
    heating_mask = [p == "HEATING" for p in phases]
    heating_elapsed = elapsed[heating_mask]
    heating_temps = temps[heating_mask]

    if len(heating_elapsed) < 10:
        print("Warning: Not enough heating data points")
        return 0.0, heating_elapsed, heating_temps

    # Compute dT/dt using central differences
    dt = np.diff(heating_elapsed)
    dT = np.diff(heating_temps)

    # Avoid division by zero
    valid = dt > 0
    dt = dt[valid]
    dT = dT[valid]
    dT_dt = dT / dt

    # Average temperature for each interval
    T_avg = (heating_temps[:-1][valid] + heating_temps[1:][valid]) / 2

    # P_eff for each interval
    P_eff = water_mass_kg * WATER_SPECIFIC_HEAT * dT_dt + k_cool * (T_avg - ambient_temp)

    # Use median to be robust to outliers
    P_effective = float(np.median(P_eff))
    P_std = float(np.std(P_eff))

    print(f"  Effective power: {P_effective:.0f} W (±{P_std:.0f} W)")

    t = heating_elapsed - heating_elapsed[0]
    return P_effective, t, heating_temps


def compute_pid_constants(k_cool, water_mass_kg, power_watts):
    """Compute PID constants for the feedforward + PID controller.

    The feedforward handles steady-state, so PID only handles corrections.

    Process model (linearized around setpoint):
        K_process = P / k_cool  (°C per unit duty change at steady state)
        τ = M × C / k_cool     (thermal time constant)

    PID tuning (conservative, since feedforward does the heavy lifting):
        Kp = k_cool / P  (inverse of process gain)
        Ki = Kp / (4 × τ)
        Kd = 0  (start without derivative)
    """
    tau = water_mass_kg * WATER_SPECIFIC_HEAT / k_cool
    K_process = power_watts / k_cool

    kp = k_cool / power_watts
    ki = kp / (4 * tau)
    kd = 0.0

    print(f"  Process gain (K): {K_process:.1f} °C/duty")
    print(f"  Time constant (τ): {tau:.0f} s ({tau/60:.1f} min)")
    print(f"  Suggested PID: Kp={kp:.6f}, Ki={ki:.8f}, Kd={kd:.4f}")

    return {"kp": round(kp, 6), "ki": round(ki, 8), "kd": kd}


def generate_plots(
    run_dir,
    elapsed, temps, phases,
    cooling_t, cooling_T,
    heating_t, heating_T,
    k_cool, water_mass_kg, ambient_temp,
    metadata,
):
    """Generate diagnostic calibration plots."""
    fig, axes = plt.subplots(2, 1, figsize=(12, 10), sharex=False)

    # --- Plot 1: Full calibration curve ---
    ax1 = axes[0]
    heating_mask = [p == "HEATING" for p in phases]
    cooling_mask = [p == "COOLING" for p in phases]

    ax1.plot(
        elapsed[heating_mask] / 60, temps[heating_mask],
        color="#ff5722", linewidth=2, label="Heating (relay ON)"
    )
    ax1.plot(
        elapsed[cooling_mask] / 60, temps[cooling_mask],
        color="#2196f3", linewidth=2, label="Cooling (relay OFF)"
    )
    ax1.axhline(y=ambient_temp, color="gray", linestyle="--", alpha=0.5, label=f"Ambient ({ambient_temp}°C)")
    ax1.set_xlabel("Time (minutes)")
    ax1.set_ylabel("Temperature (°C)")
    ax1.set_title(
        f"Calibration: {metadata.get('machine_name', '?')} — "
        f"{metadata.get('water_volume_liters', '?')}L water"
    )
    ax1.legend()
    ax1.grid(True, alpha=0.3)

    # --- Plot 2: Cooling curve with exponential fit ---
    ax2 = axes[1]
    if len(cooling_t) > 5:
        ax2.plot(cooling_t / 60, cooling_T, "o", color="#2196f3", markersize=2, label="Measured")

        # Exponential fit overlay
        tau = water_mass_kg * WATER_SPECIFIC_HEAT / k_cool
        T0 = cooling_T[0]
        t_fit = np.linspace(0, cooling_t[-1], 200)
        T_fit = ambient_temp + (T0 - ambient_temp) * np.exp(-t_fit / tau)
        ax2.plot(t_fit / 60, T_fit, "-", color="#ff9800", linewidth=2,
                 label=f"Fit: τ={tau:.0f}s, k_cool={k_cool:.2f} W/°C")

    ax2.set_xlabel("Cooling Time (minutes)")
    ax2.set_ylabel("Temperature (°C)")
    ax2.set_title("Cooling Phase — Exponential Decay Fit")
    ax2.legend()
    ax2.grid(True, alpha=0.3)

    plt.tight_layout()
    plot_path = os.path.join(run_dir, "calibration_plot.png")
    plt.savefig(plot_path, dpi=200)
    plt.close()
    print(f"  Plot saved: {plot_path}")


def main():
    parser = argparse.ArgumentParser(
        description="Analyze calibration data and compute thermal parameters."
    )
    parser.add_argument(
        "run_dir",
        help="Path to calibration run directory (e.g., data/calibration/800w_multi_cooker_...)"
    )
    parser.add_argument(
        "--ambient", type=float, default=None,
        help="Actual room ambient temperature in °C (default: from metadata or 28°C)"
    )
    parser.add_argument(
        "--notes", type=str, default="",
        help="Optional notes about test conditions (e.g., 'ceiling fan setting 1')"
    )
    args = parser.parse_args()

    run_dir = args.run_dir

    # Load metadata
    metadata_path = os.path.join(run_dir, "metadata.json")
    if not os.path.exists(metadata_path):
        print(f"Error: {metadata_path} not found")
        sys.exit(1)

    with open(metadata_path) as f:
        metadata = json.load(f)

    water_mass_kg = metadata.get(
        "total_water_mass_kg", 
        metadata.get("total_water_volume_liters", metadata.get("water_mass_kg", metadata.get("water_volume_liters", 1.0)))
    )
    power_watts = metadata.get("power_watts", 800)

    # Ambient temp: CLI > metadata > default
    if args.ambient is not None:
        ambient_temp = args.ambient
    elif "ambient_temp" in metadata:
        ambient_temp = metadata["ambient_temp"]
    else:
        ambient_temp = 28.0  # Sensible default for tropical/warm rooms

    print(f"╔══════════════════════════════════════════════════╗")
    print(f"║  Calibration Analysis                           ║")
    print(f"╠══════════════════════════════════════════════════╣")
    print(f"║  Machine: {metadata.get('machine_name', '?'):<39}║")
    print(f"║  Power:   {power_watts}W{' ' * (37 - len(str(power_watts)))}║")
    print(f"║  Water:   {water_mass_kg}kg{' ' * (36 - len(str(water_mass_kg)))}║")
    print(f"║  Ambient: {ambient_temp}°C{' ' * (35 - len(str(ambient_temp)))}║")
    if args.notes:
        # Truncate notes to fit the box
        note_display = args.notes[:37]
        print(f"║  Notes:   {note_display:<39}║")
    print(f"╚══════════════════════════════════════════════════╝")

    # Load CSV data
    csv_path = os.path.join(run_dir, "calibration_data.csv")
    if not os.path.exists(csv_path):
        print(f"Error: {csv_path} not found")
        sys.exit(1)

    elapsed, temps, phases = load_calibration_data(csv_path)
    print(f"\nLoaded {len(elapsed)} data points.")

    # Compute cooling coefficient
    print("\n--- Cooling Analysis ---")
    k_cool, cooling_t, cooling_T, soak_duration_s = compute_cooling_coefficient(
        elapsed, temps, phases, water_mass_kg, ambient_temp
    )

    # Compute effective power
    print("\n--- Heating Analysis ---")
    P_eff, heating_t, heating_T = compute_effective_power(
        elapsed, temps, phases, water_mass_kg, k_cool, ambient_temp
    )

    # Compute PID constants
    print("\n--- PID Tuning ---")
    pid_constants = compute_pid_constants(k_cool, water_mass_kg, power_watts)

    # Save results
    results = {
        "k_cool": round(k_cool, 3),
        "effective_power_watts": round(P_eff, 1),
        "rated_power_watts": power_watts,
        "water_mass_kg": water_mass_kg,
        "ambient_temp": ambient_temp,
        "thermal_soak_duration_s": round(soak_duration_s, 1),
        "thermal_time_constant_s": round(water_mass_kg * WATER_SPECIFIC_HEAT / k_cool, 1),
        "pid": pid_constants,
        "notes": args.notes if args.notes else None,
    }

    results_path = os.path.join(run_dir, "thermal_parameters.json")
    with open(results_path, "w") as f:
        json.dump(results, f, indent=4)
    print(f"\n✓ Thermal parameters saved: {results_path}")

    # Generate plots
    print("\nGenerating plots...")
    generate_plots(
        run_dir, elapsed, temps, phases,
        cooling_t, cooling_T, heating_t, heating_T,
        k_cool, water_mass_kg, ambient_temp, metadata,
    )

    # Print summary
    print("\n" + "=" * 50)
    print("SUMMARY — Update config.json with these values:")
    print("=" * 50)
    print(f'  "k_cool": {results["k_cool"]},')
    print(f'  "pid": {json.dumps(pid_constants)}')
    print()
    print(f"Feedforward duty at 42°C (ambient {ambient_temp}°C):")
    duty_ff = k_cool * (42 - ambient_temp) / power_watts
    print(f"  {duty_ff:.4f} ({duty_ff*100:.1f}% → ON {duty_ff*30:.1f}s per 30s window)")
    print()
    print(f"Feedforward duty at 85°C (ambient {ambient_temp}°C):")
    duty_ff_85 = k_cool * (85 - ambient_temp) / power_watts
    print(f"  {duty_ff_85:.4f} ({duty_ff_85*100:.1f}% → ON {duty_ff_85*30:.1f}s per 30s window)")
    print()
    if soak_duration_s > 10:
        print(f"⚠  Thermal soak: {soak_duration_s:.0f}s ({soak_duration_s/60:.1f} min) — "
              f"the cooker's element retains significant heat after relay OFF.")
        print(f"   The controller should anticipate this and cut power EARLY.")


if __name__ == "__main__":
    main()
