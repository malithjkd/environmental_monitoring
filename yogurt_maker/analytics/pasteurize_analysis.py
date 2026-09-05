"""Pasteurize Phase Performance Analysis — Multi-Run Comparison

Analyzes past yogurt maker runs to diagnose why the PASTEURIZE phase
takes 80–108 minutes, and simulates the effect of higher PID ki values
to find the optimal integral gain for faster heating.

Computes:
  - Rolling 2-min integral error (∫(setpoint−T)dt over last 120s)
  - Cumulative integral error
  - Actual vs physics-optimal duty cycles
  - Simulated duty with enhanced ki values
  - Theoretical optimal heating time
  - Recommended ki value for target ramp time

Generates an interactive HTML report with multi-run overlay charts.

Usage:
    python analytics/pasteurize_analysis.py

    # Or specify runs explicitly:
    python analytics/pasteurize_analysis.py data/2026_08_16_12_07_13 data/2026_08_22_07_51_34
"""

import csv
import json
import sys
from pathlib import Path
from datetime import datetime
from collections import deque

WATER_SPECIFIC_HEAT = 4186.0  # J/(kg·°C)

# Default runs to analyze if none specified
DEFAULT_RUNS = [
    "data/2026_08_16_12_07_13",
    "data/2026_08_22_07_51_34",
    "data/2026_08_23_11_06_51",
    "data/2026_08_19_09_52_36",
]

# Base directory (relative to this script's location)
BASE_DIR = Path(__file__).resolve().parent.parent


def load_run(run_path):
    """Load CSV data and metadata for a single run.

    Returns:
        dict with keys: 'path', 'name', 'metadata', 'data', 'pasteurize_data'
        or None if files are missing.
    """
    run_path = Path(run_path)
    csv_file = run_path / "temperature_log.csv"
    meta_file = run_path / "metadata.json"

    if not csv_file.exists():
        print(f"  ⚠ Skipping {run_path.name}: no temperature_log.csv")
        return None

    metadata = {}
    if meta_file.exists():
        with open(meta_file) as f:
            metadata = json.load(f)

    data = []
    with open(csv_file) as f:
        for row in csv.DictReader(f):
            data.append(row)

    if not data:
        print(f"  ⚠ Skipping {run_path.name}: empty CSV")
        return None

    # Extract PASTEURIZE phase
    pasteurize_data = [r for r in data if r["Stage"] == "PASTEURIZE"]

    return {
        "path": run_path,
        "name": run_path.name,
        "metadata": metadata,
        "data": data,
        "pasteurize_data": pasteurize_data,
    }


