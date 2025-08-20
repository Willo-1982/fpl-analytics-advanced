from __future__ import annotations
import os, json
from typing import Dict, Any

STATE_PATH = "data/user_state/state.json"

def ensure_dirs():
    os.makedirs(os.path.dirname(STATE_PATH), exist_ok=True)

def default_state() -> Dict[str, Any]:
    return {
        "budget": 100.0,
        "bank": 0.0,
        "free_transfers": 1,
        "chip_free_hit_available": True,
        "chip_wildcard_available": True,
        "squad": [],
        "starters": [],
        "captain": None,
        "vice": None,
    }

def load_state() -> Dict[str, Any]:
    ensure_dirs()
    if not os.path.exists(STATE_PATH):
        s = default_state()
        save_state(s)
        return s
    with open(STATE_PATH, "r", encoding="utf-8") as f:
        return json.load(f)

def save_state(s: Dict[str, Any]) -> None:
    ensure_dirs()
    with open(STATE_PATH, "w", encoding="utf-8") as f:
        json.dump(s, f, indent=2)
