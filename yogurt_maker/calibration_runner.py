"""Smart Yogurt Maker — Calibration Runner (Host-side)

Runs on the Raspberry Pi Zero 2W (or development machine).
Deploys the calibration_test.py to the Pico W via mpremote,
captures the serial output, and saves it as a CSV file for analysis.

Usage:
    python calibration_runner.py --machine 800w_multi_cooker --volume 1.5

The script creates a timestamped directory in data/calibration/ with:
  - calibration_data.csv   (parsed sensor data)
  - raw_output.log         (full serial output)
  - metadata.json          (test parameters)
"""

import subprocess
import datetime
import sys
import re
import os
import json
import argparse


def parse_args():
    parser = argparse.ArgumentParser(description="Run calibration test on Pico W")
    parser.add_argument(
        "--machine",
        required=True,
        choices=["800w_multi_cooker", "500w_rice_cooker_warm", "800w_rice_cooker_cook"],
        help="Machine being tested"
    )
    parser.add_argument(
        "--milk-volume",
        type=float,
        default=0.25,
        help="Milk (or dummy water) volume in liters (default: 0.25L)"
    )
    parser.add_argument(
        "--water-bath-volume",
        type=float,
        default=1.75,
        help="Water bath volume in liters (default: 1.75L)"
    )
    parser.add_argument(
        "--pot-type",
        type=str,
        default="porcelain",
        help="Type of pot used (e.g., porcelain_250ml, glass_500ml, None)"
    )
    parser.add_argument(
        "--heating-target",
        type=float,
        default=55.0,
        help="Stop heating at this temperature (default: 55°C)"
    )
    parser.add_argument(
        "--cooling-target",
        type=float,
        default=40.0,
        help="Stop cooling at this temperature (default: 40°C)"
    )
    return parser.parse_args()


def main():
    args = parse_args()

    # Total volume calculation
    total_volume = args.milk_volume + args.water_bath_volume

    # Load machine config
    with open("config.json", "r") as f:
        config = json.load(f)

    machine_config = config["machines"].get(args.machine)
    if not machine_config:
        print(f"Error: Machine '{args.machine}' not found in config.json")
        sys.exit(1)

    # Create output directory
    timestamp = datetime.datetime.now().strftime("%Y_%m_%d_%H_%M_%S")
    run_dir = os.path.join("data", "calibration", f"{args.machine}_{timestamp}")
    os.makedirs(run_dir, exist_ok=True)

    csv_path = os.path.join(run_dir, "calibration_data.csv")
    raw_log_path = os.path.join(run_dir, "raw_output.log")
    metadata_path = os.path.join(run_dir, "metadata.json")

    # Save metadata
    metadata = {
        "test_type": "calibration",
        "machine": args.machine,
        "machine_name": machine_config["name"],
        "power_watts": machine_config["power_watts"],
        "milk_volume_liters": args.milk_volume,
        "water_bath_volume_liters": args.water_bath_volume,
        "total_water_volume_liters": total_volume,
        "total_water_mass_kg": total_volume,  # 1L water ≈ 1kg
        "pot_type": args.pot_type,
        "heating_target_c": args.heating_target,
        "cooling_target_c": args.cooling_target,
        "timestamp": timestamp,
    }
    with open(metadata_path, "w") as f:
        json.dump(metadata, f, indent=4)

    print(f"╔══════════════════════════════════════════════════╗")
    print(f"║  Smart Yogurt Maker — Calibration Test          ║")
    print(f"╠══════════════════════════════════════════════════╣")
    print(f"║  Machine: {machine_config['name']:<39}║")
    print(f"║  Power:   {machine_config['power_watts']}W{' ' * (37 - len(str(machine_config['power_watts'])))}║")
    print(f"║  Volume:  {total_volume}L{' ' * (37 - len(str(total_volume)))}║")
    print(f"║  Heating target: {args.heating_target}°C{' ' * (29 - len(str(args.heating_target)))}║")
    print(f"║  Cooling target: {args.cooling_target}°C{' ' * (29 - len(str(args.cooling_target)))}║")
    print(f"║  Output:  {run_dir:<39}║")
    print(f"╚══════════════════════════════════════════════════╝")
    print()

    # Launch mpremote run calibration_test.py
    print("Starting calibration test on Pico W...")
    process = subprocess.Popen(
        ["mpremote", "run", "calibration_test.py"],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1,
    )

    capturing_csv = False
    csv_lines = []

    try:
        with open(raw_log_path, "w") as raw_log:
            for line in iter(process.stdout.readline, ""):
                line = line.rstrip("\n")

                # Always log raw output
                raw_log.write(line + "\n")
                raw_log.flush()

                # Print to terminal
                sys.stdout.write(line + "\n")
                sys.stdout.flush()

                # Detect CSV boundaries
                if line.strip() == "CSV_START":
                    capturing_csv = True
                    continue
                elif line.strip() == "CSV_END":
                    capturing_csv = False
                    continue

                # Capture CSV data lines (skip comments)
                if capturing_csv and not line.startswith("#"):
                    csv_lines.append(line)

    except KeyboardInterrupt:
        print("\nCalibration interrupted by user.")
        process.terminate()

    process.wait()

    # Write parsed CSV
    if csv_lines:
        with open(csv_path, "w") as f:
            for csv_line in csv_lines:
                f.write(csv_line + "\n")
        print(f"\n✓ Saved {len(csv_lines) - 1} data points to {csv_path}")
        print(f"✓ Raw output saved to {raw_log_path}")
        print(f"✓ Metadata saved to {metadata_path}")
        print(f"\nNext step: run calibration_analyzer.py to compute thermal parameters:")
        print(f"  python calibration_analyzer.py {run_dir}")
    else:
        print("\n✗ No CSV data captured. Check the Pico connection.")


if __name__ == "__main__":
    main()
