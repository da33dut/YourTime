"""YourTime – Tkinter settings window with system-tray integration.

Reuse guide for other projects
-------------------------------
LBtn        – drop-in label-button widget, no YourTime-specific logic.
StatusMixin – timed status-bar messages with priority queuing;
              mix into any tk.Tk subclass.
LockMixin   – generic lock/unlock infrastructure for ttk + LBtn widget groups.
App         – assembles the above into the full YourTime window.

Frontend/Backend contract
--------------------------
- Import only: AppController, base, do_action, autostart_*, validate_time
- No direct Watchdog access; no backend module-level state touched.
- Callbacks on_trigger / on_warn are the only inbound channel from backend.
"""
import ctypes, threading
import tkinter as tk
from tkinter import ttk

from definitions import (
    # domain
    LANGS, ACTION_KEYS, ACTION_NEXT, DAYS_EN, DAY_CYCLE, DAY_COLORS,
    LANG, DEFAULT_LANG, DEFAULT_ACTION, UNLIMITED,
    DEFAULT_DAY_LIMIT_MIN, DAY_LIMIT_MIN_LO, DAY_LIMIT_MIN_HI,
    DEFAULT_TAKT_SEC, TAKT_SEC_LO, TAKT_SEC_HI,
    # GUI geometry – settings frame
    W_DAY, W_ROW, W_ENTRY_TIME, W_DAY_LIMIT,
    W_SPINLBL, W_LANG, W_AUTOSTART, W_ACTION, W_SPINBOX,
    # GUI geometry – password row & adjust
    W_PW_LBL, W_PWSET, W_EXT, PW_ENTRY_WIDTH,
    # GUI geometry – bottom bar & status bar
    W_LOCK, W_SIDE, W_STATUSBAR_DT, W_STATUSBAR_REM,
    # padding
    PAD_OUTER, PAD_INNER, PAD_ROW, PAD_BTN, BTN_PAD,
    # fonts
    FONT_NORMAL, FONT_BOLD, FONT_ROW_HDR, FONT_REM,
    # colours
    C_BLUE, C_GREEN, C_RED, C_GRAY_N, C_WHITE, C_BLACK, C_DIS_BG, C_DIS_FG,
    # timings
    TICK_MS, STATUS_DURATION_MS, TRIGGER_DURATION_MS,
    WARN_FRONT_INTERVAL_MS, STARTUP_HIDE_DELAY_MS, TOPMOST_RELEASE_MS,
    # assets
    ICON_ICO_PATH, TRAY_ICO_PATH, TRAY_ICON_SIZE,
    # misc
    MSG_PRIO, WIN_TITLE, DAY_DEFAULT_START, DAY_DEFAULT_END,
)
from backend import (
    AppController, base, do_action,
    autostart_enabled, autostart_exists, autostart_set, validate_time,
)

try:
    import pystray
    from PIL import Image, ImageDraw
    HAS_TRAY = True
except ImportError:
    HAS_TRAY = False


# ===========================================================================
# LBtn – reusable label-button widget (no YourTime-specific dependencies)
# ===========================================================================

class LBtn:
    """tk.Label styled as a clickable button.

    Two disable modes:
      enable(False)        – bg->gray, fg->gray, flat relief  (editable controls)
      set_clickable(False) – bg preserved, fg->gray, flat relief (status toggles)
    """

    def __init__(self, parent, text: str, width: int, cmd,
                 active_bg: str = C_GRAY_N, active_fg: str = C_BLACK,
                 bold: bool = False):
        self.active_bg = active_bg
        self.active_fg = active_fg
        self._cmd      = cmd
        self._enabled  = True
        self._pressed  = False
        self.w = tk.Label(
            parent, text=text,
            font=FONT_BOLD if bold else FONT_NORMAL,
            width=width, relief="raised", bd=1,
            bg=active_bg, fg=active_fg, cursor="hand2", anchor="center",
        )
        self.w.bind("<ButtonPress-1>",   lambda e: self._press())
        self.w.bind("<ButtonRelease-1>", lambda e: self._release())
        self.w.bind("<Leave>",           lambda e: self._cancel())

    def _press(self) -> None:
        if self._enabled:
            self._pressed = True; self.w.config(relief="sunken")

    def _release(self) -> None:
        if self._enabled and self._pressed:
            self._pressed = False; self.w.config(relief="raised")
            if self._cmd: self._cmd()

    def _cancel(self) -> None:
        self._pressed = False
        if self._enabled: self.w.config(relief="raised")

    def enable(self, on: bool) -> None:
        self._enabled = on
        if not on: self._pressed = False
        self.w.config(
            bg=self.active_bg if on else C_DIS_BG,
            fg=self.active_fg if on else C_DIS_FG,
            cursor="hand2" if on else "arrow",
            relief="raised" if on else "flat",
        )

    def set_clickable(self, on: bool) -> None:
        """Toggle interactivity while preserving background colour."""
        self._enabled = on
        self.w.config(
            fg=self.active_fg if on else C_DIS_FG,
            cursor="hand2" if on else "arrow",
            relief="raised" if on else "flat",
        )

    def config(self, **kw) -> None:
        if "active_bg" in kw: self.active_bg = kw.pop("active_bg")
        if "active_fg" in kw: self.active_fg = kw.pop("active_fg")
        self.w.config(**kw)

    def pack(self, **kw) -> None:
        kw.setdefault("ipady", BTN_PAD); self.w.pack(**kw)

    def grid(self, **kw) -> None:
        kw.setdefault("ipady", BTN_PAD); self.w.grid(**kw)


