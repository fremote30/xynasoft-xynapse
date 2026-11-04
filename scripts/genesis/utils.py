import json
from pathlib import Path
DATA_DIR = Path(__file__).resolve().parent / "data"
def load_json(name):
    with (DATA_DIR / name).open(encoding="utf-8") as f:
        return json.load(f)
def result(created=0, existing=0, skipped=0):
    return {"created": created, "existing": existing, "skipped": skipped}
