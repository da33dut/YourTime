import sys
import os
import traceback
from pathlib import Path

if getattr(sys, "frozen", False):
    sys.path.insert(0, sys._MEIPASS)


def _base() -> Path:
    return Path(sys.executable).parent if getattr(sys, "frozen", False) else Path(__file__).parent


def _log(msg: str) -> None:
    try:
        with open(_base() / "error.log", "a", encoding="utf-8") as f:
            f.write(msg + "\n")
    except Exception:
        pass


try:
    import ctypes
    import hashlib
    import json
    import subprocess
    import threading
    from datetime import datetime, timedelta, time as dtime

    from definitions import (
        LANGS, ACTION_KEYS, ACTION_NEXT, DAYS_EN, DAY_CYCLE,
        DEFAULT_CFG, LANG, UNLIMITED,
    )

    def base() -> Path:
        """Return the application's base directory (exe folder or script folder)."""
        return Path(sys.executable).parent if getattr(sys, "frozen", False) else Path(__file__).parent

    def load_cfg() -> dict:
        """Load config.json, creating it with defaults if absent."""
        p = base() / "config.json"
        if not p.exists():
            cfg = {**DEFAULT_CFG, "allowed_times": [
                {"days": d, "start": "00:00", "end": "00:00", "enabled": True, "use_timer": True}
                for d in DAYS_EN
            ]}
            save_cfg(cfg)
        return json.loads(p.read_text(encoding="utf-8"))

    def save_cfg(cfg: dict) -> None:
        """Persist cfg to config.json."""
        (base() / "config.json").write_text(
            json.dumps(cfg, indent=2, ensure_ascii=False), encoding="utf-8"
        )

    def setup_autostart() -> None:
        """
        Register the executable in HKCU autostart.

        Also checks StartupApproved\\Run and re-enables the entry
        if it was disabled by the user or a policy.
        """
        try:
            import winreg
            exe = (
                f'"{sys.executable}"' if getattr(sys, "frozen", False)
                else f'"{Path(sys.executable).with_name("pythonw.exe")}" "{Path(__file__).resolve()}"'
            )
            key = winreg.OpenKey(
                winreg.HKEY_CURRENT_USER,
                r"Software\Microsoft\Windows\CurrentVersion\Run",
                0, winreg.KEY_SET_VALUE,
            )
            winreg.SetValueEx(key, "YourTime", 0, winreg.REG_SZ, exe)
            winreg.CloseKey(key)
            try:
                sa = winreg.OpenKey(
                    winreg.HKEY_CURRENT_USER,
                    r"Software\Microsoft\Windows\CurrentVersion\Explorer\StartupApproved\Run",
                    0, winreg.KEY_READ | winreg.KEY_SET_VALUE,
                )
                data, _ = winreg.QueryValueEx(sa, "YourTime")
                if isinstance(data, bytes) and len(data) >= 1 and data[0] != 0x02:
                    enabled = bytes([0x02]) + data[1:].ljust(11, b"\x00")
                    winreg.SetValueEx(sa, "YourTime", 0, winreg.REG_BINARY, enabled)
                winreg.CloseKey(sa)
            except OSError:
                pass
        except Exception:
            pass

    def hash_pw(pw: str) -> str:
        return hashlib.sha256(pw.encode()).hexdigest()

    def current_user() -> str:
        return os.getenv("USERNAME", "").strip()

    def t(lang: str, key: str, **kw) -> str:
        """Return localised string for key in lang, with optional format substitutions."""
        tmpl = LANG[lang].get(key, LANG["DE"].get(key, key))
        return tmpl.format(**kw) if kw else tmpl

    def fmt_rem(sec: int, lang: str = "DE") -> str:
        """Format remaining seconds as '⏳ [Xd] [Xh] [Xm] XXs', or '⏳ ∞' for UNLIMITED."""
        if sec == UNLIMITED:
            return "\u23f3 \u221e"
        ud, uh, um, us = (LANG[lang][k] for k in ("unit_d", "unit_h", "unit_m", "unit_s"))
        parts = [str(v) + u for v, u in (
            (sec // 86400, ud), (sec % 86400 // 3600, uh), (sec % 3600 // 60, um)
        ) if v]
        return "\u23f3 " + " ".join(parts + ["%02d" % (sec % 60,) + us])

    def day_full(lang: str, day_en: str) -> str:
        """Return the localised full weekday name for day_en."""
        try:
            return LANG[lang]["days_full"].split("|")[DAYS_EN.index(day_en)]
        except (ValueError, IndexError):
            return day_en

    def days_short(lang: str) -> list:
        """Return list of localised short weekday names."""
        return LANG[lang]["days_short"].split("|")

    def _rem_key() -> str:
        return "remaining_seconds_" + datetime.now().strftime("%Y-%m-%d")

    def _cleanup_old_rem(cfg: dict) -> None:
        cutoff = (datetime.now() - timedelta(days=30)).strftime("%Y-%m-%d")
        for k in [k for k in list(cfg) if k.startswith("remaining_seconds_") and k[18:] < cutoff]:
            del cfg[k]

    def persist_remaining(rem: int) -> None:
        """Save today's remaining seconds to config; removes the key when UNLIMITED."""
        cfg = load_cfg()
        key = _rem_key()
        cfg.pop(key, None) if rem == UNLIMITED else cfg.update({key: max(0, int(rem))})
        _cleanup_old_rem(cfg)
        save_cfg(cfg)

    def do_action(action: str) -> None:
        """Execute the configured enforcement action (lock or logoff)."""
        try:
            if action == "lock":
                ctypes.windll.user32.LockWorkStation()
            elif action == "logoff":
                subprocess.run(["shutdown", "/l"], shell=False)
        except Exception:
            pass

    def _day_end_dt(date, end_str: str) -> datetime:
        if end_str == "00:00":
            return datetime.combine(date + timedelta(days=1), dtime.min)
        hh, mm = map(int, end_str.split(":"))
        return datetime.combine(date, dtime(hh, mm))

    def get_rule(cfg: dict, day_en: str):
        """Return the allowed_times rule for day_en, or None."""
        for r in cfg.get("allowed_times", []):
            d = r.get("days")
            if (isinstance(d, list) and day_en in d) or d == day_en:
                return r
        return None

    def is_allowed(cfg: dict) -> bool:
        """Return True if the current time falls within today's allowed window."""
        now = datetime.now()
        rule = get_rule(cfg, now.strftime("%A"))
        if not rule or not rule.get("enabled", True):
            return False
        s, e = rule.get("start", "00:00"), rule.get("end", "00:00")
        if s == e:
            return True
        hhs, mms = map(int, s.split(":"))
        return datetime.combine(now.date(), dtime(hhs, mms)) <= now < _day_end_dt(now.date(), e)

    def calc_remaining_sec(cfg: dict, stored_rem: int, now=None) -> int:
        """
        Calculate effective remaining seconds considering schedule and stored timer.

        Returns UNLIMITED (-1) when no time limit applies.
        """
        now = now or datetime.now()
        if not is_allowed(cfg):
            return stored_rem
        accumulated = 0
        for i in range(8):
            dt = now + timedelta(days=i)
            rule = get_rule(cfg, dt.strftime("%A"))
            if not rule or not rule.get("enabled", True):
                return accumulated if accumulated > 0 else UNLIMITED
            s, e = rule.get("start", "00:00"), rule.get("end", "00:00")
            use_timer = rule.get("use_timer", True)
            is_full = (s == e)
            if i == 0:
                if not is_full:
                    end_dt = _day_end_dt(dt.date(), e)
                    if now >= end_dt:
                        continue
                    secs = max(0, int((end_dt - now).total_seconds()))
                else:
                    secs = max(0, int((_day_end_dt(dt.date(), "00:00") - now).total_seconds()))
            else:
                if not is_full:
                    hhe, mme = map(int, e.split(":"))
                    secs = hhe * 3600 + mme * 60
                    return accumulated + (min(stored_rem, secs) if use_timer else secs)
                secs = 86400
            if use_timer:
                return accumulated + min(stored_rem, secs)
            if is_full:
                accumulated += secs
            else:
                return accumulated + secs
        return UNLIMITED

    def initial_remaining(cfg: dict) -> int:
        """Compute remaining seconds at startup, restoring persisted value if present."""
        ivl = max(1, int(cfg.get("check_interval_seconds", 30)))
        limit = int(cfg.get("logout_after_minutes", 60) * 60)
        stored = cfg.get(_rem_key())
        return calc_remaining_sec(
            cfg, limit if stored is None else max(ivl, min(int(stored), limit))
        )

    def reset_remaining(cfg: dict) -> int:
        """Return remaining seconds after a manual timer reset."""
        limit = int(cfg.get("logout_after_minutes", 60) * 60)
        if not is_allowed(cfg):
            return max(1, int(cfg.get("check_interval_seconds", 30)))
        return calc_remaining_sec(cfg, limit)


    class Watchdog(threading.Thread):
        """Background thread that enforces daily time limits and triggers configured actions."""

        SAVE_INTERVAL = 10

        def __init__(self, on_trigger, on_warn):
            super().__init__(daemon=True)
            self.on_trigger = on_trigger
            self.on_warn = on_warn
            self.warned = False
            self.running = True
            self._lock = threading.Lock()
            self._remaining = UNLIMITED
            self._was_allowed = None
            self._stop_evt = threading.Event()
            self._save_cd = self.SAVE_INTERVAL
            self._just_acted = False

        def get_remaining(self):
            with self._lock:
                return self._remaining

        def set_remaining(self, rem):
            with self._lock:
                self._remaining = rem
                self.warned = False
                self._save_cd = self.SAVE_INTERVAL
            persist_remaining(rem)

        def clamp_to_ivl(self, cfg):
            self.set_remaining(max(1, int(cfg.get("check_interval_seconds", 30))))

        def adjust(self, delta):
            """Add delta seconds to remaining, clamped between interval and daily limit."""
            cfg = load_cfg()
            limit = int(cfg.get("logout_after_minutes", 60) * 60)
            ivl = max(1, int(cfg.get("check_interval_seconds", 30)))
            with self._lock:
                if self._remaining == UNLIMITED:
                    return
                self._remaining = max(ivl, min(self._remaining + delta, limit))
                self.warned = False
            persist_remaining(self._remaining)

        def extend(self, s): self.adjust(+abs(s))
        def reduce(self, s): self.adjust(-abs(s))
        def kick(self): self._stop_evt.set()
        def stop(self): self.running = False; self._stop_evt.set()

        def run(self):
            cfg = load_cfg()
            ivl = max(1, int(cfg.get("check_interval_seconds", 30)))
            cd = ivl
            while self.running:
                self._stop_evt.wait(timeout=1)
                kicked = self._stop_evt.is_set()
                self._stop_evt.clear()
                if not self.running:
                    break
                try:
                    if self._just_acted:
                        self._just_acted = False
                        cfg = load_cfg()
                        ivl = max(1, int(cfg.get("check_interval_seconds", 30)))
                        persist_remaining(0)
                        self.clamp_to_ivl(cfg)
                        cd = ivl
                        continue
                    with self._lock:
                        if self._remaining > 0:
                            self._remaining -= 1
                        self._save_cd -= 1
                    if self._save_cd <= 0:
                        self._save_cd = self.SAVE_INTERVAL
                        r = self.get_remaining()
                        if r > 0:
                            persist_remaining(r)
                    cd -= 1
                    if cd <= 0 or kicked:
                        cfg = load_cfg()
                        ivl = max(1, int(cfg.get("check_interval_seconds", 30)))
                        cd = ivl
                        user = cfg.get("target_user", "").lower().strip()
                        if not (user and current_user().lower() == user):
                            continue
                        allowed = is_allowed(cfg)
                        action = cfg.get("action", "lock")
                        if self._was_allowed is None:
                            self._was_allowed = allowed
                            if not allowed:
                                self.clamp_to_ivl(cfg)
                        elif allowed != self._was_allowed:
                            self._was_allowed = allowed
                            if not allowed:
                                self.clamp_to_ivl(cfg)
                        rem = self.get_remaining()
                        if rem == 0:
                            self._just_acted = True
                            self.on_trigger("msg_timeout" if allowed else "msg_blocked", action)
                            continue
                        if rem != UNLIMITED and rem <= ivl and not self.warned:
                            self.warned = True
                            self.on_warn(max(0, rem // 60))
                        elif rem == UNLIMITED or rem > ivl:
                            self.warned = False
                except Exception as ex:
                    _log(str(datetime.now()) + ": watchdog: " + str(ex))


    class AppController:
        """Facade used by the GUI to interact with config, watchdog and scheduling logic."""

        def __init__(self, on_trigger, on_warn):
            self.wd = Watchdog(on_trigger=on_trigger, on_warn=on_warn)
            self._cfg = {}

        def start(self):
            setup_autostart()
            self.wd.start()

        def stop(self):
            persist_remaining(self.wd.get_remaining())
            self.wd.stop()

        def load(self):
            self._cfg = load_cfg()
            self.wd.set_remaining(initial_remaining(self._cfg))
            return dict(self._cfg)

        def save(self, lang, action, logout_min, interval_sec, extend_sec,
                 day_states, day_starts, day_ends, day_timers):
            """Persist GUI settings and reset the watchdog timer."""
            times = []
            for d in DAYS_EN:
                st = day_states[d]
                if st == "off":
                    times.append({"days": d, "start": "00:00", "end": "00:00",
                                  "enabled": False, "use_timer": False})
                    continue
                s = "00:00" if st == "on" else day_starts[d]
                e = "00:00" if st == "on" else day_ends[d]
                times.append({"days": d, "start": s, "end": e,
                               "enabled": True, "use_timer": day_timers[d]})
            cfg = load_cfg()
            cfg.update({
                "target_user": current_user(), "logout_after_minutes": logout_min,
                "check_interval_seconds": interval_sec, "extend_seconds": extend_sec,
                "language": lang, "action": action, "allowed_times": times,
            })
            cfg.pop(_rem_key(), None)
            save_cfg(cfg)
            self._cfg = cfg
            self.wd.set_remaining(reset_remaining(cfg))
            self.wd.kick()

        def reset_timer(self):
            cfg = load_cfg()
            self.wd.set_remaining(reset_remaining(cfg))
            self._cfg = cfg
            self.wd.kick()

        def get_remaining(self): return self.wd.get_remaining()
        def get_cfg(self): return dict(self._cfg)
        def is_login_allowed(self): return is_allowed(self._cfg)
        def extend(self, s): self.wd.extend(s); self.wd.kick()
        def reduce(self, s): self.wd.reduce(s); self.wd.kick()

        def check_password(self, pw):
            stored = load_cfg().get("password_hash", "")
            return not stored or hash_pw(pw) == stored

        def set_password(self, pw):
            cfg = load_cfg()
            cfg["password_hash"] = hash_pw(pw) if pw else ""
            save_cfg(cfg)

        def has_password(self):
            return bool(load_cfg().get("password_hash", ""))

        @staticmethod
        def translate(lang, key, **kw): return t(lang, key, **kw)

        @staticmethod
        def format_remaining(sec, lang): return fmt_rem(sec, lang)

        @staticmethod
        def format_date(lang):
            now = datetime.now()
            return "\U0001f4c5 " + t(lang, "date_fmt",
                                      day=day_full(lang, now.strftime("%A")),
                                      dt=now.strftime("%H:%M:%S"))

        @staticmethod
        def days_short(lang): return days_short(lang)


    def main():
        """
        Application entry point.

        Enforces single-instance via a named Windows mutex.
        If another instance is running, brings its window to the front.
        """
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
    tb = traceback.format_exc()
    _log("=== STARTUP CRASH ===\n" + tb)
    try:
        import ctypes as ct
        ct.windll.user32.MessageBoxW(0, tb, "YourTime - Startup Error", 0x10)
    except Exception:
        pass