# ===========================================================================
# StatusMixin – timed, priority-queued status-bar messages
# ===========================================================================

class StatusMixin:
    """Mix into tk.Tk (or tk.Toplevel) to get status_msg() / _clear_msg().

    Requires subclass to provide:
      self.sb_login            – tk.Label used as message target
      self._t(key, **kw)       – translation helper
      self.ctrl.is_login_allowed() – for the idle indicator
    """

    def _init_status(self) -> None:
        self._msg_state = None   # (key, color, after_id, kwargs)

    def status_msg(self, key: str, color: str,
                   duration_ms: int = STATUS_DURATION_MS, **kw) -> None:
        """Display a timed status message; lower MSG_PRIO number = higher priority."""
        txt      = self._t(key, **kw) if key in LANG[DEFAULT_LANG] else key
        new_prio = MSG_PRIO.get(color, 99)
        if self._msg_state:
            if new_prio > MSG_PRIO.get(self._msg_state[1], 99): return
            try: self.after_cancel(self._msg_state[2])
            except Exception: pass
        self.sb_login.config(text=txt, foreground=color)
        self._msg_state = (key, color, self.after(duration_ms, self._clear_msg), kw)

    def _clear_msg(self) -> None:
        self._msg_state = None
        self._update_sb_login()

    def _update_sb_login(self) -> None:
        if self._msg_state: return
        allowed = self.ctrl.is_login_allowed()
        self.sb_login.config(
            text=self._t("sb_allowed" if allowed else "sb_denied"),
            foreground="green" if allowed else "red",
        )


# ===========================================================================
# LockMixin – generic lock/unlock for grouped ttk + LBtn widgets
# ===========================================================================

class LockMixin:
    """Mix into tk.Tk.  Manages two widget registries:
      _ttk_lock – ttk widgets toggled via state="disabled"/"normal"
      _lbtns    – LBtn instances toggled via enable()
    """

    def _init_lock(self) -> None:
        self._ttk_lock: list = []
        self._lbtns:    list = []

    def _ttk_lw(self, w):
        """Register a ttk widget for lock/unlock."""
        self._ttk_lock.append(w); return w

    def _lbtn(self, parent, text, width, cmd,
              active_bg=C_GRAY_N, active_fg=C_BLACK,
              bold=False, lockable=True) -> LBtn:
        """Create LBtn; register in lock-list when lockable=True."""
        b = LBtn(parent, text, width, cmd, active_bg, active_fg, bold)
        if lockable: self._lbtns.append(b)
        return b

    def _set_lock(self, locked: bool) -> None:
        """Apply or lift lock on all registered widgets."""
        state = "disabled" if locked else "normal"
        for w in self._ttk_lock:
            try: w.config(state=state)
            except Exception: pass
        for b in self._lbtns:
            b.enable(not locked)


# ===========================================================================
# App – YourTime main window
# ===========================================================================

