@'
# app/state.py
from __future__ import annotations
import json, os, pathlib, streamlit as st

STATE_DIR = pathlib.Path("data/user_state")
STATE_PATH = STATE_DIR / "state.json"

DEFAULT_STATE = {
    "budget": 100.0,
    "bank": 0.0,
    "free_transfers": 1,
    "squad": [],        # list of 15 player ids
    "starters": [],     # list of 11 ids
    "captain": None,
    "vice": None,
}

def _safe_mkdirs():
    STATE_DIR.mkdir(parents=True, exist_ok=True)

def default_state() -> dict:
    return json.loads(json.dumps(DEFAULT_STATE))

def load_state() -> dict:
    _safe_mkdirs()
    if not STATE_PATH.exists():
        save_state(DEFAULT_STATE)
        return default_state()
    try:
        with open(STATE_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
            if not isinstance(data, dict):
                raise ValueError("state.json not a dict")
            # backfill missing keys
            merged = default_state()
            merged.update({k: v for k, v in data.items() if k in merged})
            return merged
    except Exception as e:
        # corrupt or unreadable → reset while keeping a backup
        backup = STATE_PATH.with_suffix(".corrupt.json")
        try:
            os.replace(STATE_PATH, backup)
        except Exception:
            pass
        save_state(DEFAULT_STATE)
        st.warning(f"User state was corrupt and has been reset. A backup (if any) is at: {backup}")
        return default_state()

def save_state(state: dict) -> None:
    _safe_mkdirs()
    tmp = STATE_PATH.with_suffix(".tmp")
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(state, f, ensure_ascii=False, indent=2)
    os.replace(tmp, STATE_PATH)
'@ | Set-Content app\state.py -Encoding UTF8
