"""YourTime – config I/O, scheduling, watchdog, AppController.

AppController is the only public API surface consumed by any frontend.
This module has zero imports from frontend.py or any GUI toolkit.
"""
import sys, ctypes, hashlib, json, subprocess, threading, traceback, atexit
from pathlib import Path
from datetime import datetime, timedelta, time as dtime

if getattr(sys, "frozen", False):
    sys.path.insert(0, sys._MEIPASS)

from definitions import (
    APP_NAME, APP_MUTEX, CONFIG_FILENAME, LOG_FILENAME, LOG_MAX_BYTES,
    LANGS, ACTION_KEYS, ACTION_NEXT, DAYS_EN, DEFAULT_CFG,
    DEFAULT_LANG, DEFAULT_ACTION, DEFAULT_DAY_LIMIT_MIN,
    DEFAULT_TAKT_SEC, LANG, UNLIMITED,
    WATCHDOG_SLEEP_GAP_SEC, USAGE_RETENTION_DAYS, REMAINING_MAX_DAYS,
    AUTOSTART_KEY, AUTOSTART_NAME, AUTOSTART_APPROVED_KEY, AUTOSTART_ENABLED_DATA,
)

_cache: dict = {"cfg": {}, "mtime": 0.0}
_cache_lock   = threading.Lock()
_uk: dict     = {"date": "", "key": ""}   # used-key memo

# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _base() -> Path:
    return Path(sys.executable).parent if getattr(sys, "frozen", False) else Path(__file__).parent

