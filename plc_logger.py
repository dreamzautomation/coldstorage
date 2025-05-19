import snap7
import sqlite3
import time
import json
from datetime import datetime
from snap7.util import get_real, get_bool

# Load tag configuration
with open("tag_config.json") as f:
    config = json.load(f)["tags"]

# Connect to PLC
client = snap7.client.Client()
client.connect("192.168.100.120", 0, 1)

def read_tag(tag):
    try:
        data = client.db_read(tag["db"], tag["start"], 4)
        if tag["type"] == "REAL":
            return round(get_real(data, 0), 2)
        elif tag["type"] == "BOOL":
            return int(get_bool(data, 0, tag["bit"]))
    except Exception as e:
        print(f"Error reading tag {tag['name']}: {e}")
    return None

def check_alarm(tag, value):
    if "alarm_high" in tag and tag["type"] == "REAL":
        return value >= tag["alarm_high"]
    if "alarm_if" in tag and tag["type"] == "BOOL":
        return value == tag["alarm_if"]
    return False

# Create table in normalized form
with sqlite3.connect("data_log.db") as conn:
    conn.execute("""
        CREATE TABLE IF NOT EXISTS logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT,
            name TEXT,
            value REAL,
            alarm INTEGER,
            acknowledged INTEGER
        )
    """)

def log_data():
    while True:
        now = datetime.now().isoformat()

        for tag in config:
            val = read_tag(tag)
            if val is None:
                continue

            alarm = 1 if check_alarm(tag, val) else 0

            with sqlite3.connect("data_log.db") as conn:
                conn.execute("""
                    INSERT INTO logs (timestamp, name, value, alarm, acknowledged)
                    VALUES (?, ?, ?, ?, ?)
                """, (now, tag["name"], val, alarm, 0))

        time.sleep(5)

if __name__ == "__main__":
    log_data()
