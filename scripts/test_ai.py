"""\nTest the 4-model AI pipeline with different sensor scenarios.
Run: venv/Scripts/python.exe scripts/test_ai.py
"""
from app.services.ai_service import ai_service

tests = [
    {"name": "Clean air",    "co_ppm": 0,   "ch4_pct": 0,   "temperature_c": 25, "humidity_pct": 50},
    {"name": "Low CO",       "co_ppm": 30,  "ch4_pct": 0.3, "temperature_c": 26, "humidity_pct": 52},
    {"name": "Warning CO",   "co_ppm": 80,  "ch4_pct": 0.8, "temperature_c": 30, "humidity_pct": 60},
    {"name": "High CO",      "co_ppm": 150, "ch4_pct": 1.2, "temperature_c": 35, "humidity_pct": 65},
    {"name": "Critical CO",  "co_ppm": 250, "ch4_pct": 1.5, "temperature_c": 40, "humidity_pct": 70},
    {"name": "Danger zone",  "co_ppm": 400, "ch4_pct": 3.0, "temperature_c": 50, "humidity_pct": 80},
    {"name": "Max danger",   "co_ppm": 500, "ch4_pct": 5.0, "temperature_c": 55, "humidity_pct": 90},
]

print("=" * 70)
print(f"  AI Models loaded: {ai_service.models_loaded}")
print("=" * 70)
print(f"  {'Scenario':<16} {'CO':>5} {'CH4':>5} {'Temp':>5}  {'Result':<8} {'Votes':>5}  {'Conf':>6}  Model Votes")
print("-" * 70)

for t in tests:
    r = ai_service.run_inference(t)
    mv = r["model_votes"]
    votes_str = f"IF:{mv['isolation_forest'][0].upper()} RF:{mv['random_forest'][0].upper()} LSTM:{mv['lstm'][0].upper()} SVM:{mv['svm'][0].upper()}"
    result = r["prediction"].upper()
    marker = " ⚠" if result == "DANGER" else "  "
    print(f"  {t['name']:<16} {t['co_ppm']:>5} {t['ch4_pct']:>5} {t['temperature_c']:>5}  {result:<8} {r['danger_votes']}/4    {r['confidence']:>5}%  {votes_str}{marker}")

print("=" * 70)
print("  Voting rule: 3-4 votes=DANGER | 0-1 votes=SAFE | 2-2 tie=RF decides (>75%)")
print("=" * 70)
