"""Rules-only microbenchmark on fictional fixture content, not model accuracy."""
import json
import platform
import statistics
import sys
import time
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'backend'))
from app.services.detection import analyze_text, analyze_url

durations = []
for i in range(1000):
    start = time.perf_counter()
    analyze_text('Congratulations! Pay RM50 registration fee immediately to secure your part-time job earning RM500 daily.')
    analyze_url('https://maybank.verify.example.com/login')
    durations.append((time.perf_counter() - start) * 1000)
result = {'scope': '1000 sequential fictional text + URL analysis pairs; excludes HTTP, OCR, database, Telegram and ML', 'python': platform.python_version(), 'platform': platform.system(), 'mean_ms_per_pair': statistics.mean(durations), 'p95_ms_per_pair': sorted(durations)[949], 'iterations': 1000, 'synthetic_inputs': True}
target = Path(__file__).resolve().parents[1] / 'docs' / 'benchmark.json'
target.write_text(json.dumps(result, indent=2), encoding='utf-8')
print(json.dumps(result, indent=2))
