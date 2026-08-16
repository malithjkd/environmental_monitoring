"""Physics Analysis Report Generator for Yogurt Maker Calibration & Run Data.

Generates a comprehensive interactive HTML report with:
  - Heating rate analysis
  - Thermal soak characterization
  - Cooling profiles (lid closed vs lid open vs water swap)
  - Energy calculations
  - Sensor lag estimation
  - Water swap cooling dynamics

Usage:
    python analytics/physics_report.py data/calibration/800w_multi_cooker_2026_08_02_22_27_43
    python analytics/physics_report.py data/2026_08_11_20_50_28
"""

import csv
import json
import sys
from pathlib import Path
from datetime import datetime

WATER_SPECIFIC_HEAT = 4186.0  # J/(kg·°C)


def load_calibration_data(run_path):
    """Load calibration CSV data."""
    csv_file = run_path / "calibration_data.csv"
    if not csv_file.exists():
        return None
    data = []
    with open(csv_file) as f:
        for row in csv.DictReader(f):
            data.append({
                "elapsed_s": float(row["elapsed_s"]),
                "temperature_c": float(row["temperature_c"]),
                "phase": row["phase"],
                "relay_state": int(row["relay_state"]),
            })
    return data


def load_run_data(run_path):
    """Load yogurt run CSV data."""
    csv_file = run_path / "temperature_log.csv"
    if not csv_file.exists():
        return None
    data = []
    with open(csv_file) as f:
        for row in csv.DictReader(f):
            data.append(row)
    return data


def analyze_calibration(data, metadata):
    """Analyze calibration heating/cooling test."""
    water_mass = metadata.get("water_mass_kg", metadata.get("water_volume_liters", 1.5))
    rated_power = metadata.get("power_watts", 800)

    heating = [d for d in data if d["phase"] == "HEATING"]
    cooling = [d for d in data if d["phase"] == "COOLING"]

    results = {"water_mass_kg": water_mass, "rated_power_w": rated_power}

    # Heating analysis
    if heating:
        t_start = heating[0]["temperature_c"]
        t_end = heating[-1]["temperature_c"]
        heat_dur = heating[-1]["elapsed_s"] - heating[0]["elapsed_s"]
        dT_heat = t_end - t_start
        Q_heat = water_mass * WATER_SPECIFIC_HEAT * dT_heat
        P_eff_heat = Q_heat / heat_dur if heat_dur > 0 else 0

        results["heating"] = {
            "start_temp_c": t_start,
            "end_temp_c": t_end,
            "delta_t_c": round(dT_heat, 2),
            "duration_s": round(heat_dur, 1),
            "energy_j": round(Q_heat, 1),
            "energy_kj": round(Q_heat / 1000, 1),
            "effective_power_w": round(P_eff_heat, 1),
            "heating_rate_c_per_min": round(dT_heat / (heat_dur / 60), 3) if heat_dur > 0 else 0,
        }

    # Thermal soak analysis
    if cooling:
        heater_off_temp = heating[-1]["temperature_c"] if heating else cooling[0]["temperature_c"]
        peak_temp = max(d["temperature_c"] for d in cooling)
        peak_idx = next(i for i, d in enumerate(cooling) if d["temperature_c"] == peak_temp)
        heater_off_time = heating[-1]["elapsed_s"] if heating else cooling[0]["elapsed_s"]
        soak_dur = cooling[peak_idx]["elapsed_s"] - heater_off_time
        soak_dT = peak_temp - heater_off_temp
        Q_soak = water_mass * WATER_SPECIFIC_HEAT * soak_dT

        results["thermal_soak"] = {
            "heater_off_temp_c": round(heater_off_temp, 2),
            "peak_temp_c": round(peak_temp, 2),
            "soak_delta_t_c": round(soak_dT, 2),
            "soak_duration_s": round(soak_dur, 1),
            "residual_energy_j": round(Q_soak, 1),
            "residual_energy_kj": round(Q_soak / 1000, 1),
            "equivalent_heating_s": round(Q_soak / rated_power, 1),
        }

        # Total energy
        total_dT = peak_temp - results["heating"]["start_temp_c"]
        Q_total = water_mass * WATER_SPECIFIC_HEAT * total_dT
        P_eff_total = Q_total / results["heating"]["duration_s"]
        results["total_energy"] = {
            "total_delta_t_c": round(total_dT, 2),
            "total_energy_kj": round(Q_total / 1000, 1),
            "effective_power_w": round(P_eff_total, 1),
            "efficiency_pct": round(P_eff_total / rated_power * 100, 1),
        }

        # Cooling analysis — split at 10 min after heater off
        cooling_after_peak = [d for d in cooling if d["elapsed_s"] >= cooling[peak_idx]["elapsed_s"]]
        lid_open_time = heater_off_time + 600  # 10 minutes

        lid_closed = [d for d in cooling_after_peak if d["elapsed_s"] <= lid_open_time]
        lid_open = [d for d in cooling_after_peak if d["elapsed_s"] > lid_open_time]

        cooling_profiles = {}
        if len(lid_closed) > 5:
            dt = lid_closed[-1]["elapsed_s"] - lid_closed[0]["elapsed_s"]
            dT = lid_closed[-1]["temperature_c"] - lid_closed[0]["temperature_c"]
            rate = dT / (dt / 60) if dt > 0 else 0
            cooling_profiles["lid_closed"] = {
                "start_temp_c": round(lid_closed[0]["temperature_c"], 2),
                "end_temp_c": round(lid_closed[-1]["temperature_c"], 2),
                "duration_s": round(dt, 1),
                "rate_c_per_min": round(rate, 3),
            }

        if len(lid_open) > 5:
            dt = lid_open[-1]["elapsed_s"] - lid_open[0]["elapsed_s"]
            dT = lid_open[-1]["temperature_c"] - lid_open[0]["temperature_c"]
            rate = dT / (dt / 60) if dt > 0 else 0
            cooling_profiles["lid_open"] = {
                "start_temp_c": round(lid_open[0]["temperature_c"], 2),
                "end_temp_c": round(lid_open[-1]["temperature_c"], 2),
                "duration_s": round(dt, 1),
                "rate_c_per_min": round(rate, 3),
            }

        results["cooling"] = cooling_profiles

    return results


