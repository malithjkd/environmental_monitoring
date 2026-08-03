import csv
import os
from datetime import datetime

MAX_POINTS_IN_MEMORY = 100

class DataLogger:
    def __init__(self):
        self.history = []
        # We don't automatically load history on init anymore to avoid edge cases 
        # when starting exactly at midnight, we'll just rely on the live data 
        # or load what exists for today so far.
        self._load_today_history()

    def get_log_filename(self):
        # Generate filename based on current date, e.g., "2026-08-03.csv"
        date_str = datetime.now().strftime('%Y-%m-%d')
        return f"{date_str}.csv"

    def _ensure_file_exists(self, filename):
        if not os.path.exists(filename):
            with open(filename, mode='w', newline='') as file:
                writer = csv.writer(file)
                writer.writerow(['timestamp', 'co2_ppm'])
                
            # If we are creating a new file for a new day, we might want to clear 
            # the history so the chart starts fresh for the day.
            # But keeping a rolling history is visually nicer. We'll leave the rolling history.

    def _load_today_history(self):
        filename = self.get_log_filename()
        if os.path.exists(filename):
            with open(filename, mode='r') as file:
                reader = csv.DictReader(file)
                all_rows = list(reader)
                for row in all_rows[-MAX_POINTS_IN_MEMORY:]:
                    try:
                        self.history.append({
                            'timestamp': row['timestamp'],
                            'co2': int(row['co2_ppm'])
                        })
                    except ValueError:
                        pass # Ignore malformed rows

    def log_reading(self, co2_value):
        now = datetime.now()
        timestamp = now.strftime('%Y-%m-%d %H:%M:%S')
        filename = self.get_log_filename()
        
        self._ensure_file_exists(filename)
        
        # Write to CSV
        with open(filename, mode='a', newline='') as file:
            writer = csv.writer(file)
            writer.writerow([timestamp, co2_value])
            
        # Update in-memory history
        self.history.append({
            'timestamp': timestamp,
            'co2': co2_value
        })
        
        # Trim in-memory history to prevent infinite growth
        if len(self.history) > MAX_POINTS_IN_MEMORY:
            self.history.pop(0)

    def get_history(self):
        return self.history
