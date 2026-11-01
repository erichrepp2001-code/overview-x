#!/usr/bin/env python3
"""Overview X – News-Sammler.

Liest die offiziellen RSS-Feeds einiger Krypto-Nachrichtenseiten,
fasst Meldungen zum selben Ereignis zusammen, zählt die Quellen,
ordnet Coins zu und schreibt das Ergebnis nach news.json.

Nur Schlagzeile, kurzer Anriss und Link werden übernommen – keine Artikel.
Nutzt nur die Python-Standardbibliothek.
"""
import email.utils
import html
import json
import os
import re
import sys
import time
import urllib.request
import xml.etree.ElementTree as ET

# Reihenfolge = Vorrang, wessen Schlagzeile bei einer Gruppe angezeigt wird
FEEDS = [
    ("CoinDesk", "https://www.coindesk.com/arc/outboundfeeds/rss/"),
    ("The Block", "https://www.theblock.co/rss.xml"),
    ("Cointelegraph", "https://cointelegraph.com/rss"),
    ("Decrypt", "https://decrypt.co/feed"),
    ("Bitcoin Magazine", "https://bitcoinmagazine.com/.rss/full/"),
    ("CryptoSlate", "https://cryptoslate.com/feed/"),
]
UA = "OverviewX-News/1.0 (private dashboard; +https://erichrepp2001-code.github.io/overview-x/)"
MAX_AGE_H = 36
MAX_ITEMS = 8        # nur das Wichtigste
MIN_ITEMS = 4        # falls wenig los ist: mit Einzelmeldungen zu Kern-Coins auffüllen
CORE = {"BTC", "ETH", "SOL", "XRP"}
# Füllmaterial: Rückblicke, Meinungen, Kursprognosen, Werbung
JUNK = re.compile(r"what happened in crypto|price prediction|price analysis|\banalyst says\b|\bopinion\b|op-ed|podcast|newsletter|"
                  r"sponsored|press release|\bhow to\b|\bguide\b|explained|\bweekly\b|\bdaily\b|recap|roundup|\bwhy\b|"
                  r"\bcould\b|\bmight\b|\bhere'?s\b|\bhere’s\b|\?$|\bmemecoin of\b|\bbest crypto\b|\btop \d+\b|\bturns \d+\b|anniversary|birthday", re.I)

# Coin-Erkennung: (Kürzel, CoinGecko-ID, Muster ohne Groß/Klein, Muster mit exakter Schreibweise)
COINS = [
    ("BTC", "bitcoin", r"\bbitcoin", r"\bBTC\b"),
    ("ETH", "ethereum", r"\bethereum|\bether\b", r"\bETH\b"),
    ("SOL", "solana", r"\bsolana", r"\bSOL\b"),
    ("XRP", "ripple", r"\bxrp\b|\bripple\b", None),
    ("LINK", "chainlink", r"\bchainlink", r"\bLINK\b"),
    ("DOT", "polkadot", r"\bpolkadot", r"\bDOT\b"),
    ("XLM", "stellar", r"\bstellar\b|\bxlm\b", None),
    ("ADA", "cardano", r"\bcardano", r"\bADA\b"),
    ("HBAR", "hedera-hashgraph", r"\bhedera|\bhbar\b", None),
    ("AVAX", "avalanche-2", r"\bavalanche\b|\bavax\b", None),
    ("ONDO", "ondo-finance", r"\bondo\b", None),
    ("TAO", "bittensor", r"\bbittensor", r"\bTAO\b"),
]

STOP = set("""a an the and or but of to in on at for from by with as is are was were be been being has have had
it its this that these those into over under after before about amid than then via vs new says said say will would could
may might can just more most less up down out off per not no yes how why what who when where which while week weeks day
days today year years month months first last next top big amid report reports according price prices market markets crypto
cryptocurrency token tokens coin coins news update live billion million trillion""".split())
SYN = {"btc": "bitcoin", "eth": "ethereum", "sol": "solana", "sec's": "sec", "u.s": "us"}


def fetch(url):
    local = os.environ.get("NEWS_LOCAL_DIR")
    if local:  # nur zum Testen
        path = os.path.join(local, re.sub(r"\W+", "_", url) + ".xml")
        with open(path, "rb") as f:
            return f.read()
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": "application/rss+xml, application/xml, text/xml"})
    with urllib.request.urlopen(req, timeout=20) as r:
        return r.read(3_000_000)


def clean(text, limit=None):
    text = html.unescape(re.sub(r"<[^>]+>", " ", text or ""))
    text = re.sub(r"\s+", " ", text).strip()
    if limit and len(text) > limit:
        text = text[:limit].rsplit(" ", 1)[0].rstrip(",.;:") + " …"
    return text


def parse_time(s):
    if not s:
        return None
    try:
        return email.utils.parsedate_to_datetime(s).timestamp()
    except Exception:
        pass
    try:
        from datetime import datetime
        return datetime.fromisoformat(s.replace("Z", "+00:00")).timestamp()
    except Exception:
        return None


