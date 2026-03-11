"""Start all 3 agent workers as subprocesses."""
import subprocess
import signal
import sys
import os
import time

WORKERS_DIR = os.path.dirname(os.path.abspath(__file__))
WORKERS = [
    ("text_summarizer.py", 8201),
    ("data_transformer.py", 8202),
    ("code_analyzer.py", 8203),
]

procs = []

def shutdown(sig=None, frame=None):
    print("\nShutting down workers...")
    for p in procs:
        p.terminate()
    for p in procs:
        p.wait(timeout=5)
    print("All workers stopped.")
    sys.exit(0)

signal.signal(signal.SIGINT, shutdown)
signal.signal(signal.SIGTERM, shutdown)

for script, port in WORKERS:
    p = subprocess.Popen(
        [sys.executable, os.path.join(WORKERS_DIR, script)],
        cwd=WORKERS_DIR,
    )
    procs.append(p)
    print(f"Started {script} (PID {p.pid}) on port {port}")

print(f"\n{len(procs)} workers running. Ctrl+C to stop.")

try:
    while True:
        time.sleep(1)
        for p in procs:
            if p.poll() is not None:
                print(f"Worker PID {p.pid} exited with code {p.returncode}")
except KeyboardInterrupt:
    shutdown()