def analyze_run(data, metadata):
    """Analyze a full yogurt run."""
    results = {}

    # Stage durations
    stages = []
    current_stage = data[0]["Stage"]
    stages.append({"stage": current_stage, "start": data[0]["Timestamp"], "start_temp": data[0]["Temperature_C"]})
    for row in data:
        if row["Stage"] != current_stage:
            stages[-1]["end"] = row["Timestamp"]
            stages[-1]["end_temp"] = row["Temperature_C"]
            current_stage = row["Stage"]
            stages.append({"stage": current_stage, "start": row["Timestamp"], "start_temp": row["Temperature_C"]})
    stages[-1]["end"] = data[-1]["Timestamp"]
    stages[-1]["end_temp"] = data[-1]["Temperature_C"]

    stage_info = []
    for s in stages:
        t1 = datetime.strptime(s["start"], "%Y-%m-%d %H:%M:%S")
        t2 = datetime.strptime(s["end"], "%Y-%m-%d %H:%M:%S")
        dur = (t2 - t1).total_seconds()
        stage_info.append({
            "stage": s["stage"],
            "duration_s": dur,
            "duration_min": round(dur / 60, 1),
            "start_temp_c": float(s["start_temp"]),
            "end_temp_c": float(s["end_temp"]),
        })
    results["stages"] = stage_info

    # Pasteurize analysis
    past_data = [r for r in data if r["Stage"] == "PASTEURIZE"]
    if past_data:
        p_temps = [float(r["Temperature_C"]) for r in past_data]
        p_duties = [float(r["Duty_Cycle"]) for r in past_data]
        t0 = datetime.strptime(past_data[0]["Timestamp"], "%Y-%m-%d %H:%M:%S")
        t1 = datetime.strptime(past_data[-1]["Timestamp"], "%Y-%m-%d %H:%M:%S")
        dur = (t1 - t0).total_seconds()
        results["pasteurize"] = {
            "duration_min": round(dur / 60, 1),
            "temp_range": f"{p_temps[0]:.1f} -> {p_temps[-1]:.1f}",
            "heating_rate_c_per_min": round((p_temps[-1] - p_temps[0]) / (dur / 60), 3) if dur > 0 else 0,
            "avg_duty_pct": round(sum(p_duties) / len(p_duties) * 100, 2),
            "max_duty_pct": round(max(p_duties) * 100, 2),
        }

    # Cooling analysis (detect water swaps)
    cool_data = [r for r in data if r["Stage"] == "COOL_DOWN"]
    if cool_data:
        temps = [float(r["Temperature_C"]) for r in cool_data]
        t0 = datetime.strptime(cool_data[0]["Timestamp"], "%Y-%m-%d %H:%M:%S")

        # Detect major water swap events
        swaps = []
        i = 0
        while i < len(temps) - 5:
            drop = temps[i] - temps[i + 5]
            if drop > 5.0:  # major swap: > 5°C in 10s
                start_idx = i
                while i < len(temps) - 1 and (temps[i] - temps[i + 1]) > -0.5:
                    i += 1
                end_idx = min(i, len(temps) - 1)
                t_s = datetime.strptime(cool_data[start_idx]["Timestamp"], "%Y-%m-%d %H:%M:%S")
                t_e = datetime.strptime(cool_data[end_idx]["Timestamp"], "%Y-%m-%d %H:%M:%S")
                dur = (t_e - t_s).total_seconds()
                swaps.append({
                    "start_temp_c": round(temps[start_idx], 2),
                    "end_temp_c": round(temps[end_idx], 2),
                    "drop_c": round(temps[start_idx] - temps[end_idx], 2),
                    "duration_s": dur,
                    "rate_c_per_min": round((temps[start_idx] - temps[end_idx]) / (dur / 60), 2) if dur > 0 else 0,
                })
            i += 1

        cool_dur = (datetime.strptime(cool_data[-1]["Timestamp"], "%Y-%m-%d %H:%M:%S") - t0).total_seconds()
        results["cooling"] = {
            "total_duration_min": round(cool_dur / 60, 1),
            "temp_range": f"{temps[0]:.1f} -> {temps[-1]:.1f}",
            "water_swaps_detected": len(swaps),
            "swaps": swaps,
        }

    # Total process
    t_start = datetime.strptime(data[0]["Timestamp"], "%Y-%m-%d %H:%M:%S")
    t_end = datetime.strptime(data[-1]["Timestamp"], "%Y-%m-%d %H:%M:%S")
    results["total_duration_hrs"] = round((t_end - t_start).total_seconds() / 3600, 2)
    results["max_temp_c"] = max(float(r["Temperature_C"]) for r in data)

    return results