def parse_feed(name, raw):
    items = []
    root = ET.fromstring(raw)
    ns = {"a": "http://www.w3.org/2005/Atom"}
    for it in root.iter("item"):
        items.append({
            "title": clean(it.findtext("title")),
            "link": (it.findtext("link") or "").strip(),
            "t": parse_time(it.findtext("pubDate")),
            "teaser": clean(it.findtext("description"), 200),
        })
    for it in root.iter("{http://www.w3.org/2005/Atom}entry"):
        link = it.find("a:link", ns)
        items.append({
            "title": clean(it.findtext("a:title", namespaces=ns)),
            "link": link.get("href") if link is not None else "",
            "t": parse_time(it.findtext("a:published", namespaces=ns) or it.findtext("a:updated", namespaces=ns)),
            "teaser": clean(it.findtext("a:summary", namespaces=ns), 200),
        })
    for i in items:
        i["source"] = name
    return [i for i in items if i["title"] and i["link"].startswith("https://") and i["t"]]


def tokens(title):
    words = re.findall(r"[a-z0-9$%.]+", title.lower())
    out = set()
    for w in words:
        w = w.strip(".")
        w = SYN.get(w, w)
        m = re.fullmatch(r"\$?(\d+(?:\.\d+)?)(?:[kmb]|bn)?", w)
        if m:
            w = m.group(1)
        if w in STOP or (len(w) < 3 and not w[:1].isdigit()):
            continue
        if w.endswith("s") and len(w) > 3 and not w.endswith("ss"):
            w = w[:-1]
        out.add(w)
    return out


def coins_in(text):
    found = []
    for sym, cid, loose, exact in COINS:
        if re.search(loose, text, re.I) or (exact and re.search(exact, text)):
            found.append({"sym": sym, "id": cid})
    return found


def cluster(items):
    groups = []
    for it in sorted(items, key=lambda x: x["t"]):
        tk = tokens(it["title"])
        best, best_score = None, 0
        for g in groups:
            if abs(it["t"] - g["last"]) > 24 * 3600:
                continue
            common = len(tk & g["tokens"])
            score = common / max(1, min(len(tk), len(g["tokens"])))
            if common >= 3 and score >= 0.45 and score > best_score:
                best, best_score = g, score
        if best:
            best["items"].append(it)
            best["tokens"] |= tk
            best["last"] = max(best["last"], it["t"])
        else:
            groups.append({"items": [it], "tokens": set(tk), "last": it["t"]})
    return groups


def main():
    now = time.time()
    items, ok = [], []
    for name, url in FEEDS:
        try:
            got = [i for i in parse_feed(name, fetch(url)) if now - i["t"] < MAX_AGE_H * 3600]
            items += got
            ok.append(name)
            print(f"{name}: {len(got)} Meldungen")
        except Exception as e:  # eine kaputte Quelle darf den Rest nicht stoppen
            print(f"{name}: übersprungen ({e.__class__.__name__}: {e})", file=sys.stderr)

    if not ok:
        print("Keine Quelle erreichbar – news.json bleibt unverändert.", file=sys.stderr)
        return 1

    order = {n: i for i, (n, _) in enumerate(FEEDS)}
    out = []
    for g in cluster(items):
        by_src = {}
        for it in sorted(g["items"], key=lambda x: x["t"]):
            by_src.setdefault(it["source"], it)  # je Quelle nur der früheste Artikel
        main_it = sorted(by_src.values(), key=lambda x: order[x["source"]])[0]
        text = " ".join(i["title"] for i in by_src.values()) + " " + main_it["teaser"]
        coins = coins_in(text)
        n = len(by_src)
        if JUNK.search(main_it["title"]):
            continue
        first = min(i["t"] for i in by_src.values())
        age_h = (now - first) / 3600
        out.append({
            "title": main_it["title"],
            "teaser": main_it["teaser"],
            "link": main_it["link"],
            "t": int(first),
            "sources": [{"name": i["source"], "link": i["link"]} for i in sorted(by_src.values(), key=lambda x: order[x["source"]])],
            "coins": coins,
            "_score": n * 2 + (1.5 if coins else 0) - age_h / 8,
            "_n": n,
            "_core": any(c["sym"] in CORE for c in coins),
        })
    out.sort(key=lambda x: x["_score"], reverse=True)
    confirmed = [o for o in out if o["_n"] >= 2][:MAX_ITEMS]
    if len(confirmed) < MIN_ITEMS:
        confirmed += [o for o in out if o["_n"] < 2 and o["_core"]][:MIN_ITEMS - len(confirmed)]
    out = confirmed
    for o in out:
        for k in ("_score", "_n", "_core"):
            del o[k]
    out.sort(key=lambda x: x["t"], reverse=True)

    data = {"updated": int(now), "feeds": ok, "items": out}
    with open(os.environ.get("NEWS_OUT", "news.json"), "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=1)
    print(f"{len(out)} Meldungen gespeichert aus {len(ok)} Quellen.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
