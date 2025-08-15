
from __future__ import annotations
import argparse, os, shutil
from utils import read_toml, write_json, utcnow_str
from fpl_client import FPLClient

def save(data, name, cfg):
    ts = utcnow_str(cfg['caching']['timestamp_format'])
    raw = os.path.join(cfg['caching']['raw_dir'], f"{name}_{ts}.json")
    write_json(data, raw)
    if cfg['caching']['write_latest_copies']:
        shutil.copyfile(raw, os.path.join(cfg['caching']['cache_dir'], f"{name}.json"))

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["all"])
    ap.add_argument("--config", default="configs/config.toml")
    args = ap.parse_args()

    cfg = read_toml(args.config)
    cli = FPLClient(timeout=cfg['network']['timeout_seconds'], headers={"User-Agent": cfg['user_agent']['value']})

    if args.cmd == "all":
        print("Fetching bootstrap-static ...")
        b = cli.get_bootstrap(); save(b, "bootstrap-static", cfg)
        print("Fetching fixtures ...")
        f = cli.get_fixtures();   save(f, "fixtures", cfg)
        print("Saved to data/cache/.")

if __name__ == "__main__":
    main()
