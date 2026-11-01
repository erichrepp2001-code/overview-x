#!/usr/bin/env python3
"""Overview X – Terminliste für "Kommende Woche" erzeugen (events.json).

Quellen: offizielle Kalender von Fed, BLS, BEA; feste Regeln für
Options-Verfall (Deribit/CME: letzter Freitag im Monat) und
XRP-Escrow (Ripple: jeweils am Monatsersten).
Bei Terminänderungen hier anpassen und neu ausführen.
"""
import calendar
import json
from datetime import date, datetime, timedelta, timezone
from zoneinfo import ZoneInfo

NY = ZoneInfo("America/New_York")
FED, BLS, BEA = "Federal Reserve", "U.S. Bureau of Labor Statistics", "U.S. Bureau of Economic Analysis"
ev = []


def add(day, hm, title, desc, level, src, tz=NY, coins=None):
    t = datetime.fromisoformat(f"{day}T{hm}").replace(tzinfo=tz)
    ev.append({"t": int(t.timestamp()), "title": title, "desc": desc, "level": level, "src": src, "coins": coins or []})


# Politik
add("2026-11-03", "06:00", "US-Zwischenwahlen (Midterms)",
    "Wahl von Repräsentantenhaus und einem Drittel des Senats. Die Mehrheiten entscheiden mit über Krypto-Gesetze und Regulierung. "
    "Erste Ergebnisse in der Nacht auf Mittwoch, starke Schwankungen möglich.", "hoch", "US-Wahltermin")

# Fed
for d, sep in [("2026-12-09", 1), ("2027-01-27", 0), ("2027-03-17", 1), ("2027-04-28", 0), ("2027-06-09", 1),
               ("2027-07-28", 0), ("2027-09-15", 1), ("2027-10-27", 0), ("2027-12-08", 1)]:
    add(d, "14:00", "Zinsentscheid der US-Notenbank (Fed)",
        "Wichtigster Termin für den Gesamtmarkt. Bitcoin reagiert oft stark auf Zinsentscheid und Pressekonferenz."
        + (" Mit neuer Zinsprognose (Dot Plot)." if sep else ""), "hoch", FED)
add("2026-11-18", "14:00", "Protokoll der letzten Fed-Sitzung",
    "Details zur Zinsdiskussion vom Oktober. Kann Erwartungen an Zinssenkungen verschieben.", "mittel", FED)

# Inflation und Arbeitsmarkt
for d in ["2026-11-10", "2026-12-10", "2027-01-13", "2027-02-11", "2027-03-10", "2027-04-13", "2027-05-12", "2027-06-10",
          "2027-07-14", "2027-08-11", "2027-09-14", "2027-10-14", "2027-11-10", "2027-12-10"]:
    add(d, "08:30", "US-Inflationsdaten (CPI)",
        "Höher als erwartet belastet meist Krypto, niedriger stützt die Hoffnung auf Zinssenkungen.", "hoch", BLS)
for d in ["2026-11-06", "2026-12-04", "2027-01-08", "2027-02-05", "2027-03-05", "2027-04-02", "2027-05-07", "2027-06-04",
          "2027-07-02", "2027-08-06", "2027-09-03", "2027-10-08", "2027-11-05", "2027-12-03"]:
    add(d, "08:30", "US-Arbeitsmarktbericht",
        "Neue Jobs und Arbeitslosenquote. Starke Überraschungen bewegen Dollar, Aktien und Bitcoin.", "hoch", BLS)
for d in ["2026-11-13", "2026-12-15"]:
    add(d, "08:30", "US-Erzeugerpreise (PPI)", "Vorbote der Inflation, meist mit kleinerer Wirkung als CPI.", "mittel", BLS)
for d in ["2026-11-25", "2026-12-23"]:
    add(d, "08:30", "PCE-Inflation und US-Wachstum (BIP)", "Die PCE-Inflation ist das bevorzugte Inflationsmaß der Fed.", "mittel", BEA)

# Krypto-Termine nach festen Regeln
for y, m in [(2026, 11), (2026, 12)] + [(2027, k) for k in range(1, 13)]:
    last = date(y, m, calendar.monthrange(y, m)[1])
    fri = last - timedelta(days=(last.weekday() - 4) % 7)
    quarter = m in (3, 6, 9, 12)
    add(fri.isoformat(), "08:00", ("Großer Quartals-Verfall" if quarter else "Monatlicher Verfall") + " von Bitcoin-Optionen",
        "Optionen und Futures auf Bitcoin und Ether laufen aus (Deribit, CME). Rund um den Termin oft erhöhte Schwankungen."
        + (" Zum Quartalsende besonders großes Volumen." if quarter else ""), "hoch" if quarter else "mittel",
        "Deribit / CME", tz=timezone.utc, coins=["BTC", "ETH"])
    first = date(y, m, 1)
    add(first.isoformat(), "00:00", "XRP-Escrow: monatliche Freigabe",
        "Ripple gibt laut eigenem Treuhand-Plan monatlich XRP aus der Treuhand frei. Ein großer Teil fließt meist zurück, "
        "die Menge wird aber oft beobachtet.", "mittel", "Ripple", tz=timezone.utc, coins=["XRP"])

ev.sort(key=lambda e: e["t"])
with open("events.json", "w", encoding="utf-8") as f:
    json.dump({"note": "Offizielle Kalender (Fed, BLS, BEA) und feste Krypto-Termine. Termine können sich verschieben.", "events": ev},
              f, ensure_ascii=False, indent=1)
print(len(ev), "Termine")
