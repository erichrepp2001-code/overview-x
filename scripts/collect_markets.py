#!/usr/bin/env python3
"""Overview X – Weltmärkte.

Lädt Tagesschlusskurse aus der öffentlichen Datenbank FRED
(Federal Reserve Bank of St. Louis, CSV-Download ohne Schlüssel)
und schreibt Kurs und Veränderungen nach markets.json.
Nur Python-Standardbibliothek.
"""
import csv
import io
import json
import os
import sys
import time
import urllib.request
from datetime import date, timedelta

SERIES = {
    "nasdaq": "NASDAQ100",     # Nasdaq-100, Punkte
    "sp": "SP500",             # S&P 500, Punkte
    "oil": "DCOILBRENTEU",     # Brent-Rohöl, US-Dollar je Barrel
}
URL = "https://fred.stlouisfed.org/graph/fredgraph.csv?id={id}&cosd={start}"
UA = "OverviewX-Markets/1.0 (private dashboard; +https://erichrepp2001-code.github.io/overview-x/)"


def load(series_id):
    start = (date.today() - timedelta(days=5 * 366 + 10)).isoformat()
    req = urllib.request.Request(URL.format(id=series_id, start=start), headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=30) as r:
        text = r.read().decode("utf-8")
    rows = []
    for row in csv.reader(io.StringIO(text)):
        if len(row) < 2 or row[1] in ("", ".") or not row[0][:1].isdigit():
            continue
        rows.append((date.fromisoformat(row[0]), float(row[1])))
    return rows


def change_since(rows, days):
    """Veränderung in % gegenüber dem letzten Kurs, der mindestens `days` Tage alt ist."""
    last_d, last_v = rows[-1]
    target = last_d - timedelta(days=days)
    for d, v in reversed(rows):
        if d <= target:
            return round((last_v / v - 1) * 100, 2)
    return None


def main():
    out, ok = {}, 0
    for key, sid in SERIES.items():
        try:
            rows = load(sid)
            if len(rows) < 2:
                raise ValueError("zu wenige Daten")
            d, v = rows[-1]
            out[key] = {
                "value": v,
                "date": d.isoformat(),
                "d1": round((v / rows[-2][1] - 1) * 100, 2),
                "d7": change_since(rows, 7),
                "m1": change_since(rows, 30),
                "m6": change_since(rows, 182),
                "y1": change_since(rows, 365),
                "y5": change_since(rows, 5 * 365),
                "spark": [x[1] for x in rows[-60:]],
            }
            ok += 1
            print(f"{key}: {v} ({d})")
        except Exception as e:
            print(f"{key}: übersprungen ({e.__class__.__name__}: {e})", file=sys.stderr)
    if not ok:
        print("Keine Daten – markets.json bleibt unverändert.", file=sys.stderr)
        return 1
    path = os.environ.get("MARKETS_OUT", "markets.json")
    try:  # fehlende Werte vom letzten Mal behalten
        with open(path, encoding="utf-8") as f:
            old = json.load(f).get("data", {})
        for k, v in old.items():
            out.setdefault(k, v)
    except Exception:
        pass
    with open(path, "w", encoding="utf-8") as f:
        json.dump({"updated": int(time.time()), "source": "FRED, Federal Reserve Bank of St. Louis", "data": out}, f, indent=1)
    return 0


if __name__ == "__main__":
    sys.exit(main())