def compute_pasteurize_metrics(run):
    """Compute detailed PASTEURIZE phase metrics for a single run.

    Returns a dict of analysis results.
    """
    pdata = run["pasteurize_data"]
    if not pdata:
        return None

    meta = run["metadata"]
    power_w = meta.get("power_watts", 800)
    k_cool = meta.get("k_cool", 0.839)
    ambient = 28  # Typical ambient (not stored in metadata)
    kp = meta.get("pid", {}).get("kp", 0.001048)
    ki = meta.get("pid", {}).get("ki", 3e-08)
    kd = meta.get("pid", {}).get("kd", 0.0)

    setpoint = float(pdata[0]["Setpoint_C"])
    dt_sample = 2  # 2-second sample interval

    # Parse timestamps
    t_start = datetime.strptime(pdata[0]["Timestamp"], "%Y-%m-%d %H:%M:%S")
    t_end = datetime.strptime(pdata[-1]["Timestamp"], "%Y-%m-%d %H:%M:%S")
    duration_s = (t_end - t_start).total_seconds()

    temps = [float(r["Temperature_C"]) for r in pdata]
    duties = [float(r["Duty_Cycle"]) for r in pdata]

    # --- Rolling 2-min integral error ---
    window_samples = 60  # 120s / 2s = 60 samples
    rolling_integral_errors = []
    error_buffer = deque(maxlen=window_samples)

    for i, t in enumerate(temps):
        error = setpoint - t
        error_buffer.append(error)
        # Sum of errors in window * dt
        rolling_ie = sum(error_buffer) * dt_sample
        rolling_integral_errors.append(rolling_ie)

    # --- Cumulative integral error ---
    cumulative_integral_errors = []
    cum_ie = 0.0
    for t in temps:
        error = setpoint - t
        cum_ie += error * dt_sample
        cumulative_integral_errors.append(cum_ie)

    # --- Feedforward duty at each point ---
    ff_duty = k_cool * (setpoint - ambient) / power_w

    # --- Physics-optimal duty: what duty would produce ideal heating ---
    water_mass = meta.get("water_volume_liters", 1.5)
    target_rate_c_per_min = 1.0  # 1 deg C/min as a baseline
    p_ramp = water_mass * WATER_SPECIFIC_HEAT * (target_rate_c_per_min / 60)
    mid_temp = (temps[0] + setpoint) / 2
    p_loss = k_cool * (mid_temp - ambient)
    optimal_duty = (p_ramp + p_loss) / power_w

    # --- Simulated duty with enhanced ki values ---
    sim_ki_values = [1e-06, 5e-06, 1e-05, 5e-05, 1e-04, 5e-04]
    simulated_duties = {}

    for sim_ki in sim_ki_values:
        sim_integral = 0.0
        sim_duties = []
        for i, t in enumerate(temps):
            error = setpoint - t
            sim_integral += error * dt_sample

            # Anti-windup clamp (same as PID class)
            max_i = 1.0 / max(sim_ki, 1e-10)
            if sim_integral > max_i:
                sim_integral = max_i
            elif sim_integral < -max_i:
                sim_integral = -max_i

            p_term = kp * error
            i_term = sim_ki * sim_integral
            duty = ff_duty + p_term + i_term

            # Clamp to [0, 1]
            duty = max(0.0, min(1.0, duty))
            sim_duties.append(duty)

        label = f"ki={sim_ki:.0e}"
        simulated_duties[label] = sim_duties

    # --- Theoretical optimal time at higher duty ---
    delta_t = setpoint - temps[0]
    scenarios = {}
    for scenario_duty in [0.20, 0.30, 0.50, 0.80]:
        p_eff = scenario_duty * power_w - k_cool * (mid_temp - ambient)
        if p_eff > 0:
            t_opt = water_mass * WATER_SPECIFIC_HEAT * delta_t / p_eff
            scenarios[f"{int(scenario_duty*100)}% duty"] = {
                "time_min": round(t_opt / 60, 1),
                "effective_power_w": round(p_eff, 0),
            }

    # --- Elapsed time axis (seconds from start) ---
    elapsed_s = [i * dt_sample for i in range(len(temps))]

    return {
        "run_name": run["name"],
        "setpoint": setpoint,
        "start_temp": temps[0],
        "end_temp": temps[-1],
        "duration_s": duration_s,
        "duration_min": round(duration_s / 60, 1),
        "heating_rate_c_per_min": round(delta_t / (duration_s / 60), 3) if duration_s > 0 else 0,
        "avg_duty_pct": round(sum(duties) / len(duties) * 100, 2),
        "max_duty_pct": round(max(duties) * 100, 2),
        "min_duty_pct": round(min(duties) * 100, 2),
        "ff_duty_pct": round(ff_duty * 100, 2),
        "effective_power_w": round(sum(duties) / len(duties) * power_w, 0),
        "ki_actual": ki,
        "total_integral_error": round(cumulative_integral_errors[-1], 1),
        "max_rolling_ie_2min": round(max(rolling_integral_errors), 1),
        "optimal_duty_1c_per_min": round(optimal_duty * 100, 2),
        "power_watts": power_w,
        "k_cool": k_cool,
        "water_mass_kg": water_mass,
        # Time series for charts
        "_elapsed_s": elapsed_s,
        "_temps": temps,
        "_duties": duties,
        "_rolling_ie": rolling_integral_errors,
        "_cumulative_ie": cumulative_integral_errors,
        "_simulated_duties": simulated_duties,
        "_scenarios": scenarios,
    }