def generate_html_report(results, run_path, data, is_calibration):
    """Generate an interactive HTML physics report."""
    title = f"Physics Report — {run_path.name}"

    # Prepare chart data
    if is_calibration:
        chart_labels = [str(d["elapsed_s"]) for d in data[::5]]
        chart_temps = [d["temperature_c"] for d in data[::5]]
        chart_phases = [d["phase"] for d in data[::5]]
        x_label = "Elapsed Time (s)"
    else:
        chart_labels = [r["Timestamp"].split(" ")[1] for r in data[::10]]
        chart_temps = [float(r["Temperature_C"]) for r in data[::10]]
        chart_phases = [r["Stage"] for r in data[::10]]
        x_label = "Time"

    # Build the results summary cards
    cards_html = ""

    if "heating" in results:
        h = results["heating"]
        cards_html += f"""
        <div class="card">
            <h3>🔥 Heating Phase</h3>
            <div class="stat-grid">
                <div class="stat"><span class="val">{h['start_temp_c']:.1f} → {h['end_temp_c']:.1f}</span><span class="label">Temperature (°C)</span></div>
                <div class="stat"><span class="val">{h['duration_s']:.0f}s ({h['duration_s']/60:.1f} min)</span><span class="label">Duration</span></div>
                <div class="stat"><span class="val">{h['energy_kj']:.1f} kJ</span><span class="label">Energy Absorbed</span></div>
                <div class="stat"><span class="val">{h['effective_power_w']:.0f} W</span><span class="label">Effective Power</span></div>
                <div class="stat"><span class="val">{h['heating_rate_c_per_min']:.2f} °C/min</span><span class="label">Heating Rate</span></div>
            </div>
        </div>"""

    if "thermal_soak" in results:
        s = results["thermal_soak"]
        cards_html += f"""
        <div class="card">
            <h3>🌡️ Thermal Soak (Sensor Lag)</h3>
            <div class="stat-grid">
                <div class="stat"><span class="val">{s['heater_off_temp_c']:.1f} → {s['peak_temp_c']:.1f}</span><span class="label">Temp Rise After Heater OFF</span></div>
                <div class="stat"><span class="val">+{s['soak_delta_t_c']:.1f} °C</span><span class="label">Overshoot</span></div>
                <div class="stat"><span class="val">{s['soak_duration_s']:.0f}s ({s['soak_duration_s']/60:.1f} min)</span><span class="label">Soak Duration</span></div>
                <div class="stat"><span class="val">{s['residual_energy_kj']:.1f} kJ</span><span class="label">Residual Energy</span></div>
                <div class="stat"><span class="val">{s['equivalent_heating_s']:.0f}s</span><span class="label">Equiv. Heating Time @ {results['rated_power_w']}W</span></div>
            </div>
        </div>"""

    if "total_energy" in results:
        e = results["total_energy"]
        cards_html += f"""
        <div class="card">
            <h3>⚡ Energy Summary</h3>
            <div class="stat-grid">
                <div class="stat"><span class="val">{e['total_energy_kj']:.1f} kJ</span><span class="label">Total Energy to Peak</span></div>
                <div class="stat"><span class="val">{e['effective_power_w']:.0f} W</span><span class="label">Effective Power</span></div>
                <div class="stat"><span class="val">{e['efficiency_pct']:.1f}%</span><span class="label">Efficiency ({results['rated_power_w']}W rated)</span></div>
            </div>
        </div>"""

    if "cooling" in results and isinstance(results["cooling"], dict):
        cool = results["cooling"]
        if "lid_closed" in cool or "lid_open" in cool:
            cooling_items = ""
            if "lid_closed" in cool:
                lc = cool["lid_closed"]
                cooling_items += f'<div class="stat"><span class="val">{lc["rate_c_per_min"]:.3f} °C/min</span><span class="label">Lid Closed ({lc["start_temp_c"]:.0f}→{lc["end_temp_c"]:.0f}°C)</span></div>'
            if "lid_open" in cool:
                lo = cool["lid_open"]
                cooling_items += f'<div class="stat"><span class="val">{lo["rate_c_per_min"]:.3f} °C/min</span><span class="label">Lid Open ({lo["start_temp_c"]:.0f}→{lo["end_temp_c"]:.0f}°C)</span></div>'
            cards_html += f"""
            <div class="card">
                <h3>❄️ Cooling Profiles</h3>
                <div class="stat-grid">{cooling_items}</div>
            </div>"""

        if "total_duration_min" in cool:
            swap_rows = ""
            for i, sw in enumerate(cool.get("swaps", [])):
                swap_rows += f"<tr><td>{i+1}</td><td>{sw['start_temp_c']:.1f} → {sw['end_temp_c']:.1f}</td><td>{sw['drop_c']:.1f}</td><td>{sw['duration_s']:.0f}s</td><td>{sw['rate_c_per_min']:.1f}</td></tr>"

            cards_html += f"""
            <div class="card">
                <h3>🔄 Water Swap Cooling ({cool['total_duration_min']:.0f} min total)</h3>
                <p>Temperature: {cool['temp_range']} °C | Swaps detected: {cool['water_swaps_detected']}</p>
                <table class="swap-table">
                    <tr><th>#</th><th>Temp Range</th><th>Drop (°C)</th><th>Duration</th><th>Rate (°C/min)</th></tr>
                    {swap_rows}
                </table>
            </div>"""

    if "stages" in results:
        stage_rows = ""
        for st in results["stages"]:
            stage_rows += f"<tr><td>{st['stage']}</td><td>{st['duration_min']:.1f} min</td><td>{st['start_temp_c']:.1f}</td><td>{st['end_temp_c']:.1f}</td></tr>"
        cards_html += f"""
        <div class="card">
            <h3>📊 Stage Durations (Total: {results.get('total_duration_hrs', 0):.2f} hrs)</h3>
            <table class="swap-table">
                <tr><th>Stage</th><th>Duration</th><th>Start °C</th><th>End °C</th></tr>
                {stage_rows}
            </table>
        </div>"""

    if "pasteurize" in results:
        p = results["pasteurize"]
        cards_html += f"""
        <div class="card">
            <h3>🐌 Pasteurize Phase Analysis</h3>
            <div class="stat-grid">
                <div class="stat"><span class="val">{p['duration_min']:.0f} min ({p['duration_min']/60:.1f} hrs)</span><span class="label">Duration</span></div>
                <div class="stat"><span class="val">{p['temp_range']} °C</span><span class="label">Temperature Range</span></div>
                <div class="stat"><span class="val">{p['heating_rate_c_per_min']:.3f} °C/min</span><span class="label">Average Heating Rate</span></div>
                <div class="stat"><span class="val">{p['avg_duty_pct']:.1f}%</span><span class="label">Avg Duty Cycle</span></div>
                <div class="stat"><span class="val">{p['max_duty_pct']:.1f}%</span><span class="label">Max Duty Cycle</span></div>
            </div>
            <p class="insight">⚠️ At {p['avg_duty_pct']:.0f}% average duty, only ~{p['avg_duty_pct']/100*800:.0f}W of the 800W heater is being used. Rapid heating at 80% duty would heat ~{0.80/p['avg_duty_pct']*100:.0f}× faster.</p>
        </div>"""

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{title}</title>
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{ font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif; background: #0a0a1a; color: #e0e0f0; padding: 24px; }}
        .container {{ max-width: 1200px; margin: 0 auto; }}
        h1 {{ text-align: center; font-size: 1.8rem; margin-bottom: 8px; background: linear-gradient(135deg, #ff6b6b, #ffd93d, #6bcb77); -webkit-background-clip: text; -webkit-text-fill-color: transparent; }}
        .subtitle {{ text-align: center; color: #666; margin-bottom: 32px; }}
        .card {{ background: linear-gradient(135deg, rgba(30,30,50,0.9), rgba(20,20,40,0.95)); border: 1px solid rgba(255,255,255,0.08); border-radius: 16px; padding: 24px; margin-bottom: 20px; backdrop-filter: blur(10px); }}
        .card h3 {{ color: #a8b4ff; margin-bottom: 16px; font-size: 1.1rem; }}
        .stat-grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(180px, 1fr)); gap: 16px; }}
        .stat {{ text-align: center; padding: 12px; background: rgba(255,255,255,0.03); border-radius: 10px; }}
        .stat .val {{ display: block; font-size: 1.3rem; font-weight: 700; color: #4ecdc4; margin-bottom: 4px; }}
        .stat .label {{ font-size: 0.75rem; color: #888; text-transform: uppercase; letter-spacing: 0.5px; }}
        .chart-card {{ background: linear-gradient(135deg, rgba(30,30,50,0.9), rgba(20,20,40,0.95)); border: 1px solid rgba(255,255,255,0.08); border-radius: 16px; padding: 24px; margin-bottom: 20px; }}
        .chart-container {{ height: 400px; }}
        .swap-table {{ width: 100%; border-collapse: collapse; margin-top: 12px; }}
        .swap-table th, .swap-table td {{ padding: 8px 12px; text-align: left; border-bottom: 1px solid rgba(255,255,255,0.06); }}
        .swap-table th {{ color: #a8b4ff; font-size: 0.8rem; text-transform: uppercase; }}
        .swap-table td {{ color: #ccc; font-size: 0.9rem; }}
        .insight {{ margin-top: 16px; padding: 12px 16px; background: rgba(255,107,107,0.1); border-left: 3px solid #ff6b6b; border-radius: 0 8px 8px 0; color: #ffb4b4; font-size: 0.9rem; }}
        .json-block {{ background: rgba(0,0,0,0.3); border-radius: 8px; padding: 16px; overflow-x: auto; font-family: 'SF Mono', monospace; font-size: 0.8rem; color: #8899aa; margin-top: 20px; }}
    </style>
</head>
<body>
    <div class="container">
        <h1>⚗️ {title}</h1>
        <p class="subtitle">Automated thermal physics analysis</p>

        <div class="chart-card">
            <h3>Temperature Profile</h3>
            <div class="chart-container">
                <canvas id="mainChart"></canvas>
            </div>
        </div>

        {cards_html}

        <div class="card">
            <h3>📋 Raw Results (JSON)</h3>
            <pre class="json-block">{json.dumps(results, indent=2)}</pre>
        </div>
    </div>

    <script>
        const ctx = document.getElementById('mainChart').getContext('2d');
        new Chart(ctx, {{
            type: 'line',
            data: {{
                labels: {json.dumps(chart_labels)},
                datasets: [{{
                    label: 'Temperature (°C)',
                    data: {json.dumps(chart_temps)},
                    borderColor: '#ff6b6b',
                    backgroundColor: 'rgba(255, 107, 107, 0.08)',
                    borderWidth: 2,
                    pointRadius: 0,
                    tension: 0.2,
                    fill: true
                }}]
            }},
            options: {{
                responsive: true,
                maintainAspectRatio: false,
                plugins: {{
                    legend: {{ labels: {{ color: '#e0e0f0' }} }}
                }},
                scales: {{
                    x: {{
                        ticks: {{ color: '#666', maxTicksLimit: 15 }},
                        grid: {{ color: 'rgba(255,255,255,0.03)' }},
                        title: {{ display: true, text: '{x_label}', color: '#888' }}
                    }},
                    y: {{
                        ticks: {{ color: '#666' }},
                        grid: {{ color: 'rgba(255,255,255,0.05)' }},
                        title: {{ display: true, text: 'Temperature (°C)', color: '#888' }}
                    }}
                }}
            }}
        }});
    </script>
</body>
</html>"""

    return html


def main():
    if len(sys.argv) < 2:
        print("Usage: python analytics/physics_report.py <run_dir>")
        sys.exit(1)

    run_path = Path(sys.argv[1])

    if not run_path.exists():
        print(f"Error: {run_path} not found")
        sys.exit(1)

    # Load metadata
    meta_file = run_path / "metadata.json"
    metadata = {}
    if meta_file.exists():
        with open(meta_file) as f:
            metadata = json.load(f)

    # Determine type and analyze
    cal_data = load_calibration_data(run_path)
    run_data = load_run_data(run_path)

    if cal_data:
        print(f"Analyzing calibration data: {run_path.name}")
        results = analyze_calibration(cal_data, metadata)
        html = generate_html_report(results, run_path, cal_data, is_calibration=True)
        data_for_chart = cal_data
    elif run_data:
        print(f"Analyzing run data: {run_path.name}")
        results = analyze_run(run_data, metadata)
        html = generate_html_report(results, run_path, run_data, is_calibration=False)
        data_for_chart = run_data
    else:
        print(f"Error: No calibration_data.csv or temperature_log.csv found in {run_path}")
        sys.exit(1)

    # Save HTML report
    report_path = run_path / "physics_report.html"
    with open(report_path, "w") as f:
        f.write(html)
    print(f"✓ Report saved to {report_path}")

    # Save JSON results
    json_path = run_path / "physics_analysis.json"
    with open(json_path, "w") as f:
        json.dump(results, f, indent=2)
    print(f"✓ JSON saved to {json_path}")

    # Print summary
    print("\n=== Summary ===")
    print(json.dumps(results, indent=2))


if __name__ == "__main__":
    main()