class App(tk.Tk, StatusMixin, LockMixin):
    """YourTime settings window: day-grid, right panel, password row, status bar."""

    # --- init ---------------------------------------------------------------

    def __init__(self) -> None:
        super().__init__()
        self._init_status()
        self._init_lock()

        self._lang    = DEFAULT_LANG
        self._action  = DEFAULT_ACTION
        self.unlocked = False

        self._wlabels: dict = {}    # i18n key -> widget for relabelling

        self._pw_mode            = False
        self._warn_shown         = False
        self._keep_front_running = False

        # Last-known-good cache for free-form input fields
        self._last_good_start: dict = {}
        self._last_good_end:   dict = {}
        self._last_good_limit: dict = {}
        self._last_good_takt:  int  = DEFAULT_TAKT_SEC

        self._clamping = False   # re-entry guard for spinbox trace callbacks

        self.ctrl = AppController(on_trigger=self._cb_trigger, on_warn=self._cb_warn)

        self.title(WIN_TITLE)
        self.resizable(False, False)
        ico = base().joinpath(*ICON_ICO_PATH)
        if ico.exists():
            try: self.iconbitmap(str(ico))
            except Exception: pass
        self.protocol("WM_DELETE_WINDOW", self.hide)
        self.bind("<Escape>", lambda e: self.hide())

        self._build()
        self._load()
        self._apply_lock(True)
        self._tick()
        self._tray_setup()
        self.ctrl.start()
        self.iconify()
        self.after(STARTUP_HIDE_DELAY_MS, self.withdraw)

    # --- backend callbacks --------------------------------------------------

    def _cb_trigger(self, key: str, action: str) -> None:
        """Watchdog: enforcement event – show message, execute system action."""
        self.after(0, lambda: self.status_msg(key, "red", duration_ms=TRIGGER_DURATION_MS))
        do_action(action)

    def _cb_warn(self, minutes: int) -> None:
        """Watchdog: entering warning zone."""
        self.after(0, lambda: self.status_msg("msg_warn_min", "orange", m=minutes))

    # --- i18n ---------------------------------------------------------------

    def _t(self, key: str, **kw) -> str:
        return self.ctrl.translate(self._lang, key, **kw)

    def _reg(self, key: str, w) -> None:
        """Register widget for automatic text refresh on language change."""
        self._wlabels[key] = w

    def _relabel(self) -> None:
        """Refresh all registered widget texts after a language change."""
        for key, w in self._wlabels.items():
            if key in LANG[DEFAULT_LANG]:
                try: w.config(text=self._t(key))
                except Exception: pass
        self.btn_lang.config(text=self._lang)
        self.btn_action.config(text=self._t("action_" + self._action))
        self.btn_lock.config(text=self._t("btn_unlock" if self.unlocked else "btn_lock"))
        for en, short in zip(DAYS_EN, self.ctrl.days_short(self._lang)):
            self._day_btns[en].config(text=short)
        self._update_btn_states()
        self._refresh_autostart_btn()
        self.sb_dt.config(text=self.ctrl.format_date(self._lang))
        self._update_sb_login()

    # --- window helpers -----------------------------------------------------

    def _show(self) -> None:
        self.deiconify(); self.lift(); self.focus_force()
        self.attributes("-topmost", True)
        self.after(TOPMOST_RELEASE_MS, lambda: self.attributes("-topmost", False))

    # --- lock / unlock ------------------------------------------------------

    def _apply_lock(self, locked: bool) -> None:
        self._set_lock(locked)
        self.btn_lock.config(text=self._t("btn_lock" if locked else "btn_unlock"))
        for d in DAYS_EN:
            self._day_btns[d].set_clickable(not locked)
            if locked:
                for w in self._day_entries[d]: w.config(state="disabled")
                self._day_limit_spin[d].config(state="disabled")
            else:
                self._refresh_day(d)
        self.btn_autostart.set_clickable(not locked)
        self._update_btn_states()

    def _update_btn_states(self) -> None:
        """Sync +/- takt button labels and enabled state.

        UNLIMITED -> both disabled.
        Unlocked  -> both always active.
        Locked    -> reduce always active; extend only in warning zone.
        """
        takt = self.ctrl.get_cfg().get("takt_seconds", DEFAULT_TAKT_SEC)
        us   = self._t("unit_s")
        rem  = self.ctrl.get_remaining()
        lr   = f"-{takt}{us}"; le = f"+{takt}{us}"
        if rem == UNLIMITED:
            self.btn_reduce.config(text=lr); self.btn_reduce.enable(False)
            self.btn_extend.config(text=le); self.btn_extend.enable(False)
            return
        self.btn_reduce.config(text=lr); self.btn_extend.config(text=le)
        if self.unlocked:
            self.btn_reduce.enable(True); self.btn_extend.enable(True)
        else:
            self.btn_reduce.enable(True)
            self.btn_extend.enable(rem <= takt)

    # --- autosave -----------------------------------------------------------

    def _autosave(self, *_) -> None:
        """Triggered by any GUI variable trace; re-entry guarded via _clamping."""
        if self._clamping or not self.unlocked:
            return

        for d in DAYS_EN:
            s = self.day_start[d].get().strip()
            e = self.day_end[d].get().strip()
            if validate_time(s): self._last_good_start[d] = s
            if validate_time(e): self._last_good_end[d]   = e
            self._last_good_start.setdefault(d, "00:00")
            self._last_good_end.setdefault(d,   "00:00")

        for d in DAYS_EN:
            try:
                raw     = int(self.day_limit[d].get())
                clamped = max(DAY_LIMIT_MIN_LO, min(DAY_LIMIT_MIN_HI, raw))
                self._last_good_limit[d] = clamped
                if clamped != raw:
                    self._clamping = True
                    try:   self.day_limit[d].set(clamped)
                    finally: self._clamping = False
            except (ValueError, tk.TclError): pass
            self._last_good_limit.setdefault(d, DEFAULT_DAY_LIMIT_MIN)

        try:
            raw     = int(self.v_takt.get())
            clamped = max(TAKT_SEC_LO, min(TAKT_SEC_HI, raw))
            self._last_good_takt = clamped
            if clamped != raw:
                self._clamping = True
                try:   self.v_takt.set(clamped)
                finally: self._clamping = False
        except (ValueError, tk.TclError): pass

        try:
            self.ctrl.save(
                lang=self._lang,  action=self._action,
                takt_sec=self._last_good_takt,
                day_states=dict(self.day_state),
                day_starts=dict(self._last_good_start),
                day_ends=dict(self._last_good_end),
                day_timers={d: self.day_timer[d].get() for d in DAYS_EN},
                day_limits=dict(self._last_good_limit),
            )
        except Exception: pass

    # --- inline password ----------------------------------------------------

    def _on_lock_btn(self) -> None:
        if self.unlocked:
            self.unlocked = False; self._apply_lock(True)
        else:
            self._enter_pw_mode()

    def _enter_pw_mode(self) -> None:
        self._pw_mode = True
        self.btn_lock.w.pack_forget()
        self.v_pw_inline.set("")
        self.pw_entry.pack(side="left", fill="x", expand=True)
        self.btn_pw_ok.pack(side="left", padx=(2, 0))
        self.btn_pw_cancel.pack(side="left", padx=(2, PAD_BTN))
        self.pw_entry.focus_set()

    def _exit_pw_mode(self) -> None:
        self._pw_mode = False
        for w in (self.pw_entry, self.btn_pw_ok, self.btn_pw_cancel):
            w.pack_forget()
        self.v_pw_inline.set("")
        self.btn_lock.w.pack(side="left", fill="x", expand=True,
                             padx=(PAD_ROW, PAD_ROW), ipady=BTN_PAD)

    def _check_pw(self, _=None) -> None:
        ok = self.ctrl.check_password(self.v_pw_inline.get())
        if ok:
            self.unlocked = True
            self._apply_lock(False)
            self._exit_pw_mode()
            key   = "msg_unlocked" if self.ctrl.has_password() else "msg_no_pw"
            color = "green"        if self.ctrl.has_password() else "orange"
            self.status_msg(key, color)
        else:
            self.v_pw_inline.set("")
            self.status_msg("msg_pw_wrong", "red")
            self.pw_entry.focus_set()

    # --- autostart ----------------------------------------------------------

    def _refresh_autostart_btn(self) -> None:
        on  = autostart_enabled()
        col = C_GREEN if on else C_RED
        self.btn_autostart.active_bg = col
        self.btn_autostart.config(text=self._t("btn_autostart_on" if on else "btn_autostart_off"))
        self.btn_autostart.w.config(bg=col)

    def _toggle_autostart(self) -> None:
        if not self.unlocked: return
        try:
            autostart_set(not autostart_exists())
        except Exception as ex:
            self._refresh_autostart_btn()
            self.status_msg("msg_autostart_err", "red", e=ex)
            return
        self._refresh_autostart_btn()
        self.status_msg("msg_autostart_on" if autostart_enabled() else "msg_autostart_off", "blue")

    # --- cycle toggles ------------------------------------------------------

    def _cycle_lang(self) -> None:
        self._lang = LANGS[(LANGS.index(self._lang) + 1) % len(LANGS)]
        self.ctrl.set_language(self._lang)
        self._relabel()
        self._tray_update()

    def _cycle_action(self) -> None:
        self._action = ACTION_NEXT[self._action]
        self.btn_action.config(text=self._t("action_" + self._action))
        self._autosave()

    def _cycle_day(self, day: str) -> None:
        if not self.unlocked: return
        self.day_state[day] = DAY_CYCLE[self.day_state[day]]
        self._refresh_day(day)
        self._autosave()

    def _refresh_day(self, day: str) -> None:
        st  = self.day_state[day]
        col = DAY_COLORS[st]
        b   = self._day_btns[day]
        b.active_bg = col; b.w.config(bg=col)
        show_range = (st == "range") and self.unlocked
        show_limit = (st != "off")   and self.unlocked
        for w in self._day_entries[day]:
            w.config(state="normal" if show_range else "disabled")
        self._day_limit_spin[day].config(state="normal" if show_limit else "disabled")

    # --- timer adjust -------------------------------------------------------

    def _on_extend(self) -> None:
        t = self.ctrl.get_cfg().get("takt_seconds", DEFAULT_TAKT_SEC)
        self.ctrl.extend(t); self.status_msg("msg_extended", "blue", s=t)

    def _on_reduce(self) -> None:
        t = self.ctrl.get_cfg().get("takt_seconds", DEFAULT_TAKT_SEC)
        self.ctrl.reduce(t); self.status_msg("msg_reduced", "blue", s=t)

    def _save_pw(self) -> None:
        p1, p2 = self.v_pw1.get(), self.v_pw2.get()
        if p1 != p2:
            self.status_msg("msg_pw_mismatch", "red"); return
        self.ctrl.set_password(p1)
        self.v_pw1.set(""); self.v_pw2.set("")
        self.status_msg("msg_pw_set" if p1 else "msg_pw_removed", "blue")

    # --- public actions -----------------------------------------------------

    def reset_timer(self) -> None:
        self.ctrl.reset_timer()
        self.status_msg("msg_reset", "blue")

    def hide(self) -> None:
        if self._pw_mode:  self._exit_pw_mode()
        if self.unlocked:  self.unlocked = False; self._apply_lock(True)
        self.withdraw()

    def exit_app(self) -> None:
        if hasattr(self, "tray"): self.tray.stop()
        self.ctrl.stop()
        self.destroy()

    # --- system tray --------------------------------------------------------

    def _tray_setup(self) -> None:
        if not HAS_TRAY: return
        ico = base().joinpath(*TRAY_ICO_PATH)
        img = Image.open(ico).resize(TRAY_ICON_SIZE) if ico.exists() else self._mk_icon()
        self.tray = pystray.Icon(
            WIN_TITLE, img, WIN_TITLE,
            pystray.Menu(pystray.MenuItem(
                self._t("tray_open"), lambda *_: self.after(0, self._show), default=True,
            )),
        )
        threading.Thread(target=self.tray.run, daemon=True).start()

    def _tray_update(self) -> None:
        if not HAS_TRAY or not hasattr(self, "tray"): return
        self.tray.menu = pystray.Menu(pystray.MenuItem(
            self._t("tray_open"), lambda *_: self.after(0, self._show), default=True,
        ))

    def _mk_icon(self) -> "Image.Image":
        img = Image.new("RGB", TRAY_ICON_SIZE, (0, 120, 215))
        d   = ImageDraw.Draw(img)
        d.ellipse([6, 6, 58, 58],   fill="white")
        d.ellipse([14, 14, 50, 50], fill=(0, 120, 215))
        d.rectangle([30, 18, 34, 34], fill="white")
        d.rectangle([30, 30, 44, 34], fill="white")
        return img

    # --- foreground enforcement ---------------------------------------------

    def _force_front(self) -> None:
        """Force window to foreground, bypassing Windows focus lock via AttachThreadInput."""
        self.deiconify(); self.attributes("-topmost", True); self.lift(); self.focus_force()
        try:
            hwnd  = ctypes.windll.user32.GetParent(self.winfo_id()) or self.winfo_id()
            fg    = ctypes.windll.user32.GetForegroundWindow()
            tid   = ctypes.windll.kernel32.GetCurrentThreadId()
            fgtid = ctypes.windll.user32.GetWindowThreadProcessId(fg, None)
            if fgtid and fgtid != tid:
                ctypes.windll.user32.AttachThreadInput(tid, fgtid, True)
                ctypes.windll.user32.SetForegroundWindow(hwnd)
                ctypes.windll.user32.AttachThreadInput(tid, fgtid, False)
            else:
                ctypes.windll.user32.SetForegroundWindow(hwnd)
        except Exception: pass

    def _keep_front(self) -> None:
        warn = self.ctrl.is_in_warn_zone()
        if warn:
            self._keep_front_running = True
            if self.state() in ("withdrawn", "iconic"):
                self._force_front()
            else:
                self.lift(); self.attributes("-topmost", True)
            self.after(WARN_FRONT_INTERVAL_MS, self._keep_front)
        else:
            self._keep_front_running = False
            self.attributes("-topmost", False)

    # --- main tick ----------------------------------------------------------

    def _tick(self) -> None:
        try:
            rem  = self.ctrl.get_remaining()
            warn = self.ctrl.is_in_warn_zone()
            self.sb_dt.config(text=self.ctrl.format_date(self._lang))
            self._update_sb_login()
            self.sb_rem.config(
                text=self.ctrl.format_remaining(rem, self._lang),
                foreground="red" if warn else "blue",
            )
            self.btn_lock.config(text=self._t("btn_unlock" if self.unlocked else "btn_lock"))
            self._update_btn_states()
            if warn and not self._warn_shown:
                self._warn_shown = True
                self._force_front()
                if not self._keep_front_running:
                    self._keep_front()
            if not warn:
                self._warn_shown = False
                self.attributes("-topmost", False)
        except Exception: pass
        self.after(TICK_MS, self._tick)

    # --- load ---------------------------------------------------------------

    def _load(self) -> None:
        try:
            cfg = self.ctrl.load()
            self._lang   = cfg.get("language", DEFAULT_LANG)
            if self._lang not in LANGS: self._lang = DEFAULT_LANG
            self._action = cfg.get("action", DEFAULT_ACTION)
            if self._action not in ACTION_KEYS: self._action = DEFAULT_ACTION
            self.btn_lang.config(text=self._lang)
            self.btn_action.config(text=self._t("action_" + self._action))
            self.v_takt.set(cfg.get("takt_seconds", DEFAULT_TAKT_SEC))

            for r in cfg.get("allowed_times", []):
                d = r.get("days")
                for dd in (d if isinstance(d, list) else [d]):
                    if dd not in self.day_state: continue
                    s, e = r.get("start", "00:00"), r.get("end", "00:00")
                    if not r.get("enabled", True):    self.day_state[dd] = "off"
                    elif s == e:                       self.day_state[dd] = "on"
                    else:                              self.day_state[dd] = "range"
                    self.day_start[dd].set(s); self.day_end[dd].set(e)
                    self.day_timer[dd].set(r.get("use_timer", True))
                    self.day_limit[dd].set(r.get("limit_minutes", DEFAULT_DAY_LIMIT_MIN))

            for d in DAYS_EN: self._refresh_day(d)
            self._last_good_takt = cfg.get("takt_seconds", DEFAULT_TAKT_SEC)
            for d in DAYS_EN:
                sv = self.day_start[d].get().strip()
                ev = self.day_end[d].get().strip()
                self._last_good_start[d] = sv if validate_time(sv) else "00:00"
                self._last_good_end[d]   = ev if validate_time(ev) else "00:00"
                try:   self._last_good_limit[d] = int(self.day_limit[d].get())
                except (ValueError, tk.TclError): self._last_good_limit[d] = DEFAULT_DAY_LIMIT_MIN
            self._relabel()
            self._refresh_autostart_btn()
        except Exception as ex:
            self.status_msg("msg_cfg_err", "red", e=ex)

    # -----------------------------------------------------------------------
    # UI build
    # -----------------------------------------------------------------------

    def _build(self) -> None:
        self._build_settings()
        self._build_password_row()
        self._build_buttons()
        self._build_statusbar()

    def _build_settings(self) -> None:
        outer = ttk.LabelFrame(self, text=self._t("frm_settings"))
        outer.pack(fill="x", padx=PAD_OUTER, pady=PAD_INNER)
        self._reg("frm_settings", outer)

        # Day grid -----------------------------------------------------------
        days_f = ttk.Frame(outer)
        days_f.grid(row=0, column=0, sticky="nsew", padx=(4, 8), pady=PAD_BTN)

        for row, key in enumerate(("row_from", "row_to", "row_timer", "row_limit_min"), start=2):
            lbl = ttk.Label(days_f, text=self._t(key), width=W_ROW, font=FONT_ROW_HDR, anchor="w")
            lbl.grid(row=row, column=0, sticky="w", padx=PAD_BTN, pady=PAD_ROW)
            self._reg(key, lbl)

        self.day_state = {}; self.day_start = {}; self.day_end   = {}
        self.day_timer = {}; self.day_limit = {}
        self._day_btns = {}; self._day_entries = {}; self._day_limit_spin = {}

        for col, (en, short) in enumerate(zip(DAYS_EN, self.ctrl.days_short(self._lang)), start=1):
            b = self._lbtn(
                days_f, short, W_DAY, lambda d=en: self._cycle_day(d),
                active_bg=DAY_COLORS["on"], active_fg=C_WHITE, bold=True, lockable=False,
            )
            b.w.grid(row=0, column=col, padx=1, pady=PAD_BTN)
            self._day_btns[en] = b

            vs = tk.StringVar(value=DAY_DEFAULT_START)
            ve = tk.StringVar(value=DAY_DEFAULT_END)
            self.day_start[en] = vs; self.day_end[en] = ve
            es = ttk.Entry(days_f, textvariable=vs, width=W_ENTRY_TIME, justify="center")
            ee = ttk.Entry(days_f, textvariable=ve, width=W_ENTRY_TIME, justify="center")
            es.grid(row=2, column=col, padx=1, pady=PAD_ROW)
            ee.grid(row=3, column=col, padx=1, pady=PAD_ROW)
            self._day_entries[en] = (es, ee)
            self._ttk_lw(es); self._ttk_lw(ee)

            vt = tk.BooleanVar(value=True); self.day_timer[en] = vt
            self._ttk_lw(ttk.Checkbutton(days_f, variable=vt)).grid(
                row=4, column=col, padx=1, pady=PAD_ROW)

            vl = tk.IntVar(value=DEFAULT_DAY_LIMIT_MIN); self.day_limit[en] = vl
            sp = ttk.Spinbox(days_f, from_=DAY_LIMIT_MIN_LO, to=DAY_LIMIT_MIN_HI,
                             textvariable=vl, width=W_DAY_LIMIT, justify="center")
            sp.grid(row=5, column=col, padx=1, pady=PAD_ROW)
            self._day_limit_spin[en] = sp; self._ttk_lw(sp)
            self.day_state[en] = "on"

            vs.trace_add("write", self._autosave)
            ve.trace_add("write", self._autosave)
            vt.trace_add("write", self._autosave)
            vl.trace_add("write", self._autosave)

        ttk.Separator(outer, orient="vertical").grid(row=0, column=1, sticky="ns", pady=PAD_BTN)

        # Right panel --------------------------------------------------------
        rf = ttk.Frame(outer)
        rf.grid(row=0, column=2, sticky="new", padx=(8, 4), pady=PAD_BTN)

        right_rows = [
            ("lbl_lang",      lambda: self._lbtn(rf, self._lang, W_LANG, self._cycle_lang,
                                                  active_bg=C_BLUE, active_fg=C_WHITE,
                                                  bold=True, lockable=False)),
            ("lbl_autostart", lambda: self._lbtn(rf, self._t("btn_autostart_off"), W_AUTOSTART,
                                                  self._toggle_autostart,
                                                  active_bg=C_RED, active_fg=C_WHITE,
                                                  bold=True, lockable=False)),
            ("lbl_action",    lambda: self._lbtn(rf, self._t("action_" + self._action), W_ACTION,
                                                  self._cycle_action,
                                                  active_bg=C_BLUE, active_fg=C_WHITE, bold=True)),
        ]
        _attr = {"lbl_lang": "btn_lang", "lbl_autostart": "btn_autostart", "lbl_action": "btn_action"}
        for row, (lbl_key, factory) in enumerate(right_rows):
            lbl = ttk.Label(rf, text=self._t(lbl_key), width=W_SPINLBL, anchor="w")
            lbl.grid(row=row, column=0, sticky="w", padx=(0, PAD_BTN), pady=(0, PAD_BTN))
            self._reg(lbl_key, lbl)
            btn = factory()
            btn.w.grid(row=row, column=1, sticky="w", pady=(0, PAD_BTN))
            setattr(self, _attr[lbl_key], btn)

        lbl_takt = ttk.Label(rf, text=self._t("lbl_takt"), width=W_SPINLBL, anchor="w")
        lbl_takt.grid(row=3, column=0, sticky="w", padx=(0, PAD_BTN), pady=PAD_ROW)
        self._reg("lbl_takt", lbl_takt)
        self.v_takt = tk.IntVar(value=DEFAULT_TAKT_SEC)
        self._ttk_lw(ttk.Spinbox(
            rf, from_=TAKT_SEC_LO, to=TAKT_SEC_HI,
            textvariable=self.v_takt, width=W_SPINBOX,
        )).grid(row=3, column=1, pady=PAD_ROW, sticky="w")
        self.v_takt.trace_add("write", self._autosave)

    def _build_password_row(self) -> None:
        outer = ttk.Frame(self)
        outer.pack(fill="x", padx=PAD_OUTER, pady=(0, PAD_INNER))

        # Password panel (left)
        fp = ttk.LabelFrame(outer, text=self._t("frm_password"))
        fp.pack(side="left", fill="both", expand=False)
        self._reg("frm_password", fp)

        inner = ttk.Frame(fp)
        inner.pack(fill="x", padx=PAD_INNER, pady=PAD_INNER)

        self.v_pw1 = tk.StringVar()
        self.v_pw2 = tk.StringVar()
        for col, (key, var) in enumerate([("lbl_pw_new", self.v_pw1),
                                          ("lbl_pw_rep", self.v_pw2)]):
            lbl = ttk.Label(inner, text=self._t(key), width=W_PW_LBL, anchor="w")
            lbl.grid(row=0, column=col * 2, sticky="w", padx=(0, PAD_BTN))
            self._reg(key, lbl)
            self._ttk_lw(ttk.Entry(inner, textvariable=var, show="*",
                                   width=PW_ENTRY_WIDTH)).grid(
                row=0, column=col * 2 + 1, sticky="w", padx=(0, 4))

        b_pw = self._lbtn(inner, self._t("btn_pw_set"), W_PWSET, self._save_pw)
        b_pw.grid(row=0, column=4)
        self._reg("btn_pw_set", b_pw)

        # Adjust frame (right)
        ext_f = ttk.LabelFrame(outer, text=self._t("frm_adjust"))
        ext_f.pack(side="right", padx=(8, 0), fill="both")
        self._reg("frm_adjust", ext_f)

        bf2 = ttk.Frame(ext_f)
        bf2.pack(fill="both", expand=True, padx=PAD_INNER, pady=PAD_INNER)
        self.btn_reduce = self._lbtn(bf2, "-", W_EXT, self._on_reduce,
                                     active_bg=C_RED,   active_fg=C_WHITE,
                                     bold=True, lockable=False)
        self.btn_reduce.pack(side="left", padx=(0, PAD_BTN))
        self.btn_extend = self._lbtn(bf2, "+", W_EXT, self._on_extend,
                                     active_bg=C_GREEN, active_fg=C_WHITE,
                                     bold=True, lockable=False)
        self.btn_extend.pack(side="left", padx=(PAD_BTN, 0))

    def _build_buttons(self) -> None:
        bf = ttk.Frame(self)
        bf.pack(fill="x", padx=PAD_OUTER, pady=(0, PAD_INNER))

        self.btn_reset = self._lbtn(bf, self._t("btn_reset"), W_SIDE, self.reset_timer)
        self.btn_reset.pack(side="right", padx=(PAD_ROW, 0))
        self._reg("btn_reset", self.btn_reset)

        self.btn_quit = self._lbtn(bf, self._t("btn_quit"), W_SIDE, self.exit_app)
        self.btn_quit.pack(side="right", padx=PAD_ROW)
        self._reg("btn_quit", self.btn_quit)

        self.btn_lock = self._lbtn(bf, self._t("btn_lock"), W_LOCK, self._on_lock_btn,
                                   lockable=False)
        self.btn_lock.w.pack(side="left", fill="x", expand=True,
                             padx=(0, PAD_ROW), ipady=BTN_PAD)

        # Inline password widgets (hidden until _enter_pw_mode)
        self.v_pw_inline   = tk.StringVar()
        self.pw_entry      = ttk.Entry(bf, textvariable=self.v_pw_inline, show="*", width=1)
        self.btn_pw_ok     = ttk.Button(bf, text="\u2714", width=3, command=self._check_pw)
        self.btn_pw_cancel = ttk.Button(bf, text="\u2716", width=3, command=self._exit_pw_mode)
        self.pw_entry.bind("<Return>", self._check_pw)
        self.pw_entry.bind("<Escape>", lambda e: self._exit_pw_mode())

    def _build_statusbar(self) -> None:
        sb = tk.Frame(self, bd=1, relief="sunken")
        sb.pack(fill="x", side="bottom")
        self.sb_dt = tk.Label(sb, text="", anchor="w",
                              padx=PAD_INNER, width=W_STATUSBAR_DT)
        self.sb_dt.pack(side="left")
        self.sb_login = tk.Label(sb, text="", anchor="w",
                                 padx=PAD_OUTER + 16, font=FONT_REM)
        self.sb_login.pack(side="left", fill="x", expand=True)
        self.sb_rem = tk.Label(sb, text="", anchor="e", padx=PAD_INNER,
                               font=FONT_REM, width=W_STATUSBAR_REM)
        self.sb_rem.pack(side="right")
