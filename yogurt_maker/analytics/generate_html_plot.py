import csv
import json
import sys
import os
from pathlib import Path

def generate_report(run_dir):
    run_path = Path(run_dir)
    csv_file = run_path / "temperature_log.csv"
    meta_file = run_path / "metadata.json"
    
    if not csv_file.exists():
        print(f"Error: {csv_file} not found")
        sys.exit(1)
        
    timestamps = []
    temps = []
    setpoints = []
    duties = []
    relays = []
    
    manual_timestamps = []
    manual_temps = []
    
    # Downsample data to avoid freezing the browser if there are too many points
    # 12 hours * 3600 seconds / 2s interval = 21600 points. Let's take every 10th point.
    step = 10 
    
    with open(csv_file, 'r') as f:
        reader = list(csv.DictReader(f))
        for i, row in enumerate(reader):
            if i % step == 0:
                # Keep time part only for cleaner x-axis
                time_str = row['Timestamp'].split(' ')[1] if ' ' in row['Timestamp'] else row['Timestamp']
                timestamps.append(time_str)
                temps.append(float(row['Temperature_C']))
                setpoints.append(float(row['Setpoint_C']))
                duties.append(float(row['Duty_Cycle']))
                relays.append(float(row['Relay_State']))
            
            # Manual temps are sparse, so we should always grab them regardless of step
            if 'Manual_Temp_C' in row and row['Manual_Temp_C'].strip():
                time_str = row['Timestamp'].split(' ')[1] if ' ' in row['Timestamp'] else row['Timestamp']
                manual_timestamps.append(time_str)
                manual_temps.append(float(row['Manual_Temp_C']))
            
    # read meta
    title = "Yogurt Maker Run Analysis"
    if meta_file.exists():
        with open(meta_file, 'r') as f:
            meta = json.load(f)
            title = f"Run: {meta.get('test_name', 'Unknown')} - {meta.get('machine', 'Unknown')} ({meta.get('timestamp')})"
            
    html_content = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>{title}</title>
        <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
        <style>
            body {{ font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif; background: #121212; color: #fff; padding: 20px; }}
            .container {{ max-width: 1200px; margin: 0 auto; background: #1e1e1e; padding: 20px; border-radius: 12px; box-shadow: 0 8px 16px rgba(0,0,0,0.5); }}
            h2 {{ text-align: center; color: #e0e0e0; }}
            .stats {{ display: flex; justify-content: space-around; margin-top: 20px; padding: 20px; background: #2a2a2a; border-radius: 8px; }}
            .stat-box {{ text-align: center; }}
            .stat-value {{ font-size: 24px; font-weight: bold; color: #4CAF50; }}
            .stat-label {{ font-size: 14px; color: #aaaaaa; }}
        </style>
    </head>
    <body>
        <div class="container">
            <h2>{title}</h2>
            <div style="width: 100%; margin: auto;">
                <canvas id="tempChart"></canvas>
            </div>
            
            <div class="stats">
                <div class="stat-box">
                    <div class="stat-value">{max(temps):.1f} &deg;C</div>
                    <div class="stat-label">Max Temperature</div>
                </div>
                <div class="stat-box">
                    <div class="stat-value">{len(reader)}</div>
                    <div class="stat-label">Total Data Points logged</div>
                </div>
                <div class="stat-box">
                    <div class="stat-value">{round(len(reader) * 2 / 3600, 2)} hrs</div>
                    <div class="stat-label">Duration (approx)</div>
                </div>
            </div>
        </div>
        <script>
            const ctx = document.getElementById('tempChart').getContext('2d');
            new Chart(ctx, {{
                type: 'line',
                data: {{
                    labels: {json.dumps(timestamps)},
                    datasets: [
                        {{
                            label: 'Temperature (°C)',
                            data: {json.dumps(temps)},
                            borderColor: '#FF5252',
                            backgroundColor: 'rgba(255, 82, 82, 0.1)',
                            yAxisID: 'y',
                            tension: 0.2,
                            pointRadius: 0,
                            borderWidth: 2,
                            fill: true
                        }},
                        {{
                            label: 'Setpoint (°C)',
                            data: {json.dumps(setpoints)},
                            borderColor: '#FFC107',
                            borderDash: [5, 5],
                            yAxisID: 'y',
                            tension: 0,
                            pointRadius: 0,
                            borderWidth: 2
                        }},
                        {{
                            label: 'Manual Pot Temp (°C)',
                            data: {json.dumps([{'x': mt_t, 'y': mt_v} for mt_t, mt_v in zip(manual_timestamps, manual_temps)])},
                            borderColor: '#00E676',
                            backgroundColor: '#00E676',
                            yAxisID: 'y',
                            type: 'scatter',
                            pointRadius: 6,
                            pointStyle: 'crossRot',
                            borderWidth: 2
                        }},
                        {{
                            label: 'Duty Cycle (%)',
                            data: {json.dumps(duties)},
                            borderColor: '#448AFF',
                            yAxisID: 'y1',
                            tension: 0.1,
                            pointRadius: 0,
                            borderWidth: 1,
                            backgroundColor: 'rgba(68, 138, 255, 0.1)',
                            fill: true
                        }}
                    ]
                }},
                options: {{
                    responsive: true,
                    interaction: {{
                      mode: 'index',
                      intersect: false,
                    }},
                    plugins: {{
                        legend: {{
                            labels: {{ color: '#e0e0e0' }}
                        }}
                    }},
                    scales: {{
                        x: {{
                            ticks: {{ color: '#aaa', maxTicksLimit: 20 }},
                            grid: {{ color: '#333' }}
                        }},
                        y: {{
                            type: 'linear',
                            display: true,
                            position: 'left',
                            title: {{ display: true, text: 'Temperature (°C)', color: '#e0e0e0' }},
                            ticks: {{ color: '#aaa' }},
                            grid: {{ color: '#333' }}
                        }},
                        y1: {{
                            type: 'linear',
                            display: true,
                            position: 'right',
                            grid: {{ drawOnChartArea: false }},
                            title: {{ display: true, text: 'Duty Cycle', color: '#e0e0e0' }},
                            ticks: {{ color: '#aaa' }}
                        }}
                    }}
                }}
            }});
        </script>
    </body>
    </html>
    """
    
    out_file = run_path / "interactive_report.html"
    with open(out_file, 'w') as f:
        f.write(html_content)
        
    print(f"Generated report at {out_file}")

if __name__ == "__main__":
    generate_report(sys.argv[1])
