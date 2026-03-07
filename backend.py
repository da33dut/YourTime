"""YourTime backend – config I/O, scheduling logic, watchdog, AppController."""

import sys, os, traceback
from pathlib import Path

if getattr(sys, "frozen", False):
    sys.path.insert(0, sys._MEIPASS)

def _base() -> Path:
    return Path(sys.executable).parent if getattr(sys, "frozen", False) else Path(__file__).parent

def _log(msg: str) -> None:
    try:
        p = _base() / "error.log"
        if p.exists() and p.stat().st_size > 100_000:
            t = p.read_text(encoding="utf-8", errors="replace")
            p.write_text(t[len(t) // 2:], encoding="utf-8")
        with open(p, "a", encoding="utf-8") as f:
            f.write(msg + "\n")
    except Exception:
        pass

try:
    import ctypes, hashlib, json, subprocess, threading
    from datetime import datetime, timedelta, time as dtime

    from definitions import (
        LANGS, ACTION_KEYS, ACTION_NEXT, DAYS_EN, DEFAULT_CFG,
        DEFAULT_LANG, DEFAULT_ACTION, DEFAULT_DAY_LIMIT_MIN,
        LANG, UNLIMITED,
        AUTOSTART_KEY, AUTOSTART_NAME, AUTOSTART_APPROVED_KEY, AUTOSTART_ENABLED_DATA,
    )

    _cache: dict = {"cfg": {}, "mtime": 0.0}
    _cache_lock = threading.Lock()
    _rk: dict = {"date": "", "key": ""}

    # --- autostart -----------------------------------------------------------

    def _autostart_exe_cmd() -> str:
        if getattr(sys, "frozen", False):
            return f'"{sys.executable}"'
        return f'"{Path(sys.executable).with_name("pythonw.exe")}" "{Path(__file__).resolve()}"'

    def autostart_exists() -> bool:
        try:
            import winreg
            k = winreg.OpenKey(winreg.HKEY_CURRENT_USER, AUTOSTART_KEY, 0, winreg.KEY_READ)
            try: winreg.QueryValueEx(k, AUTOSTART_NAME); return True
            except OSError: return False
            finally: winreg.CloseKey(k)
        except Exception: return False

    def autostart_enabled() -> bool:
        try:
            import winreg
            k = winreg.OpenKey(winreg.HKEY_CURRENT_USER, AUTOSTART_KEY, 0, winreg.KEY_READ)
            try: winreg.QueryValueEx(k, AUTOSTART_NAME)
            except OSError: return False
            finally: winreg.CloseKey(k)
            try:
                sa = winreg.OpenKey(winreg.HKEY_CURRENT_USER, AUTOSTART_APPROVED_KEY,
                                    0, winreg.KEY_READ)
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
                sa = winreg.OpenKey(winreg.HKEY_CURRENT_USER, AUTOSTART_APPROVED_KEY,
                                    0, winreg.KEY_READ | winreg.KEY_SET_VALUE)
                try:
                    winreg.SetValueEx(sa, AUTOSTART_NAME, 0, winreg.REG_BINARY,
                                      AUTOSTART_ENABLED_DATA)
                finally: winreg.CloseKey(sa)
            except OSError: pass

    # --- base / config -------------------------------------------------------

    def base() -> Path: return _base()

    def load_cfg() -> dict:
        p = base() / "config.json"
        try: mtime = p.stat().st_mtime
        except OSError: mtime = -1.0
        with _cache_lock:
            if 0 < mtime == _cache["mtime"] and _cache["cfg"]:
                return dict(_cache["cfg"])
        if not p.exists():
            cfg = {**DEFAULT_CFG, "allowed_times": [
                {"days": d, "start": "00:00", "end": "00:00",
                 "enabled": True, "use_timer": True,
                 "limit_minutes": DEFAULT_DAY_LIMIT_MIN}
                for d in DAYS_EN
            ]}
            save_cfg(cfg); return dict(cfg)
        cfg = json.loads(p.read_text(encoding="utf-8"))
        with _cache_lock:
            _cache["cfg"] = cfg; _cache["mtime"] = mtime
        return dict(cfg)

    def save_cfg(cfg: dict) -> None:
        p = base() / "config.json"
        p.write_text(json.dumps(cfg, indent=2, ensure_ascii=False), encoding="utf-8")
        try: mtime = p.stat().st_mtime
        except OSError: mtime = -1.0
        with _cache_lock:
            _cache["cfg"] = dict(cfg); _cache["mtime"] = mtime

    def hash_pw(pw: str) -> str: return hashlib.sha256(pw.encode()).hexdigest()
    def current_user() -> str: return os.getenv("USERNAME", "").strip()

    def t(lang: str, key: str, **kw) -> str:
        tmpl = LANG[lang].get(key, LANG[DEFAULT_LANG].get(key, key))
        return tmpl.format(**kw) if kw else tmpl

    def fmt_rem(sec: int, lang: str = DEFAULT_LANG) -> str:
        if sec == UNLIMITED: return "\u23f3 \u221e"
        ud, uh, um, us = (LANG[lang][k] for k in ("unit_d","unit_h","unit_m","unit_s"))
        parts = [str(v)+u for v,u in
                 ((sec//86400,ud),(sec%86400//3600,uh),(sec%3600//60,um)) if v]
        return "\u23f3 " + " ".join(parts + ["%02d"%(sec%60,)+us])

    def day_full(lang: str, day_en: str) -> str:
        try: return LANG[lang]["days_full"].split("|")[DAYS_EN.index(day_en)]
        except (ValueError, IndexError): return day_en

    def days_short(lang: str) -> list:
        return LANG[lang]["days_short"].split("|")

    # --- time helpers --------------------------------------------------------

    def _parse_time(s: str) -> tuple:
        parts = s.strip().split(":")
        if len(parts) != 2: raise ValueError(s)
        h, m = int(parts[0]), int(parts[1])
        if not (0 <= h <= 23 and 0 <= m <= 59): raise ValueError(s)
        return h, m

    def validate_time(s: str) -> bool:
        try: _parse_time(s); return True
        except Exception: return False

    # --- persistence helpers -------------------------------------------------

    def _rem_key() -> str:
        d = datetime.now().strftime("%Y-%m-%d")
        if d != _rk["date"]: _rk["date"] = d; _rk["key"] = "remaining_seconds_" + d
        return _rk["key"]

    def _cleanup_old_rem(cfg: dict) -> None:
        cutoff = (datetime.now() - timedelta(days=30)).strftime("%Y-%m-%d")
        for k in [k for k in list(cfg)
                  if k.startswith("remaining_seconds_") and k[18:] < cutoff]:
            del cfg[k]

    def persist_remaining(rem: int) -> None:
        cfg = load_cfg(); key = _rem_key()
        cfg.pop(key, None) if rem == UNLIMITED else cfg.update({key: max(0, int(rem))})
        _cleanup_old_rem(cfg); save_cfg(cfg)

    def do_action(action: str) -> None:
        try:
            if action == "lock": ctypes.windll.user32.LockWorkStation()
            elif action == "logoff": subprocess.run(["shutdown", "/l"], shell=False)
        except Exception: pass

    # --- scheduling ----------------------------------------------------------

    def _day_end_dt(date, end_str: str) -> datetime:
        if end_str == "00:00":
            return datetime.combine(date + timedelta(days=1), dtime.min)
        h, m = _parse_time(end_str)
        return datetime.combine(date, dtime(h, m))

    def get_rule(cfg: dict, day_en: str):
        for r in cfg.get("allowed_times", []):
            d = r.get("days")
            if (isinstance(d, list) and day_en in d) or d == day_en: return r
        return None

    def day_limit_sec(rule: dict) -> int:
        return int(rule.get("limit_minutes", DEFAULT_DAY_LIMIT_MIN)) * 60

    def is_allowed(cfg: dict) -> bool:
        now = datetime.now()
        rule = get_rule(cfg, now.strftime("%A"))
        if not rule or not rule.get("enabled", True): return False
        s, e = rule.get("start","00:00"), rule.get("end","00:00")
        if s == e: return True
        try:
            hs, ms = _parse_time(s)
            return datetime.combine(now.date(), dtime(hs, ms)) <= now < _day_end_dt(now.date(), e)
        except ValueError: return False

    def calc_remaining_sec(cfg: dict, stored_rem: int, now=None) -> int:
        now = now or datetime.now()
        if not is_allowed(cfg): return stored_rem
        accumulated = 0
        for i in range(8):
            dt = now + timedelta(days=i)
            rule = get_rule(cfg, dt.strftime("%A"))
            if not rule or not rule.get("enabled", True):
                return accumulated if accumulated > 0 else UNLIMITED
            s, e = rule.get("start","00:00"), rule.get("end","00:00")
            use_timer = rule.get("use_timer", True)
            limit = day_limit_sec(rule)
            is_full = (s == e)
            if i == 0:
                if not is_full:
                    try: end_dt = _day_end_dt(dt.date(), e)
                    except ValueError: return accumulated if accumulated > 0 else UNLIMITED
                    if now >= end_dt: continue
                    secs = max(0, int((end_dt - now).total_seconds()))
                else:
                    secs = max(0, int((_day_end_dt(dt.date(),"00:00") - now).total_seconds()))
            else:
                if not is_full:
                    try: hhe, mme = _parse_time(e)
                    except ValueError: return accumulated if accumulated > 0 else UNLIMITED
                    secs = hhe*3600 + mme*60
                    return accumulated + (min(stored_rem, min(secs, limit)) if use_timer else secs)
                secs = 86400
            if use_timer:
                return accumulated + min(stored_rem, min(secs, limit))
            if is_full: accumulated += secs
            else: return accumulated + secs
        return UNLIMITED

    def _today_limit(cfg: dict) -> int:
        rule = get_rule(cfg, datetime.now().strftime("%A"))
        return day_limit_sec(rule) if rule else DEFAULT_DAY_LIMIT_MIN * 60

    def initial_remaining(cfg: dict) -> int:
        takt = max(1, int(cfg.get("takt_seconds", 30)))
        limit = _today_limit(cfg)
        stored = cfg.get(_rem_key())
        return calc_remaining_sec(
            cfg, limit if stored is None else max(takt, min(int(stored), limit)))

    def reset_remaining(cfg: dict) -> int:
        if not is_allowed(cfg):
            return max(1, int(cfg.get("takt_seconds", 30)))
        return calc_remaining_sec(cfg, _today_limit(cfg))

    # --- watchdog ------------------------------------------------------------

    class Watchdog(threading.Thread):
        """
        Background thread enforcing daily time limits.

        Loop runs every 1 second:
          - decrement RS by 1
          - check allowed-state transition (max 1s latency)
          - every takt_seconds: persist to disk + check warn/trigger threshold
        """

        def __init__(self, on_trigger, on_warn):
            super().__init__(daemon=True)
            self.on_trigger = on_trigger; self.on_warn = on_warn
            self.warned = False; self.running = True
            self._lock = threading.Lock()
            self._remaining = UNLIMITED; self._was_allowed = None
            self._stop_evt = threading.Event()
            self._save_cd = 0          # counts up to takt_seconds
            self._just_acted = False

        def get_remaining(self) -> int:
            with self._lock: return self._remaining

        def set_remaining(self, rem: int) -> None:
            with self._lock:
                self._remaining = rem; self.warned = False
            self._save_cd = 0          # force persist on next tick
            persist_remaining(rem)

        def clamp_to_takt(self, cfg: dict) -> None:
            self.set_remaining(max(1, int(cfg.get("takt_seconds", 30))))

        def adjust(self, delta: int) -> None:
            cfg = load_cfg(); limit = _today_limit(cfg)
            takt = max(1, int(cfg.get("takt_seconds", 30)))
            with self._lock:
                if self._remaining == UNLIMITED: return
                self._remaining = max(takt, min(self._remaining + delta, limit))
                self.warned = False
            persist_remaining(self._remaining)

        def extend(self, s: int) -> None: self.adjust(+abs(s))
        def reduce(self, s: int)  -> None: self.adjust(-abs(s))
        def kick(self) -> None: self._stop_evt.set()
        def stop(self) -> None: self.running = False; self._stop_evt.set()

        def _tick_rs(self) -> None:
            """Decrement RS by 1 every second."""
            with self._lock:
                if self._remaining not in (UNLIMITED, 0):
                    self._remaining -= 1

        def _check_transition(self, cfg: dict) -> bool:
            """
            Detect allowed-state change every second.
            Returns True if a transition just occurred (caller should skip
            the normal warn/trigger check this cycle to avoid false alarms).
            """
            allowed = is_allowed(cfg)
            if self._was_allowed is None:
                self._was_allowed = allowed
                if not allowed: self.clamp_to_takt(cfg)
                return True
            if allowed == self._was_allowed:
                return False
            # --- transition detected ---
            self._was_allowed = allowed
            if not allowed:
                self.clamp_to_takt(cfg)
            else:
                # Entered allowed window: re-evaluate RS from full daily limit
                self.set_remaining(calc_remaining_sec(cfg, _today_limit(cfg)))
            return True  # skip warn/trigger this cycle

        def _evaluate_warn_trigger(self, cfg: dict, takt: int) -> None:
            """Check warn threshold and trigger action. Called every takt seconds."""
            user = cfg.get("target_user", "").lower().strip()
            if not (user and current_user().lower() == user): return
            allowed = is_allowed(cfg); action = cfg.get("action", DEFAULT_ACTION)
            rem = self.get_remaining()
            if rem == 0:
                self._just_acted = True
                self.on_trigger("msg_timeout" if allowed else "msg_blocked", action)
                return
            if rem != UNLIMITED and rem <= takt and not self.warned:
                self.warned = True; self.on_warn(max(0, rem // 60))
            elif rem == UNLIMITED or rem > takt:
                self.warned = False

        def run(self) -> None:
            cfg = load_cfg()
            takt = max(1, int(cfg.get("takt_seconds", 30)))
            while self.running:
                self._stop_evt.wait(timeout=1)
                kicked = self._stop_evt.is_set(); self._stop_evt.clear()
                if not self.running: break
                try:
                    if self._just_acted:
                        self._just_acted = False
                        cfg = load_cfg()
                        takt = max(1, int(cfg.get("takt_seconds", 30)))
                        persist_remaining(0); self.clamp_to_takt(cfg)
                        self._save_cd = 0
                        continue

                    # reload config every takt seconds or on kick
                    self._save_cd += 1
                    if self._save_cd >= takt or kicked:
                        self._save_cd = 0
                        cfg = load_cfg()
                        takt = max(1, int(cfg.get("takt_seconds", 30)))
                        r = self.get_remaining()
                        if r not in (UNLIMITED, 0): persist_remaining(r)

                    self._tick_rs()

                    # transition check every second (max 1s latency)
                    transitioned = self._check_transition(cfg)

                    # warn/trigger only on takt boundary, not mid-transition
                    if not transitioned and self._save_cd == 0:
                        self._evaluate_warn_trigger(cfg, takt)

                except Exception as ex:
                    _log(str(datetime.now()) + ": watchdog: " + str(ex))

    # --- controller ----------------------------------------------------------

    class AppController:
        """Facade used by the GUI to interact with config, watchdog and scheduling."""

        def __init__(self, on_trigger, on_warn):
            self.wd = Watchdog(on_trigger=on_trigger, on_warn=on_warn)
            self._cfg: dict = {}

        def start(self) -> None: self.wd.start()

        def stop(self) -> None:
            persist_remaining(self.wd.get_remaining()); self.wd.stop()

        def load(self) -> dict:
            self._cfg = load_cfg()
            self.wd.set_remaining(initial_remaining(self._cfg))
            return dict(self._cfg)

        def save(self, lang: str, action: str, takt_sec: int,
                 day_states: dict, day_starts: dict, day_ends: dict,
                 day_timers: dict, day_limits: dict) -> None:
            times = []
            for d in DAYS_EN:
                st = day_states[d]
                s = "00:00" if st != "range" else day_starts[d]
                e = "00:00" if st != "range" else day_ends[d]
                times.append({"days": d, "start": s, "end": e,
                               "enabled": st != "off",
                               "use_timer": day_timers[d],
                               "limit_minutes": day_limits[d]})
            cfg = load_cfg()
            cfg.update({"target_user": current_user(),
                        "takt_seconds": takt_sec,
                        "language": lang, "action": action,
                        "allowed_times": times})
            # remove old keys from previous versions
            cfg.pop("check_interval_seconds", None)
            cfg.pop("extend_seconds", None)
            cfg.pop("logout_after_minutes", None)
            cfg.pop(_rem_key(), None)
            save_cfg(cfg); self._cfg = cfg
            self.wd.set_remaining(reset_remaining(cfg)); self.wd.kick()

        def reset_timer(self) -> None:
            cfg = load_cfg(); self.wd.set_remaining(reset_remaining(cfg))
            self._cfg = cfg; self.wd.kick()

        def get_remaining(self) -> int: return self.wd.get_remaining()
        def get_cfg(self) -> dict: return dict(self._cfg)

        def is_login_allowed(self) -> bool:
            # Always live — no cached _cfg so statusbar is always in sync
            return is_allowed(load_cfg())

        def extend(self, s: int) -> None: self.wd.extend(s); self.wd.kick()
        def reduce(self, s: int) -> None: self.wd.reduce(s); self.wd.kick()

        def check_password(self, pw: str) -> bool:
            stored = load_cfg().get("password_hash","")
            return not stored or hash_pw(pw) == stored

        def set_password(self, pw: str) -> None:
            cfg = load_cfg()
            cfg["password_hash"] = hash_pw(pw) if pw else ""
            save_cfg(cfg)

        def has_password(self) -> bool:
            return bool(load_cfg().get("password_hash",""))

        @staticmethod
        def translate(lang: str, key: str, **kw) -> str: return t(lang, key, **kw)
        @staticmethod
        def format_remaining(sec: int, lang: str) -> str: return fmt_rem(sec, lang)
        @staticmethod
        def format_date(lang: str) -> str:
            now = datetime.now()
            return "\U0001f4c5 " + t(lang, "date_fmt",
                                      day=day_full(lang, now.strftime("%A")),
                                      dt=now.strftime("%H:%M:%S"))
        @staticmethod
        def days_short(lang: str) -> list: return days_short(lang)

    # --- entry point ---------------------------------------------------------

    def main() -> None:
        mutex = ctypes.windll.kernel32.CreateMutexW(None, True, "YourTime_SingleInstance")
        if ctypes.windll.kernel32.GetLastError() == 183:
            hwnd = ctypes.windll.user32.FindWindowW(None, "YourTime")
            if hwnd:
                ctypes.windll.user32.ShowWindow(hwnd, 9)
                ctypes.windll.user32.SetForegroundWindow(hwnd)
            return
        from frontend import App
        App().mainloop()

    if __name__ == "__main__":
        main()

except Exception:
    tb = traceback.format_exc(); _log("=== STARTUP CRASH ===\n" + tb)
    try:
        import ctypes as ct
        ct.windll.user32.MessageBoxW(0, tb, "YourTime - Startup Error", 0x10)
    except Exception: pass
