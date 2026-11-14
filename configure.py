#!/usr/bin/env python3
"""Terminal UI for ~/.config/omarchy/stock-ticker.json: symbols, schedule, alert settings.

Keys: up/down move, Enter edit/open, space toggle, s save, q quit.
Symbols screen: a add (checked against Yahoo), d delete, q back.
Python 3 stdlib only. Other keys in the config file are preserved.
"""
import curses, json, os, urllib.parse, urllib.request

PATH = os.path.expanduser("~/.config/omarchy/stock-ticker.json")
DAYS = ["mon", "tue", "wed", "thu", "fri", "sat", "sun"]
DEFAULT_SCHEDULE = {"start": "06:00", "end": "17:00", "days": DAYS[:5]}


def load():
    try:
        with open(PATH) as f:
            c = json.load(f)
        return c if isinstance(c, dict) else {}
    except Exception:
        return {}


def save(cfg):
    os.makedirs(os.path.dirname(PATH), exist_ok=True)
    tmp = PATH + ".tmp"
    with open(tmp, "w") as f:
        json.dump(cfg, f, indent=2)
        f.write("\n")
    os.replace(tmp, PATH)


def valid_time(s):
    try:
        h, m = s.split(":")
        return 0 <= int(h) < 24 and 0 <= int(m) < 60 and len(m) == 2
    except Exception:
        return False


def norm_time(s):
    h, m = s.strip().split(":")
    return "%02d:%02d" % (int(h), int(m))


def probe(sym):
    """Return (ok, message) by asking Yahoo for the symbol's latest price."""
    try:
        url = "https://query1.finance.yahoo.com/v8/finance/chart/%s?interval=1m&range=1d" % urllib.parse.quote(sym)
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        r = json.load(urllib.request.urlopen(req, timeout=10))["chart"]["result"][0]
        bars = [c for c in r["indicators"]["quote"][0]["close"] if c is not None]
        if not bars:
            return False, "no price data"
        return True, "%s %.2f %s" % (sym, r["meta"]["regularMarketPrice"], r["meta"].get("currency", ""))
    except Exception:
        return False, "not found (Canadian: .TO / .CN suffix)"


