# Overview X – Hinweise für Claude

- Nutzer: Herr Repp, Coding-Einsteiger. Auf Deutsch, Schritt für Schritt, mit "Sie".
- Seite: eine einzige `index.html` (GitHub Pages, https://erichrepp2001-code.github.io/overview-x/), mobil zuerst, Farbschema "Mitternacht".
- **Bei jeder Änderung an `index.html` den Wert in `<meta name="ox-build" content="JJJJMMTTHHMM">` hochzählen.** Die Seite vergleicht ihn beim Öffnen und lädt sich sonst nicht neu (iPhone-Home-Bildschirm hält alte Versionen fest).
- Daten: CoinGecko (Kurse, ohne Schlüssel), alternative.me (Fear & Greed), Binance-Marktdaten (Wochenkerzen für 6M/5Y), FRED (Weltmärkte, `scripts/collect_markets.py`), RSS-Feeds (News, `scripts/collect_news.py`), feste Termine (`scripts/make_events.py` -> `events.json`).
- GitHub Actions schreiben `news.json` und `markets.json`; vor dem Push immer `git fetch` + `rebase`.
- Grundsätze: legal, sicher, kostenlos (Kosten nur nach ausdrücklicher Zustimmung), keine Schlüssel im öffentlichen Code, keine automatischen Trades.
