
from __future__ import annotations
import json, os
from datetime import datetime, timezone
def utcnow_str(fmt="%Y-%m-%dT%H-%M-%SZ"): return datetime.now(timezone.utc).strftime(fmt)
def write_json(obj, path): os.makedirs(os.path.dirname(path), exist_ok=True); open(path,"w",encoding="utf-8").write(json.dumps(obj, ensure_ascii=False, indent=2))
def read_toml(path):
    try: import tomllib
    except ModuleNotFoundError: import tomli as tomllib
    with open(path,"rb") as f: return tomllib.load(f)