def generate_html_report(all_metrics, output_path):
    """Generate an interactive HTML report comparing all runs."""

    # Colors for each run
    colors = [
        {"line": "#ff6b6b", "bg": "rgba(255,107,107,0.15)"},
        {"line": "#4ecdc4", "bg": "rgba(78,205,196,0.15)"},
        {"line": "#ffd93d", "bg": "rgba(255,217,61,0.15)"},
        {"line": "#a78bfa", "bg": "rgba(167,139,250,0.15)"},
    ]

    # Simulated ki colors
    sim_colors = ["#ff9ff3", "#54a0ff", "#5f27cd", "#01a3a4", "#f368e0", "#ee5a24"]

    # --- Summary table ---
    summary_rows = ""
    for m in all_metrics:
        summary_rows += f"""<tr>
            <td>{m['run_name']}</td>
            <td>{m['start_temp']:.1f} → {m['end_temp']:.1f}°C</td>
            <td class="highlight">{m['duration_min']:.0f} min</td>
            <td>{m['heating_rate_c_per_min']:.3f} °C/min</td>
            <td class="warn">{m['avg_duty_pct']:.1f}%</td>
            <td>{m['effective_power_w']:.0f}W / {m['power_watts']}W</td>
            <td>{m['total_integral_error']:.0f} °C·s</td>
            <td>{m['max_rolling_ie_2min']:.0f} °C·s</td>
        </tr>"""

    # --- Scenarios table ---
    scenario_rows = ""
    if all_metrics:
        ref = all_metrics[0]
        for duty_label, info in ref["_scenarios"].items():
            speedup = ref["duration_min"] / info["time_min"] if info["time_min"] > 0 else 0
            scenario_rows += f"""<tr>
                <td>{duty_label}</td>
                <td>{info['effective_power_w']:.0f}W</td>
                <td>{info['time_min']:.1f} min</td>
                <td>{speedup:.1f}×</td>
            </tr>"""

    # --- Chart datasets: Temperature overlay ---
    temp_datasets = []
    for i, m in enumerate(all_metrics):
        c = colors[i % len(colors)]
        step = max(1, len(m["_elapsed_s"]) // 500)
        elapsed_min = [round(s / 60, 2) for s in m["_elapsed_s"][::step]]
        temps_ds = [round(t, 2) for t in m["_temps"][::step]]
        temp_datasets.append({
            "label": m["run_name"],
            "data": [{"x": e, "y": t} for e, t in zip(elapsed_min, temps_ds)],
            "borderColor": c["line"],
            "backgroundColor": c["bg"],
            "borderWidth": 2,
            "pointRadius": 0,
            "tension": 0.3,
            "fill": False,
        })

    # Add setpoint line
    if all_metrics:
        max_time = max(m["duration_min"] for m in all_metrics)
        temp_datasets.append({
            "label": f"Setpoint ({all_metrics[0]['setpoint']}°C)",
            "data": [{"x": 0, "y": all_metrics[0]["setpoint"]}, {"x": max_time, "y": all_metrics[0]["setpoint"]}],
            "borderColor": "#ffffff",
            "borderWidth": 1,
            "borderDash": [5, 5],
            "pointRadius": 0,
            "fill": False,
        })

    # --- Chart datasets: Duty cycle overlay ---
    duty_datasets = []
    for i, m in enumerate(all_metrics):
        c = colors[i % len(colors)]
        step = max(1, len(m["_elapsed_s"]) // 500)
        elapsed_min = [round(s / 60, 2) for s in m["_elapsed_s"][::step]]
        duties_ds = [round(d * 100, 2) for d in m["_duties"][::step]]
        duty_datasets.append({
            "label": m["run_name"],
            "data": [{"x": e, "y": d} for e, d in zip(elapsed_min, duties_ds)],
            "borderColor": c["line"],
            "borderWidth": 1.5,
            "pointRadius": 0,
            "tension": 0.3,
            "fill": False,
        })

    # Add optimal line
    if all_metrics:
        opt = all_metrics[0]["optimal_duty_1c_per_min"]
        duty_datasets.append({
            "label": f"Optimal for 1°C/min ({opt:.1f}%)",
            "data": [{"x": 0, "y": opt}, {"x": max_time, "y": opt}],
            "borderColor": "#00ff88",
            "borderWidth": 2,
            "borderDash": [8, 4],
            "pointRadius": 0,
            "fill": False,
        })

    # --- Chart datasets: Rolling integral error ---
    rie_datasets = []
    for i, m in enumerate(all_metrics):
        c = colors[i % len(colors)]
        step = max(1, len(m["_elapsed_s"]) // 500)
        elapsed_min = [round(s / 60, 2) for s in m["_elapsed_s"][::step]]
        rie_ds = [round(v, 1) for v in m["_rolling_ie"][::step]]
        rie_datasets.append({
            "label": m["run_name"],
            "data": [{"x": e, "y": r} for e, r in zip(elapsed_min, rie_ds)],
            "borderColor": c["line"],
            "backgroundColor": c["bg"],
            "borderWidth": 2,
            "pointRadius": 0,
            "tension": 0.3,
            "fill": True,
        })

    # --- Chart datasets: Cumulative integral error ---
    cie_datasets = []
    for i, m in enumerate(all_metrics):
        c = colors[i % len(colors)]
        step = max(1, len(m["_elapsed_s"]) // 500)
        elapsed_min = [round(s / 60, 2) for s in m["_elapsed_s"][::step]]
        cie_ds = [round(v, 0) for v in m["_cumulative_ie"][::step]]
        cie_datasets.append({
            "label": m["run_name"],
            "data": [{"x": e, "y": c_val} for e, c_val in zip(elapsed_min, cie_ds)],
            "borderColor": c["line"],
            "borderWidth": 2,
            "pointRadius": 0,
            "tension": 0.3,
            "fill": False,
        })

    # --- Chart datasets: Simulated ki comparison (use first run) ---
    sim_datasets = []
    if all_metrics:
        ref = all_metrics[0]
        step = max(1, len(ref["_elapsed_s"]) // 500)
        elapsed_min = [round(s / 60, 2) for s in ref["_elapsed_s"][::step]]

        # Add actual duty
        actual_ds = [round(d * 100, 2) for d in ref["_duties"][::step]]
        sim_datasets.append({
            "label": f"Actual (ki={ref['ki_actual']:.0e})",
            "data": [{"x": e, "y": d} for e, d in zip(elapsed_min, actual_ds)],
            "borderColor": "#ff6b6b",
            "borderWidth": 2,
            "pointRadius": 0,
            "tension": 0.3,
            "fill": False,
        })

        for j, (ki_label, sim_duty_list) in enumerate(ref["_simulated_duties"].items()):
            sim_ds = [round(d * 100, 2) for d in sim_duty_list[::step]]
            sim_datasets.append({
                "label": ki_label,
                "data": [{"x": e, "y": d} for e, d in zip(elapsed_min, sim_ds)],
                "borderColor": sim_colors[j % len(sim_colors)],
                "borderWidth": 1.5,
                "pointRadius": 0,
                "tension": 0.3,
                "fill": False,
            })

    # --- Ki recommendation table ---
    ki_rec_rows = ""
    if all_metrics:
        ref = all_metrics[0]
        for ki_label, sim_duty_list in ref["_simulated_duties"].items():
            avg_sim = sum(sim_duty_list) / len(sim_duty_list) * 100
            max_sim = max(sim_duty_list) * 100
            eff_power = sum(sim_duty_list) / len(sim_duty_list) * ref["power_watts"]

            delta_t_val = ref["setpoint"] - ref["start_temp"]
            mid_temp_val = (ref["start_temp"] + ref["setpoint"]) / 2
            p_loss = ref["k_cool"] * (mid_temp_val - 28)
            p_eff = eff_power - p_loss
            est_time = ref["water_mass_kg"] * WATER_SPECIFIC_HEAT * delta_t_val / p_eff / 60 if p_eff > 0 else float("inf")
            speedup = ref["duration_min"] / est_time if est_time > 0 and est_time != float("inf") else 0

            ki_rec_rows += f"""<tr>
                <td>{ki_label}</td>
                <td>{avg_sim:.1f}%</td>
                <td>{max_sim:.1f}%</td>
                <td>{eff_power:.0f}W</td>
                <td>{est_time:.0f} min</td>
                <td>{speedup:.1f}×</td>
            </tr>"""

    avg_dur = sum(m["duration_min"] for m in all_metrics) / len(all_metrics)
    avg_duty = sum(m["avg_duty_pct"] for m in all_metrics) / len(all_metrics)
    avg_power = sum(m["effective_power_w"] for m in all_metrics) / len(all_metrics)

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Pasteurize Phase Analysis</title>
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;600;700&display=swap" rel="stylesheet">
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{
            font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
            background: #0a0a1a;
            color: #e0e0f0;
            padding: 24px;
            line-height: 1.6;
        }}
        .container {{ max-width: 1400px; margin: 0 auto; }}
        h1 {{
            text-align: center;
            font-size: 2rem;
            font-weight: 700;
            margin-bottom: 8px;
            background: linear-gradient(135deg, #ff6b6b, #ffd93d, #4ecdc4);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
        }}
        .subtitle {{
            text-align: center;
            color: #666;
            margin-bottom: 32px;
            font-size: 0.95rem;
        }}
        .card {{
            background: linear-gradient(135deg, rgba(30,30,50,0.9), rgba(20,20,40,0.95));
            border: 1px solid rgba(255,255,255,0.08);
            border-radius: 16px;
            padding: 24px;
            margin-bottom: 24px;
            backdrop-filter: blur(10px);
        }}
        .card h3 {{
            color: #a8b4ff;
            margin-bottom: 16px;
            font-size: 1.15rem;
            font-weight: 600;
        }}
        .grid-2 {{
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 24px;
        }}
        @media (max-width: 900px) {{
            .grid-2 {{ grid-template-columns: 1fr; }}
        }}
        .chart-container {{
            height: 380px;
            position: relative;
        }}
        table {{
            width: 100%;
            border-collapse: collapse;
            margin-top: 12px;
        }}
        th, td {{
            padding: 10px 14px;
            text-align: left;
            border-bottom: 1px solid rgba(255,255,255,0.06);
            font-size: 0.88rem;
        }}
        th {{
            color: #a8b4ff;
            font-size: 0.78rem;
            text-transform: uppercase;
            letter-spacing: 0.5px;
            font-weight: 600;
        }}
        td {{ color: #ccc; }}
        td.highlight {{
            color: #ff6b6b;
            font-weight: 700;
            font-size: 1rem;
        }}
        td.warn {{
            color: #ffd93d;
            font-weight: 600;
        }}
        td.good {{
            color: #4ecdc4;
            font-weight: 600;
        }}
        .insight {{
            margin-top: 20px;
            padding: 16px 20px;
            background: rgba(255,107,107,0.08);
            border-left: 3px solid #ff6b6b;
            border-radius: 0 10px 10px 0;
            color: #ffb4b4;
            font-size: 0.92rem;
        }}
        .insight.positive {{
            background: rgba(78,205,196,0.08);
            border-left-color: #4ecdc4;
            color: #b4ffe0;
        }}
        .insight strong {{ color: inherit; }}
        .stat-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(160px, 1fr));
            gap: 14px;
        }}
        .stat {{
            text-align: center;
            padding: 14px;
            background: rgba(255,255,255,0.03);
            border-radius: 10px;
        }}
        .stat .val {{
            display: block;
            font-size: 1.4rem;
            font-weight: 700;
            color: #4ecdc4;
            margin-bottom: 4px;
        }}
        .stat .val.danger {{ color: #ff6b6b; }}
        .stat .label {{
            font-size: 0.72rem;
            color: #888;
            text-transform: uppercase;
            letter-spacing: 0.5px;
        }}
        .badge {{
            display: inline-block;
            padding: 3px 10px;
            border-radius: 12px;
            font-size: 0.75rem;
            font-weight: 600;
        }}
        .badge.rec {{
            background: rgba(78,205,196,0.2);
            color: #4ecdc4;
            border: 1px solid rgba(78,205,196,0.3);
        }}
    </style>
</head>
<body>
    <div class="container">
        <h1>Pasteurize Phase Performance Analysis</h1>
        <p class="subtitle">Multi-run comparison &middot; Integral error diagnostics &middot; Enhanced ki simulation</p>

        <!-- KEY FINDINGS -->
        <div class="card">
            <h3>Key Findings</h3>
            <div class="stat-grid">
                <div class="stat">
                    <span class="val danger">{avg_dur:.0f} min</span>
                    <span class="label">Avg Pasteurize Duration</span>
                </div>
                <div class="stat">
                    <span class="val danger">{avg_duty:.1f}%</span>
                    <span class="label">Avg Duty Cycle</span>
                </div>
                <div class="stat">
                    <span class="val danger">{avg_power:.0f}W</span>
                    <span class="label">Avg Effective Power (of {all_metrics[0]['power_watts']}W)</span>
                </div>
                <div class="stat">
                    <span class="val">{all_metrics[0]['ff_duty_pct']:.1f}%</span>
                    <span class="label">Feedforward Duty (steady-state)</span>
                </div>
                <div class="stat">
                    <span class="val">{all_metrics[0]['optimal_duty_1c_per_min']:.1f}%</span>
                    <span class="label">Optimal Duty (1 deg C/min ramp)</span>
                </div>
                <div class="stat">
                    <span class="val">{all_metrics[0]['ki_actual']:.0e}</span>
                    <span class="label">Current ki Value</span>
                </div>
            </div>
            <div class="insight">
                <strong>Root Cause:</strong> The feedforward computes steady-state maintenance power ({all_metrics[0]['ff_duty_pct']:.1f}% = {all_metrics[0]['ff_duty_pct']/100*all_metrics[0]['power_watts']:.0f}W),
                not ramp-up power. The PID ki={all_metrics[0]['ki_actual']:.0e} is so small that even after
                {max(m['duration_min'] for m in all_metrics):.0f} minutes of sustained error, the integral term contributes less than 1% duty.
                Effectively only ~{avg_power:.0f}W of {all_metrics[0]['power_watts']}W is used during PASTEURIZE.
            </div>
        </div>

        <!-- SUMMARY TABLE -->
        <div class="card">
            <h3>Run Comparison Summary</h3>
            <div style="overflow-x:auto;">
            <table>
                <tr>
                    <th>Run</th>
                    <th>Temp Range</th>
                    <th>Duration</th>
                    <th>Heating Rate</th>
                    <th>Avg Duty</th>
                    <th>Effective Power</th>
                    <th>Total integral error dt</th>
                    <th>Max 2min integral error</th>
                </tr>
                {summary_rows}
            </table>
            </div>
        </div>

        <!-- CHARTS ROW 1: Temperature + Duty -->
        <div class="grid-2">
            <div class="card">
                <h3>Temperature Profiles (PASTEURIZE Only)</h3>
                <div class="chart-container">
                    <canvas id="tempChart"></canvas>
                </div>
            </div>
            <div class="card">
                <h3>Actual Duty Cycle vs Optimal</h3>
                <div class="chart-container">
                    <canvas id="dutyChart"></canvas>
                </div>
            </div>
        </div>

        <!-- CHARTS ROW 2: Integral Errors -->
        <div class="grid-2">
            <div class="card">
                <h3>Rolling 2-Min Integral Error</h3>
                <div class="chart-container">
                    <canvas id="rieChart"></canvas>
                </div>
                <p style="color:#888; font-size:0.8rem; margin-top:12px;">
                    Shows the accumulated (setpoint - temperature) x dt over the last 120 seconds at each point.
                    High sustained values indicate the controller is not responding aggressively enough.
                </p>
            </div>
            <div class="card">
                <h3>Cumulative Integral Error</h3>
                <div class="chart-container">
                    <canvas id="cieChart"></canvas>
                </div>
                <p style="color:#888; font-size:0.8rem; margin-top:12px;">
                    Total accumulated error since PASTEURIZE start. This is what the PID integral term
                    integrates. With ki={all_metrics[0]['ki_actual']:.0e}, even {max(m['total_integral_error'] for m in all_metrics):.0f} deg C s of accumulated error
                    produces only {all_metrics[0]['ki_actual'] * max(m['total_integral_error'] for m in all_metrics) * 100:.3f}% duty.
                </p>
            </div>
        </div>

        <!-- SIMULATED KI CHART -->
        <div class="card">
            <h3>Simulated Duty Cycle with Enhanced ki Values (Run: {all_metrics[0]['run_name']})</h3>
            <div class="chart-container" style="height:420px;">
                <canvas id="simChart"></canvas>
            </div>
            <p style="color:#888; font-size:0.8rem; margin-top:12px;">
                Shows what the duty cycle <em>would have been</em> if the ki value were higher,
                using the actual temperature data from this run. Higher ki means faster integral ramp and more power applied earlier.
            </p>
        </div>

        <!-- KI RECOMMENDATION TABLE -->
        <div class="card">
            <h3>Enhanced ki &mdash; Impact Estimates</h3>
            <div style="overflow-x:auto;">
            <table>
                <tr>
                    <th>ki Value</th>
                    <th>Avg Duty</th>
                    <th>Max Duty</th>
                    <th>Eff. Power</th>
                    <th>Est. Duration</th>
                    <th>Speedup</th>
                </tr>
                <tr>
                    <td>Actual (ki={all_metrics[0]['ki_actual']:.0e})</td>
                    <td class="warn">{all_metrics[0]['avg_duty_pct']:.1f}%</td>
                    <td>{all_metrics[0]['max_duty_pct']:.1f}%</td>
                    <td>{all_metrics[0]['effective_power_w']:.0f}W</td>
                    <td class="highlight">{all_metrics[0]['duration_min']:.0f} min</td>
                    <td>1.0x</td>
                </tr>
                {ki_rec_rows}
            </table>
            </div>
            <div class="insight positive">
                <strong>Recommendation:</strong> A ki value in the range <strong>1e-04 to 5e-04</strong> would
                significantly increase duty during PASTEURIZE while still allowing the integral to settle
                once the setpoint is reached. Combined with the existing anti-windup clamp, this should
                safely reduce PASTEURIZE time from ~{avg_dur:.0f} min to an estimated 15-30 min.
                <br><br>
                <span class="badge rec">RECOMMENDED: ki = 1e-04</span> &mdash; Good balance between speed and overshoot control.
                The anti-windup clamp (max integral = 1/ki = 10,000) limits the I-term to a maximum of 1.0 (100% duty),
                and the safety_max_temp cutoff provides a hard backstop.
            </div>
        </div>

        <!-- HEATING TIME SCENARIOS -->
        <div class="card">
            <h3>Theoretical Heating Time at Various Duty Cycles</h3>
            <table>
                <tr>
                    <th>Duty Cycle</th>
                    <th>Effective Power</th>
                    <th>Est. Time ({all_metrics[0]['start_temp']:.0f} to {all_metrics[0]['setpoint']:.0f} deg C)</th>
                    <th>Speedup vs Actual</th>
                </tr>
                <tr>
                    <td>Current (~{all_metrics[0]['avg_duty_pct']:.0f}%)</td>
                    <td>{all_metrics[0]['effective_power_w']:.0f}W</td>
                    <td class="highlight">{all_metrics[0]['duration_min']:.0f} min</td>
                    <td>1.0x</td>
                </tr>
                {scenario_rows}
            </table>
        </div>

    </div>

    <script>
        // Common chart options
        const commonOpts = {{
            responsive: true,
            maintainAspectRatio: false,
            plugins: {{
                legend: {{
                    labels: {{ color: '#e0e0f0', font: {{ size: 11 }} }}
                }}
            }},
            scales: {{
                x: {{
                    type: 'linear',
                    ticks: {{ color: '#666', maxTicksLimit: 15 }},
                    grid: {{ color: 'rgba(255,255,255,0.03)' }},
                    title: {{ display: true, text: 'Elapsed (min)', color: '#888' }}
                }},
                y: {{
                    ticks: {{ color: '#666' }},
                    grid: {{ color: 'rgba(255,255,255,0.05)' }}
                }}
            }}
        }};

        // 1. Temperature chart
        new Chart(document.getElementById('tempChart'), {{
            type: 'line',
            data: {{ datasets: {json.dumps(temp_datasets)} }},
            options: {{
                ...commonOpts,
                scales: {{
                    ...commonOpts.scales,
                    y: {{ ...commonOpts.scales.y, title: {{ display: true, text: 'Temperature (deg C)', color: '#888' }} }}
                }}
            }}
        }});

        // 2. Duty cycle chart
        new Chart(document.getElementById('dutyChart'), {{
            type: 'line',
            data: {{ datasets: {json.dumps(duty_datasets)} }},
            options: {{
                ...commonOpts,
                scales: {{
                    ...commonOpts.scales,
                    y: {{ ...commonOpts.scales.y, title: {{ display: true, text: 'Duty Cycle (%)', color: '#888' }} }}
                }}
            }}
        }});

        // 3. Rolling integral error chart
        new Chart(document.getElementById('rieChart'), {{
            type: 'line',
            data: {{ datasets: {json.dumps(rie_datasets)} }},
            options: {{
                ...commonOpts,
                scales: {{
                    ...commonOpts.scales,
                    y: {{ ...commonOpts.scales.y, title: {{ display: true, text: 'Integral error dt (deg C s) [2-min window]', color: '#888' }} }}
                }}
            }}
        }});

        // 4. Cumulative integral error chart
        new Chart(document.getElementById('cieChart'), {{
            type: 'line',
            data: {{ datasets: {json.dumps(cie_datasets)} }},
            options: {{
                ...commonOpts,
                scales: {{
                    ...commonOpts.scales,
                    y: {{ ...commonOpts.scales.y, title: {{ display: true, text: 'Cumulative integral error dt (deg C s)', color: '#888' }} }}
                }}
            }}
        }});

        // 5. Simulated ki chart
        new Chart(document.getElementById('simChart'), {{
            type: 'line',
            data: {{ datasets: {json.dumps(sim_datasets)} }},
            options: {{
                ...commonOpts,
                scales: {{
                    ...commonOpts.scales,
                    y: {{
                        ...commonOpts.scales.y,
                        title: {{ display: true, text: 'Simulated Duty Cycle (%)', color: '#888' }},
                        max: 100
                    }}
                }}
            }}
        }});
    </script>
</body>
</html>"""

    with open(output_path, "w") as f:
        f.write(html)

    return html


def main():
    print("=" * 56)
    print("  Pasteurize Phase Performance Analysis")
    print("=" * 56)

    # Determine run paths
    if len(sys.argv) > 1:
        run_paths = [Path(p) for p in sys.argv[1:]]
    else:
        run_paths = [BASE_DIR / r for r in DEFAULT_RUNS]

    # Load all runs
    print(f"\nLoading {len(run_paths)} runs...")
    runs = []
    for rp in run_paths:
        if not rp.exists():
            print(f"  Warning: Path not found: {rp}")
            continue
        run = load_run(rp)
        if run and run["pasteurize_data"]:
            runs.append(run)
            print(f"  OK {run['name']}: {len(run['pasteurize_data'])} PASTEURIZE samples")
        elif run:
            print(f"  Warning: {run['name']}: no PASTEURIZE data found")

    if not runs:
        print("\nERROR: No valid runs with PASTEURIZE data found.")
        sys.exit(1)

    # Compute metrics
    print(f"\nAnalyzing {len(runs)} runs...")
    all_metrics = []
    for run in runs:
        metrics = compute_pasteurize_metrics(run)
        if metrics:
            all_metrics.append(metrics)
            print(f"  OK {metrics['run_name']}: {metrics['duration_min']} min, "
                  f"avg duty {metrics['avg_duty_pct']:.1f}%, "
                  f"integral_error = {metrics['total_integral_error']:.0f} deg C s")

    if not all_metrics:
        print("\nERROR: No metrics computed.")
        sys.exit(1)

    # Generate report
    output_dir = BASE_DIR / "analytics"
    output_dir.mkdir(exist_ok=True)
    report_path = output_dir / "pasteurize_analysis_report.html"

    print(f"\nGenerating report...")
    generate_html_report(all_metrics, report_path)
    print(f"  OK HTML report: {report_path}")

    # Save JSON results
    json_results = []
    for m in all_metrics:
        # Remove time-series data from JSON output (too large)
        result = {k: v for k, v in m.items() if not k.startswith("_")}
        json_results.append(result)

    json_path = output_dir / "pasteurize_analysis.json"
    with open(json_path, "w") as f:
        json.dump(json_results, f, indent=2)
    print(f"  OK JSON data:   {json_path}")

    # Print summary
    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)
    avg_dur = sum(m["duration_min"] for m in all_metrics) / len(all_metrics)
    avg_duty = sum(m["avg_duty_pct"] for m in all_metrics) / len(all_metrics)
    avg_power = sum(m["effective_power_w"] for m in all_metrics) / len(all_metrics)

    print(f"  Runs analyzed:       {len(all_metrics)}")
    print(f"  Avg PASTEURIZE time: {avg_dur:.0f} min")
    print(f"  Avg duty cycle:      {avg_duty:.1f}% ({avg_power:.0f}W of {all_metrics[0]['power_watts']}W)")
    print(f"  Feedforward duty:    {all_metrics[0]['ff_duty_pct']:.1f}%")
    print(f"  Current ki:          {all_metrics[0]['ki_actual']:.0e}")
    print(f"\n  RECOMMENDATION: Increase ki to 1e-04 (3333x larger)")
    print(f"  Expected result: PASTEURIZE time ~15-30 min instead of ~{avg_dur:.0f} min")
    print("=" * 60)


if __name__ == "__main__":
    main()
