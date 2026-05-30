"""Run the full mock roaming billing validation pipeline."""

import subprocess
import sys

steps = [
    [sys.executable, "src/validator.py"],
    [sys.executable, "src/reconcile.py"],
    [sys.executable, "src/generate_report.py"],
]

for step in steps:
    print("\nRunning:", " ".join(step))
    subprocess.run(step, check=True)

print("\nDone. Check the reports/ folder.")
