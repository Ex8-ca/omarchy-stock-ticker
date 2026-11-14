# Stock Ticker

A scrolling stock ticker docked just under the Omarchy bar. Each symbol shows its price and a green ▲ / red ▼ with the move over the last 5 minutes. Colors and font follow your Omarchy theme.

## Install

```sh
omarchy plugin add https://github.com/ex8-ca/omarchy-stock-ticker.git --enable
```

## Configure

Optional `~/.config/omarchy/stock-ticker.json` (default is a list of ~17 large caps and ETFs):

```json
{ "symbols": ["AAPL", "NVDA", "TSLA", "SPY"] }
```

Quotes refresh every 60 seconds.

## Settings UI

A terminal UI edits the symbol list, schedule and alert settings, so you don't have to touch the JSON:

```sh
python3 ~/.local/share/omarchy/plugins/stock-ticker/configure.py   # path of your install/clone
# or, in a floating Omarchy terminal:
omarchy-launch-tui python3 /path/to/configure.py
```

Arrow keys to move, Enter/space to edit or toggle, `s` to save, `q` to quit. In the symbols list, `a` adds (each symbol is checked against Yahoo first) and `d` deletes. Other keys in the config file are preserved. Changes apply within a minute.

## Schedule

By default the ticker runs all the time. To show it only at certain times, add a `schedule` (system local time, 24-hour). Outside the window the strip is hidden and no requests are made:

```json
{ "schedule": { "start": "06:00", "end": "17:00", "days": ["mon", "tue", "wed", "thu", "fri"] } }
```

`days` defaults to every day, `start`/`end` to the whole day; `start` later than `end` means an overnight window. The schedule is checked on each 60-second refresh, so changes take effect within a minute.

## Move alerts

If a symbol moves 5% or more over a 15-minute window (up or down), its entry in the strip flashes green/red and shows `⚠ +5.3% / 15m`. Tune it in the same config file:

```json
{ "alertPercent": 5, "alertWindowMinutes": 15 }
```

With reduced motion enabled in your theme the highlight stays steady instead of flashing.

## Data source and privacy

Quotes come from Yahoo Finance's public, unofficial chart endpoint (no API key), one request per symbol per minute, from `fetch.py` (Python 3 stdlib only). Data may be delayed and the endpoint can change or rate-limit. Outside market hours the arrows show the move across the last 5 minutes of the most recent session. Not financial advice.

Alpha Vantage's free tier (25 requests/day) is too small for per-minute multi-symbol updates, so it is not used.

## Remove

```sh
omarchy plugin remove io.github.ex8-ca.stock-ticker
```
