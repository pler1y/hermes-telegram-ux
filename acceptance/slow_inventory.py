"""Synthetic slow source used only by the acceptance checklist."""
import csv
import json
from pathlib import Path
import time
time.sleep(20)
with Path(__file__).with_name("inventory.csv").open(encoding="utf-8-sig") as stream:
    print(json.dumps(list(csv.DictReader(stream)), ensure_ascii=False))