class UI:
    def __init__(self, scr):
        self.scr = scr
        self.cfg = load()
        self.cfg.setdefault("symbols", [])
        self.dirty = False
        self.msg = ""
        curses.curs_set(0)
        curses.use_default_colors()

    # -- helpers -----------------------------------------------------------
    def draw(self, title, lines, sel, help_):
        s = self.scr
        s.erase()
        h, w = s.getmaxyx()
        s.addnstr(0, 1, title + ("  [unsaved]" if self.dirty else ""), w - 2, curses.A_BOLD)
        top = max(0, sel - (h - 5)) if sel >= h - 4 else 0
        for i, line in enumerate(lines[top:top + h - 4]):
            attr = curses.A_REVERSE if i + top == sel else 0
            s.addnstr(2 + i, 1, line.ljust(w - 2), w - 2, attr)
        s.addnstr(h - 2, 1, self.msg, w - 2)
        s.addnstr(h - 1, 1, help_, w - 2, curses.A_DIM)
        s.refresh()

    def prompt(self, label, initial=""):
        """Single-line input. Returns the string, or None if cancelled (Esc)."""
        buf = list(initial)
        curses.curs_set(1)
        try:
            while True:
                h, w = self.scr.getmaxyx()
                self.scr.move(h - 3, 0)
                self.scr.clrtoeol()
                self.scr.addnstr(h - 3, 1, label + "".join(buf), w - 2)
                self.scr.refresh()
                k = self.scr.get_wch()
                if k in ("\n", "\r") or k == curses.KEY_ENTER:
                    return "".join(buf).strip()
                if k == "\x1b":
                    return None
                if k in (curses.KEY_BACKSPACE, "\x7f", "\b"):
                    if buf:
                        buf.pop()
                elif isinstance(k, str) and k.isprintable():
                    buf.append(k)
        finally:
            curses.curs_set(0)

    def set_msg(self, m):
        self.msg = m

    # -- screens -----------------------------------------------------------
    def schedule(self):
        return self.cfg.get("schedule") if isinstance(self.cfg.get("schedule"), dict) else None

    def rows(self):
        sch = self.schedule()
        r = [("sched", "Schedule         " + ("ON  (hidden outside the window)" if sch else "OFF (always running)"))]
        if sch:
            r.append(("start", "  Start time     " + str(sch.get("start", "00:00"))))
            r.append(("end", "  End time       " + str(sch.get("end", "24:00"))))
            days = sch.get("days") or DAYS
            r.append(("days", "  Days           " + " ".join(d.capitalize() if d in days else "--" for d in DAYS)))
        r.append(("pct", "Alert percent    %s%%" % self.cfg.get("alertPercent", 5)))
        r.append(("win", "Alert window     %s min" % self.cfg.get("alertWindowMinutes", 15)))
        r.append(("syms", "Symbols          %d  (Enter to edit)" % len(self.cfg["symbols"])))
        return r

    def main(self):
        sel = 0
        while True:
            rows = self.rows()
            sel = min(sel, len(rows) - 1)
            self.draw("Stock Ticker settings  -  " + PATH, [t for _, t in rows], sel,
                      "up/down move   Enter edit   space toggle   s save   q quit")
            self.msg = ""
            k = self.scr.getch()
            key = rows[sel][0]
            if k in (curses.KEY_UP, ord("k")):
                sel = max(0, sel - 1)
            elif k in (curses.KEY_DOWN, ord("j")):
                sel = min(len(rows) - 1, sel + 1)
            elif k == ord("s"):
                save(self.cfg)
                self.dirty = False
                self.set_msg("Saved. The ticker picks it up within a minute.")
            elif k == ord("q"):
                if self.dirty:
                    a = self.prompt("Unsaved changes. Save? (y/n/Esc): ")
                    if a is None:
                        continue
                    if a.lower().startswith("y"):
                        save(self.cfg)
                return
            elif k in (ord(" "), 10, curses.KEY_ENTER):
                self.activate(key)

    def activate(self, key):
        c = self.cfg
        if key == "sched":
            if self.schedule():
                del c["schedule"]
            else:
                c["schedule"] = dict(DEFAULT_SCHEDULE, days=list(DEFAULT_SCHEDULE["days"]))
            self.dirty = True
        elif key in ("start", "end"):
            v = self.prompt("%s time (HH:MM, 24h): " % key.capitalize(), str(self.schedule().get(key, "")))
            if v is None:
                return
            if valid_time(v):
                self.schedule()[key] = norm_time(v)
                self.dirty = True
            else:
                self.set_msg("Invalid time %r - use HH:MM, e.g. 06:00" % v)
        elif key == "days":
            self.days()
        elif key in ("pct", "win"):
            name = "alertPercent" if key == "pct" else "alertWindowMinutes"
            v = self.prompt("%s: " % name, str(c.get(name, 5 if key == "pct" else 15)))
            if v is None:
                return
            try:
                n = float(v)
                assert n > 0
                c[name] = int(n) if n == int(n) else n
                self.dirty = True
            except Exception:
                self.set_msg("Enter a number greater than 0")
        elif key == "syms":
            self.symbols()

    def days(self):
        sch = self.schedule()
        days = list(sch.get("days") or DAYS)
        sel = 0
        while True:
            lines = ["[%s] %s" % ("x" if d in days else " ", d.capitalize()) for d in DAYS]
            self.draw("Days the ticker runs", lines, sel, "up/down move   space toggle   q/Enter done")
            k = self.scr.getch()
            if k in (curses.KEY_UP, ord("k")):
                sel = max(0, sel - 1)
            elif k in (curses.KEY_DOWN, ord("j")):
                sel = min(6, sel + 1)
            elif k == ord(" "):
                d = DAYS[sel]
                days = [x for x in days if x != d] if d in days else [x for x in DAYS if x in days or x == d]
                sch["days"] = days
                self.dirty = True
            elif k in (ord("q"), 10, curses.KEY_ENTER, 27):
                if not days:
                    self.set_msg("No days selected - the ticker would never run")
                    sch["days"] = list(DEFAULT_SCHEDULE["days"])
                return

    def symbols(self):
        syms = self.cfg["symbols"]
        sel = 0
        while True:
            sel = min(sel, max(0, len(syms) - 1))
            self.draw("Symbols (%d)" % len(syms), syms or ["(empty - the built-in default list is used)"], sel,
                      "a add   d delete   up/down move   q back")
            self.msg = ""
            k = self.scr.getch()
            if k in (curses.KEY_UP, ord("k")):
                sel = max(0, sel - 1)
            elif k in (curses.KEY_DOWN, ord("j")):
                sel = min(max(0, len(syms) - 1), sel + 1)
            elif k == ord("d") and syms:
                self.set_msg("Removed " + syms.pop(sel))
                self.dirty = True
            elif k == ord("a"):
                v = self.prompt("Add symbol(s), space/comma separated: ")
                if not v:
                    continue
                added, bad = [], []
                for s in v.replace(",", " ").split():
                    s = s.upper()
                    if s in syms or s in added:
                        continue
                    self.set_msg("Checking %s ..." % s)
                    ok, m = probe(s)
                    self.draw("Symbols (%d)" % len(syms), syms, sel, "")
                    (added if ok else bad).append(s if ok else "%s: %s" % (s, m))
                syms.extend(added)
                if added:
                    self.dirty = True
                self.set_msg(("Added %s. " % ", ".join(added) if added else "") + ("Rejected " + "; ".join(bad) if bad else ""))
            elif k in (ord("q"), 27):
                return


def main():
    curses.wrapper(lambda scr: UI(scr).main())


if __name__ == "__main__":
    main()
