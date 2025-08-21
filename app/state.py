# app/state.py
from __future__ import annotations
import json
from pathlib import Path
from typing import Dict, Any

STATE_PATH = Path("data/user_state/state.json")

def default_state() -> Dict[str, Any]:
    return {
        "budget": 100.0,
        "bank": 0.0,
        "free_transfers": 1,
        "squad": [],     # 15 player ids
        "starters": [],  # 11 player ids
        "captain": None,
        "vice": None,
    }

def load_state() -> Dict[str, Any]:
    """Load state from disk; if missing or invalid, return defaults."""
    try:
        if STATE_PATH.exists():
            with STATE_PATH.open("r", encoding="utf-8") as f:
                data = json.load(f)
            # coerce types & fill missing keys
            base = default_state()
            base.update(data if isinstance(data, dict) else {})
            # ensure shapes
            base["budget"] = float(base.get("budget", 100.0))
            base["bank"] = float(base.get("bank", 0.0))
            base["free_transfers"] = int(base.get("free_transfers", 1))
            base["squad"] = [int(x) for x in (base.get("squad") or [])]
            base["starters"] = [int(x) for x in (base.get("starters") or [])]
            base["captain"] = None if base.get("captain") in ("", None) else int(base["captain"])
            base["vice"] = None if base.get("vice") in ("", None) else int(base["vice"])
            return base
    except Exception:
        # corrupt file; fall through to defaults
        pass
    return default_state()

def save_state(state: Dict[str, Any]) -> None:
    """Persist state to disk (pretty JSON)."""
    STATE_PATH.parent.mkdir(parents=True, exist_ok=True)
    with STATE_PATH.open("w", encoding="utf-8") as f:
        json.dump(state, f, ensure_ascii=False, indent=2)