def _log(msg: str) -> None:
    try:
        p = _base() / LOG_FILENAME
        if p.exists() and p.stat().st_size > LOG_MAX_BYTES:
            t = p.read_text(encoding="utf-8", errors="replace")
            p.write_text(t[len(t) // 2:], encoding="utf-8")
        with open(p, "a", encoding="utf-8") as f:
            f.write(msg + "\n")
    except Exception:
        pass

# ---------------------------------------------------------------------------
# Autostart
# ---------------------------------------------------------------------------

def _autostart_exe_cmd() -> str:
    if getattr(sys, "frozen", False):
        return '"' + sys.executable + '"'
    return ('"' + str(Path(sys.executable).with_name("pythonw.exe"))
            + '" "' + str(Path(__file__).resolve()) + '"')

def autostart_exists() -> bool:
    try:
        import winreg
        k = winreg.OpenKey(winreg.HKEY_CURRENT_USER, AUTOSTART_KEY, 0, winreg.KEY_READ)
        try:    winreg.QueryValueEx(k, AUTOSTART_NAME); return True
        except OSError: return False
        finally: winreg.CloseKey(k)
    except Exception: return False

def autostart_enabled() -> bool:
    try:
        import winreg
        k = winreg.OpenKey(winreg.HKEY_CURRENT_USER, AUTOSTART_KEY, 0, winreg.KEY_READ)
        try:    winreg.QueryValueEx(k, AUTOSTART_NAME)
        except OSError: return False
        finally: winreg.CloseKey(k)
        try:
            sa = winreg.OpenKey(winreg.HKEY_CURRENT_USER, AUTOSTART_APPROVED_KEY, 0, winreg.KEY_READ)
            try:
                data, _ = winreg.QueryValueEx(sa, AUTOSTART_NAME)
                if isinstance(data, bytes) and len(data) >= 1 and data[0] != 0x02:
                    return False
            except OSError: pass
            finally: winreg.CloseKey(sa)
        except OSError: pass
        return True
    except Exception: return False

def autostart_set(enable: bool) -> None:
    import winreg
    k = winreg.OpenKey(winreg.HKEY_CURRENT_USER, AUTOSTART_KEY, 0, winreg.KEY_SET_VALUE)
    try:
        if enable:
            winreg.SetValueEx(k, AUTOSTART_NAME, 0, winreg.REG_SZ, _autostart_exe_cmd())
        else:
            try: winreg.DeleteValue(k, AUTOSTART_NAME)
            except OSError: pass
    finally: winreg.CloseKey(k)
    if enable:
        try:
            sa = winreg.OpenKey(winreg.HKEY_CURRENT_USER, AUTOSTART_APPROVED_KEY, 0,
                                winreg.KEY_READ | winreg.KEY_SET_VALUE)
            try: winreg.SetValueEx(sa, AUTOSTART_NAME, 0, winreg.REG_BINARY, AUTOSTART_ENABLED_DATA)
            finally: winreg.CloseKey(sa)
        except OSError: pass

# ---------------------------------------------------------------------------
# Config I/O
# ---------------------------------------------------------------------------

def base() -> Path:
    """Public accessor for the base directory (used by frontend for icon paths)."""
    return _base()

def load_cfg() -> dict:
    p = _base() / CONFIG_FILENAME
    try:    mtime = p.stat().st_mtime
    except OSError: mtime = -1.0
    with _cache_lock:
        if 0 < mtime == _cache["mtime"] and _cache["cfg"]:
            return dict(_cache["cfg"])
    if not p.exists():
        cfg = {**DEFAULT_CFG, "allowed_times": [
            {"days": d, "start": "00:00", "end": "00:00",
             "enabled": True, "use_timer": True, "limit_minutes": DEFAULT_DAY_LIMIT_MIN}
            for d in DAYS_EN
        ]}
        save_cfg(cfg)
        return dict(cfg)
    cfg = json.loads(p.read_text(encoding="utf-8"))
    for k in ("target_user", "check_interval_seconds", "extend_seconds", "logout_after_minutes"):
        cfg.pop(k, None)
    with _cache_lock:
        _cache["cfg"] = cfg; _cache["mtime"] = mtime
    return dict(cfg)

def save_cfg(cfg: dict) -> None:
    p = _base() / CONFIG_FILENAME
    p.write_text(json.dumps(cfg, indent=2, ensure_ascii=False), encoding="utf-8")
    try:    mtime = p.stat().st_mtime
    except OSError: mtime = -1.0
    with _cache_lock:
        _cache["cfg"] = dict(cfg); _cache["mtime"] = mtime

def hash_pw(pw: str) -> str:
    return hashlib.sha256(pw.encode()).hexdigest()

def validate_time(s: str) -> bool:
    try: _parse_time(s); return True
    except Exception: return False

# ---------------------------------------------------------------------------
# i18n / formatting
# ---------------------------------------------------------------------------

def t(lang: str, key: str, **kw) -> str:
    tmpl = LANG[lang].get(key, LANG[DEFAULT_LANG].get(key, key))
    return tmpl.format(**kw) if kw else tmpl

def fmt_rem(sec: int, lang: str = DEFAULT_LANG) -> str:
    if sec == UNLIMITED:
        return "\u23f3 \u221e"
    ud, uh, um, us = (LANG[lang][k] for k in ("unit_d", "unit_h", "unit_m", "unit_s"))
    parts = [str(v) + u for v, u in (
        (sec // 86400, ud), (sec % 86400 // 3600, uh), (sec % 3600 // 60, um)) if v]
    return "\u23f3 " + " ".join(parts + ["%02d" % (sec % 60,) + us])

def day_full(lang: str, day_en: str) -> str:
    try: return LANG[lang]["days_full"].split("|")[DAYS_EN.index(day_en)]
    except (ValueError, IndexError): return day_en

def days_short(lang: str) -> list:
    return LANG[lang]["days_short"].split("|")

# ---------------------------------------------------------------------------
# Time helpers
# ---------------------------------------------------------------------------

def _parse_time(s: str) -> tuple:
    parts = s.strip().split(":")
    if len(parts) != 2: raise ValueError(s)
    h, m = int(parts[0]), int(parts[1])
    if not (0 <= h <= 23 and 0 <= m <= 59): raise ValueError(s)
    return h, m

def _day_end_dt(date, end_str: str) -> datetime:
    if end_str == "00:00":
        return datetime.combine(date + timedelta(days=1), dtime.min)
    h, m = _parse_time(end_str)
    return datetime.combine(date, dtime(h, m))

def get_rule(cfg: dict, day_en: str) -> dict | None:
    for r in cfg.get("allowed_times", []):
        d = r.get("days")
        if (isinstance(d, list) and day_en in d) or d == day_en:
            return r
    return None

def day_limit_sec(rule: dict) -> int:
    return int(rule.get("limit_minutes", DEFAULT_DAY_LIMIT_MIN)) * 60

# ---------------------------------------------------------------------------
# Scheduling core
# ---------------------------------------------------------------------------

def _window(rule: dict, date) -> tuple | None:
    s = rule.get("start", "00:00"); e = rule.get("end", "00:00")
    if s == e: return None
    try: sh, sm = _parse_time(s)
    except ValueError: return None
    return (datetime.combine(date, dtime(sh, sm)), _day_end_dt(date, e))

def calc_remaining(cfg: dict, used_today: int, now: datetime | None = None) -> int:
    """Continuous remaining seconds from now through consecutive unblocked periods."""
    if now is None: now = datetime.now()
    MAX = REMAINING_MAX_DAYS * 24 * 3600
    total = 0
    period_end = now

    for i in range(REMAINING_MAX_DAYS + 1):
        date = (now + timedelta(days=i)).date()
        rule = get_rule(cfg, date.strftime("%A"))
        if not rule or not rule.get("enabled", True):
            break
        win       = _window(rule, date)
        use_timer = rule.get("use_timer", True)

        if i > 0:
            allowed_start = win[0] if win is not None else datetime.combine(date, dtime.min)
            if allowed_start > period_end:
                break

        if i == 0:
            if use_timer:
                total += max(0, day_limit_sec(rule) - used_today); break
            elif win is None:
                midnight = datetime.combine(date + timedelta(days=1), dtime.min)
                total += max(0, int((midnight - now).total_seconds()))
                period_end = midnight
            else:
                ws, we = win
                if ws <= now < we: total += max(0, int((we - now).total_seconds()))
                break
        else:
            if use_timer:
                total += day_limit_sec(rule); break
            elif win is None:
                total += 86400
                period_end = datetime.combine(date + timedelta(days=1), dtime.min)
            else:
                ws, we = win
                total += max(0, int((we - ws).total_seconds())); break

        if total > MAX:
            return UNLIMITED
    return total

def should_enforce(cfg: dict, used_today: int, now: datetime | None = None) -> bool:
    """True when the PC must be locked: day-off, outside window, or budget exhausted."""
    if now is None: now = datetime.now()
    rule = get_rule(cfg, now.strftime("%A"))
    if not rule or not rule.get("enabled", True): return True
    win = _window(rule, now.date())
    if win is not None and not (win[0] <= now < win[1]): return True
    if rule.get("use_timer", True):
        return (day_limit_sec(rule) - used_today) <= 0
    return False

# ---------------------------------------------------------------------------
# Persistence – daily usage counter
# ---------------------------------------------------------------------------

def _used_key() -> str:
    d = datetime.now().strftime("%Y-%m-%d")
    if d != _uk["date"]:
        _uk["date"] = d; _uk["key"] = "used_seconds_" + d
    return _uk["key"]

def _cleanup_old_used(cfg: dict) -> None:
    cutoff = (datetime.now() - timedelta(days=USAGE_RETENTION_DAYS)).strftime("%Y-%m-%d")
    for k in [k for k in list(cfg) if k.startswith("used_seconds_") and k[13:] < cutoff]:
        del cfg[k]

def persist_used(used: int) -> None:
    cfg = load_cfg()
    cfg[_used_key()] = max(0, int(used))
    _cleanup_old_used(cfg)
    save_cfg(cfg)

def load_used(cfg: dict) -> int:
    raw = cfg.get(_used_key(), None)
    if raw is None: return 0
    return max(0, int(raw))

# ---------------------------------------------------------------------------
# System actions
# ---------------------------------------------------------------------------

def do_action(action: str) -> None:
    try:
        if action == "lock":     ctypes.windll.user32.LockWorkStation()
        elif action == "logoff": subprocess.run(["shutdown", "/l"], shell=False)
    except Exception: pass

# ---------------------------------------------------------------------------
# Watchdog
# ---------------------------------------------------------------------------

class Watchdog(threading.Thread):
    """Background thread: tracks used time, enforces limits, fires callbacks."""

    def __init__(self, on_trigger, on_warn):
        super().__init__(daemon=True)
        self.on_trigger = on_trigger  # (key: str, action: str) -> None
        self.on_warn    = on_warn     # (minutes: int) -> None
        self.warned     = False
        self.running    = True
        self._lock      = threading.RLock()  # RLock: same thread may re-enter
        self._used:     int  = 0
        self._cfg:      dict = {}
        self._today:    str  = ""
        self._stop_evt       = threading.Event()
        self._save_cd        = 0
        self._countdown: int = -1    # -1=normal, >=0=grace-period ticking to enforcement
        self._offset:    int = 0     # display correction for window-mode days
        self._max_at_start: int = 0

    # --- public API ---------------------------------------------------------

    def get_remaining(self) -> int:
        with self._lock:
            if self._countdown >= 0:
                return self._countdown
            raw = calc_remaining(self._cfg, self._used)
            if raw == UNLIMITED: return UNLIMITED
            return max(0, raw + self._offset)

    def set_used(self, used: int) -> None:
        with self._lock:
            self._used      = max(0, used)
            self._countdown = -1
            self._offset    = 0
            self.warned     = False
            self._stop_evt.set()

    def update(self, cfg: dict) -> None:
        """Push new config; preserve grace-period safety and budget continuity.

        False->True use_timer: discard accumulated non-timer usage so the full
        limit_minutes budget is available immediately.
        Existing timer budget capped to limit (not limit-takt) so the natural
        countdown fires without immediately pinning remaining at takt.
        Any config change that would cause immediate enforcement gets a full
        takt-second grace period.
        """
        takt = max(1, int(cfg.get("takt_seconds", DEFAULT_TAKT_SEC)))
        with self._lock:
            day_now      = datetime.now().strftime("%A")
            old_rule     = get_rule(self._cfg, day_now)
            old_timer_on = bool(old_rule and old_rule.get("use_timer", True))

            self._cfg    = cfg
            self._offset = 0

            rule = get_rule(cfg, day_now)
            if rule and rule.get("enabled", True) and rule.get("use_timer", True):
                limit = day_limit_sec(rule)
                if not old_timer_on:
                    self._used = 0           # fresh budget after timer switched on
                else:
                    self._used = min(self._used, max(0, limit))

            if not should_enforce(cfg, self._used):
                self._countdown = -1
            else:
                self._countdown = takt       # full grace on any config-change enforcement

            raw     = calc_remaining(cfg, 0)
            new_max = REMAINING_MAX_DAYS * 24 * 3600 if raw == UNLIMITED else raw
            if new_max > self._max_at_start:
                self._max_at_start = new_max
            self.warned = False
            self._stop_evt.set()

    def adjust(self, delta: int) -> None:
        with self._lock:
            takt = max(1, int(self._cfg.get("takt_seconds", DEFAULT_TAKT_SEC)))
            rule = get_rule(self._cfg, datetime.now().strftime("%A"))

            if rule and rule.get("use_timer", True):
                limit   = day_limit_sec(rule)
                cur_rem = (self._countdown if self._countdown >= 0
                           else max(0, calc_remaining(self._cfg, self._used)))
                new_rem = min(limit, cur_rem + delta)
                new_rem = max(takt, new_rem)
                if new_rem > limit: return
                self._used   = max(0, limit - new_rem)
                self._offset = 0
            else:
                raw = calc_remaining(self._cfg, self._used)
                if raw == UNLIMITED: return
                max_al = calc_remaining(self._cfg, 0)
                if max_al == UNLIMITED: max_al = REMAINING_MAX_DAYS * 24 * 3600
                cur_eff = (self._countdown if self._countdown >= 0
                           else max(0, raw + self._offset))
                new_rem = min(max_al, cur_eff + delta)
                new_rem = max(takt, new_rem)
                if new_rem > max_al: return
                self._offset = new_rem - raw

            self._countdown = -1
            persist_used(self._used)

    def extend(self, s: int) -> None: self.adjust(+abs(s))
    def reduce(self, s: int) -> None: self.adjust(-abs(s))

    def reset(self) -> None:
        with self._lock:
            raw = calc_remaining(self._cfg, 0)
            self._max_at_start = REMAINING_MAX_DAYS * 24 * 3600 if raw == UNLIMITED else raw
            self.set_used(0)    # RLock: same-thread re-entry safe

    def kick(self) -> None:  self._stop_evt.set()
    def stop(self) -> None:  self.running = False; self._stop_evt.set()

    # --- internals ----------------------------------------------------------

    def _check_day_change(self) -> None:
        today = datetime.now().strftime("%Y-%m-%d")
        if today != self._today:
            self._today = today
            with self._lock:
                self._used      = 0
                self._countdown = -1
                self._offset    = 0
                raw = calc_remaining(self._cfg, 0)
                self._max_at_start = REMAINING_MAX_DAYS * 24 * 3600 if raw == UNLIMITED else raw
                persist_used(0)
                self.warned = False

    def _evaluate(self, takt: int, triggered_by_zero: bool) -> None:
        with self._lock:
            cfg    = self._cfg
            used   = self._used
            offset = self._offset

        if should_enforce(cfg, used):
            if not triggered_by_zero:
                with self._lock:
                    if self._countdown < 0:
                        self._countdown = takt
                return
            with self._lock:
                self._countdown = takt
            action = cfg.get("action", DEFAULT_ACTION)
            rule   = get_rule(cfg, datetime.now().strftime("%A"))
            in_win = True
            if rule:
                win = _window(rule, datetime.now().date())
                if win is not None:
                    in_win = win[0] <= datetime.now() < win[1]
            budget = calc_remaining(cfg, used)
            key    = ("msg_timeout"
                      if (in_win and rule and rule.get("enabled", True) and budget == 0)
                      else "msg_blocked")
            self.on_trigger(key, action)
            return

        raw    = calc_remaining(cfg, used)
        budget = UNLIMITED if raw == UNLIMITED else max(0, raw + offset)
        if budget != UNLIMITED and budget <= takt and not self.warned:
            self.warned = True
            self.on_warn(max(0, budget // 60))
        elif budget == UNLIMITED or budget > takt:
            self.warned = False

    def run(self) -> None:
        cfg  = load_cfg()
        takt = max(1, int(cfg.get("takt_seconds", DEFAULT_TAKT_SEC)))
        with self._lock:
            self._cfg = cfg
            if should_enforce(cfg, self._used) and self._countdown < 0:
                self._countdown = takt
            raw = calc_remaining(cfg, 0)
            self._max_at_start = REMAINING_MAX_DAYS * 24 * 3600 if raw == UNLIMITED else raw
            self._today = datetime.now().strftime("%Y-%m-%d")

        last_tick_time = datetime.now()

        while self.running:
            kicked = self._stop_evt.wait(timeout=1)
            self._stop_evt.clear()
            if not self.running: break
            try:
                now             = datetime.now()
                wall_elapsed    = (now - last_tick_time).total_seconds()
                last_tick_time  = now
                is_sleep_resume = wall_elapsed > WATCHDOG_SLEEP_GAP_SEC

                self._check_day_change()

                with self._lock:
                    _r0 = calc_remaining(self._cfg, 0)
                    if _r0 != UNLIMITED and _r0 > self._max_at_start:
                        self._max_at_start = _r0
                    cfg  = self._cfg
                    takt = max(1, int(cfg.get("takt_seconds", DEFAULT_TAKT_SEC)))

                triggered_by_zero = False

                if not kicked and not is_sleep_resume:
                    if self._countdown > 0:
                        self._countdown -= 1
                        self._save_cd   += 1
                    elif self._countdown == -1:
                        if not should_enforce(cfg, self._used):
                            self._used    += 1
                            self._save_cd += 1
                        else:
                            self._countdown = takt
                    if self._countdown == 0:
                        triggered_by_zero = True
                        self._save_cd     = takt

                if self._save_cd >= takt or kicked:
                    self._save_cd = 0
                    persist_used(self._used)
                    if not kicked:
                        self._evaluate(takt, triggered_by_zero)

            except Exception as ex:
                _log(str(datetime.now()) + ": watchdog: " + str(ex))

# ---------------------------------------------------------------------------
# AppController – public API surface for any frontend
# ---------------------------------------------------------------------------

class AppController:
    """Facade over Watchdog and config I/O.

    Frontend contract:
      1. AppController(on_trigger, on_warn) — callbacks are the only inbound channel.
      2. call start() once; stop() on shutdown.
      3. load() on startup; save(...) on every config change.
      4. State queries: get_remaining(), is_in_warn_zone(), is_login_allowed(), get_cfg().
      5. Never access Watchdog internals directly.
    """

    def __init__(self, on_trigger, on_warn):
        self.wd    = Watchdog(on_trigger=on_trigger, on_warn=on_warn)
        self._cfg: dict = {}

    def start(self) -> None:
        self.wd.start()
        atexit.register(lambda: persist_used(self.wd._used))

    def stop(self) -> None:
        persist_used(self.wd._used)
        self.wd.stop()

    def load(self) -> dict:
        self._cfg = load_cfg()
        with self.wd._lock:
            self.wd._cfg = self._cfg
            raw     = calc_remaining(self._cfg, 0)
            new_max = REMAINING_MAX_DAYS * 24 * 3600 if raw == UNLIMITED else raw
            if new_max > self.wd._max_at_start:
                self.wd._max_at_start = new_max
            self.wd.set_used(load_used(self._cfg))
        return dict(self._cfg)

    def save(self, lang: str, action: str, takt_sec: int,
             day_states: dict, day_starts: dict, day_ends: dict,
             day_timers: dict, day_limits: dict) -> None:
        times = []
        for d in DAYS_EN:
            st = day_states[d]
            s  = "00:00" if st != "range" else day_starts[d]
            e  = "00:00" if st != "range" else day_ends[d]
            times.append({"days": d, "start": s, "end": e,
                          "enabled":       st != "off",
                          "use_timer":     day_timers[d],
                          "limit_minutes": day_limits[d]})
        cfg = load_cfg()
        cfg.update({"takt_seconds": takt_sec, "language": lang,
                    "action": action, "allowed_times": times})
        save_cfg(cfg)
        self._cfg = cfg
        self.wd.update(cfg)

    def reset_timer(self) -> None:
        self._cfg = load_cfg()
        with self.wd._lock:
            self.wd._cfg = self._cfg
        self.wd.reset()

    def get_remaining(self)    -> int:  return self.wd.get_remaining()
    def get_cfg(self)          -> dict: return dict(self._cfg)

    def is_in_warn_zone(self) -> bool:
        takt = max(1, int(self._cfg.get("takt_seconds", DEFAULT_TAKT_SEC)))
        rem  = self.wd.get_remaining()
        return rem != UNLIMITED and rem <= takt

    def is_login_allowed(self) -> bool:
        takt = max(1, int(self._cfg.get("takt_seconds", DEFAULT_TAKT_SEC)))
        rem  = self.wd.get_remaining()
        if rem == UNLIMITED: return True
        return rem > takt

    def extend(self, s: int) -> None: self.wd.extend(s); self.wd.kick()
    def reduce(self, s: int) -> None: self.wd.reduce(s); self.wd.kick()

    def check_password(self, pw: str) -> bool:
        stored = load_cfg().get("password_hash", "")
        return not stored or hash_pw(pw) == stored

    def set_password(self, pw: str) -> None:
        cfg = load_cfg()
        cfg["password_hash"] = hash_pw(pw) if pw else ""
        save_cfg(cfg)

    def has_password(self) -> bool:
        return bool(load_cfg().get("password_hash", ""))

    def set_language(self, lang: str) -> None:
        cfg = load_cfg(); cfg["language"] = lang; save_cfg(cfg)
        self._cfg = cfg
        with self.wd._lock:
            self.wd._cfg = self._cfg

    @staticmethod
    def translate(lang: str, key: str, **kw) -> str:      return t(lang, key, **kw)
    @staticmethod
    def format_remaining(sec: int, lang: str) -> str:      return fmt_rem(sec, lang)
    @staticmethod
    def days_short(lang: str) -> list:                     return days_short(lang)

    @staticmethod
    def format_date(lang: str) -> str:
        now = datetime.now()
        return "\U0001f4c5 " + t(lang, "date_fmt",
                                  day=day_full(lang, now.strftime("%A")),
                                  dt=now.strftime("%H:%M:%S"))

# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main() -> None:
    mutex = ctypes.windll.kernel32.CreateMutexW(None, True, APP_MUTEX)
    if ctypes.windll.kernel32.GetLastError() == 183:
        hwnd = ctypes.windll.user32.FindWindowW(None, APP_NAME)
        if hwnd:
            ctypes.windll.user32.ShowWindow(hwnd, 9)
            ctypes.windll.user32.SetForegroundWindow(hwnd)
        return
    from frontend import App
    App().mainloop()


if __name__ == "__main__":
    try:
        main()
    except Exception:
        tb = traceback.format_exc()
        _log("=== STARTUP CRASH ===\n" + tb)
        try:
            import ctypes as ct
            ct.windll.user32.MessageBoxW(0, tb, APP_NAME + " - Startup Error", 0x10)
        except Exception:
            pass
