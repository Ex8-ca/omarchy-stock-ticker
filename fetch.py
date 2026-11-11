#!/usr/bin/env python3
"""Print a JSON list [{s, p, d5, pct5, pctw, alert}] per symbol: price, move over the last 5 minutes,
and the move over the alert window (default 15 min) with alert=true when |pctw| >= threshold (default 5%).

Feed: Yahoo Finance's public 1-minute chart endpoint (no API key, unofficial, may change).
Config (optional): ~/.config/omarchy/stock-ticker.json
  {"symbols": ["AAPL", ...], "alertPercent": 5, "alertWindowMinutes": 15}
"""
import json, os, urllib.parse, urllib.request
from concurrent.futures import ThreadPoolExecutor

DEFAULT = ["AAPL", "MSFT", "NVDA", "GOOGL", "AMZN", "META", "TSLA", "AVGO", "AMD", "NFLX",
           "JPM", "V", "WMT", "COST", "XOM", "SPY", "QQQ"]

def config():
    try:
        with open(os.path.expanduser("~/.config/omarchy/stock-ticker.json")) as f:
            c = json.load(f)
        return c if isinstance(c, dict) else {}
    except Exception:
        return {}

def number(v, default):
    try:
        v = float(v)
        return v if v > 0 else default
    except (TypeError, ValueError):
        return default

CFG = config()
ALERT_PCT = number(CFG.get("alertPercent"), 5.0)
ALERT_WIN = number(CFG.get("alertWindowMinutes"), 15.0) * 60

def symbols():
    s = CFG.get("symbols")
    if isinstance(s, list) and s:
        return [str(x).upper() for x in s][:100]
    return DEFAULT

def quote(sym):
    try:
        url = "https://query1.finance.yahoo.com/v8/finance/chart/%s?interval=1m&range=1d" % urllib.parse.quote(sym)
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        r = json.load(urllib.request.urlopen(req, timeout=15))["chart"]["result"][0]
        pts = [(t, c) for t, c in zip(r["timestamp"], r["indicators"]["quote"][0]["close"]) if c is not None]
        last_t, last = pts[-1]
        ref = next((c for t, c in reversed(pts) if t <= last_t - 300), pts[0][1])
        d = last - ref
        refw = next((c for t, c in reversed(pts) if t <= last_t - ALERT_WIN), pts[0][1])
        pctw = (last - refw) / refw * 100 if refw else 0
        return {"s": sym, "p": round(last, 2), "d5": round(d, 2), "pct5": round(d / ref * 100, 3) if ref else 0,
                "pctw": round(pctw, 3), "win": round(ALERT_WIN / 60), "alert": abs(pctw) >= ALERT_PCT}
    except Exception:
        return None

with ThreadPoolExecutor(8) as ex:
    print(json.dumps([q for q in ex.map(quote, symbols()) if q]))
