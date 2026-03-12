"""YourTime – all constants, defaults, and i18n strings.

Sorted by layer of use:
  1. App identity
  2. Backend – domain / scheduling
  3. Backend – persistence & system
  4. Backend – i18n / formatting
  5. Frontend – GUI geometry (order mirrors layout top→bottom, left→right)
  6. Frontend – fonts, colours, timings
  7. Frontend – asset paths
"""

# ---------------------------------------------------------------------------
# 1. App identity
# ---------------------------------------------------------------------------
APP_NAME: str = "YourTime"
APP_MUTEX: str = "YourTime_SingleInstance"
CONFIG_FILENAME: str = "config.json"
LOG_FILENAME: str    = "error.log"
LOG_MAX_BYTES: int   = 100_000

# ---------------------------------------------------------------------------
# 2. Backend – domain / scheduling
# ---------------------------------------------------------------------------
LANGS: list[str]       = ["DE", "EN", "RU"]
DEFAULT_LANG: str      = "EN"

ACTION_KEYS: list[str] = ["lock", "logoff"]
DEFAULT_ACTION: str    = "lock"
ACTION_NEXT: dict[str, str] = {k: ACTION_KEYS[(i + 1) % len(ACTION_KEYS)]
                                for i, k in enumerate(ACTION_KEYS)}

DAYS_EN: list[str] = ["Monday", "Tuesday", "Wednesday", "Thursday",
                       "Friday", "Saturday", "Sunday"]
DAY_CYCLE:  dict[str, str] = {"on": "range", "range": "off", "off": "on"}
DAY_COLORS: dict[str, str] = {"on": "#2ecc71", "range": "#f1c40f", "off": "#e74c3c"}

# Sentinel: remaining == UNLIMITED → no time constraint active
UNLIMITED: int = -1

# Watchdog tick / grace period (seconds)
DEFAULT_TAKT_SEC: int = 30
TAKT_SEC_LO:      int = 1
TAKT_SEC_HI:      int = 86_400

# Watchdog: wall-clock gap > this on a ~1 s tick → OS woke from sleep
WATCHDOG_SLEEP_GAP_SEC: int = 3

# Per-day usage log retained for this many days
USAGE_RETENTION_DAYS: int = 30

# Per-day timer limit (minutes)
DEFAULT_DAY_LIMIT_MIN: int = 60
DAY_LIMIT_MIN_LO:      int = 1
DAY_LIMIT_MIN_HI:      int = 1_440   # 24 h

# calc_remaining: cap lookahead at 7 days
REMAINING_MAX_DAYS: int = 7

# Default config written on first run
DEFAULT_CFG: dict = {
    "takt_seconds":  DEFAULT_TAKT_SEC,
    "password_hash": "",
    "language":      DEFAULT_LANG,
    "action":        DEFAULT_ACTION,
}

# ---------------------------------------------------------------------------
# 3. Backend – persistence & system (autostart registry)
# ---------------------------------------------------------------------------
AUTOSTART_KEY: str = r"Software\Microsoft\Windows\CurrentVersion\Run"
AUTOSTART_APPROVED_KEY: str = (r"Software\Microsoft\Windows\CurrentVersion"
                                r"\Explorer\StartupApproved\Run")
AUTOSTART_NAME:         str   = APP_NAME
AUTOSTART_ENABLED_DATA: bytes = bytes([0x02]) + bytes(11)

# ---------------------------------------------------------------------------
# 4. Backend – i18n / formatting
# ---------------------------------------------------------------------------
LANG: dict[str, dict[str, str]] = {
    "DE": {
        "frm_settings": "Einstellungen", "frm_password": "Passwort", "frm_adjust": "Anpassen",
        "lbl_lang": "Sprache:", "lbl_action": "Aktion:", "lbl_takt": "Takt [s]:",
        "lbl_autostart": "Autostart:",
        "row_from": "Von", "row_to": "Bis", "row_timer": "Limit", "row_limit_min": "[min]",
        "lbl_pw_new": "Neu:", "lbl_pw_rep": "Wiederholen:", "btn_pw_set": "Setzen",
        "btn_lock": "\U0001f512 Entsperren", "btn_unlock": "\U0001f513 Sperren",
        "btn_reset": "\u23f1 Reset", "btn_quit": "\U0001f6aa Beenden",
        "btn_autostart_on": "AN", "btn_autostart_off": "AUS",
        "sb_allowed": "\U0001f513 Login entsperrt", "sb_denied": "\U0001f512 Login gesperrt",
        "msg_reset": "\U0001f504 Limit zurückgesetzt.",
        "msg_extended": "\u23f1 +{s}s hinzugefügt.", "msg_reduced": "\u23f1 -{s}s abgezogen.",
        "msg_pw_set": "\u2705 Passwort gesetzt.", "msg_pw_removed": "\U0001f513 Kein Passwortschutz.",
        "msg_pw_mismatch": "\u274c Nicht gleich.", "msg_pw_wrong": "\u274c Falsches Passwort.",
        "msg_unlocked": "\U0001f513 Entsperrt.", "msg_no_pw": "\U0001f513 Kein Passwort.",
        "msg_cfg_err": "Config-Fehler: {e}", "msg_err": "\u274c {e}",
        "msg_timeout": "\u23f0 Tageslimit! Aktion...", "msg_blocked": "\u26d4 Sperrzeit! Aktion...",
        "msg_warn_min": "\u26a0\ufe0f Noch {m} min!", "tray_open": "\u2699 Öffnen",
        "msg_time_invalid": "\u274c Ungültige Uhrzeit (HH:MM).",
        "msg_autostart_on":  "\u2705 Autostart aktiviert.",
        "msg_autostart_off": "\u274c Autostart deaktiviert.",
        "msg_autostart_err": "\u274c Autostart-Fehler: {e}",
        "days_short": "Mo|Di|Mi|Do|Fr|Sa|So",
        "days_full":  "Montag|Dienstag|Mittwoch|Donnerstag|Freitag|Samstag|Sonntag",
        "date_fmt": "{day}, {dt}",
        "unit_d": "T", "unit_h": "h", "unit_m": "m", "unit_s": "s",
        "action_lock": "Sperren", "action_logoff": "Abmelden",
    },
    "EN": {
        "frm_settings": "Settings", "frm_password": "Password", "frm_adjust": "Adjust",
        "lbl_lang": "Language:", "lbl_action": "Action:", "lbl_takt": "Cycle [s]:",
        "lbl_autostart": "Autostart:",
        "row_from": "From", "row_to": "To", "row_timer": "Limit", "row_limit_min": "[min]",
        "lbl_pw_new": "New:", "lbl_pw_rep": "Repeat:", "btn_pw_set": "Set",
        "btn_lock": "\U0001f512 Unlock", "btn_unlock": "\U0001f513 Lock",
        "btn_reset": "\u23f1 Reset", "btn_quit": "\U0001f6aa Quit",
        "btn_autostart_on": "ON", "btn_autostart_off": "OFF",
        "sb_allowed": "\U0001f513 Login allowed", "sb_denied": "\U0001f512 Login blocked",
        "msg_reset": "\U0001f504 Limit reset.",
        "msg_extended": "\u23f1 +{s}s added.", "msg_reduced": "\u23f1 -{s}s reduced.",
        "msg_pw_set": "\u2705 Password set.", "msg_pw_removed": "\U0001f513 No password.",
        "msg_pw_mismatch": "\u274c Not equal.", "msg_pw_wrong": "\u274c Wrong password.",
        "msg_unlocked": "\U0001f513 Unlocked.", "msg_no_pw": "\U0001f513 No password.",
        "msg_cfg_err": "Config error: {e}", "msg_err": "\u274c {e}",
        "msg_timeout": "\u23f0 Time limit!", "msg_blocked": "\u26d4 Blocked!",
        "msg_warn_min": "\u26a0\ufe0f {m} min left!", "tray_open": "\u2699 Open",
        "msg_time_invalid": "\u274c Invalid time format (HH:MM).",
        "msg_autostart_on":  "\u2705 Autostart enabled.",
        "msg_autostart_off": "\u274c Autostart disabled.",
        "msg_autostart_err": "\u274c Autostart error: {e}",
        "days_short": "Mo|Tu|We|Th|Fr|Sa|Su",
        "days_full":  "Monday|Tuesday|Wednesday|Thursday|Friday|Saturday|Sunday",
        "date_fmt": "{day}, {dt}",
        "unit_d": "d", "unit_h": "h", "unit_m": "m", "unit_s": "s",
        "action_lock": "Lock", "action_logoff": "Log off",
    },
    "RU": {
        "frm_settings": "Настройки", "frm_password": "Пароль", "frm_adjust": "Подстройка",
        "lbl_lang": "Язык:", "lbl_action": "Действие:", "lbl_takt": "Такт [с]:",
        "lbl_autostart": "Автозапуск:",
        "row_from": "С", "row_to": "По", "row_timer": "Лимит", "row_limit_min": "[мин]",
        "lbl_pw_new": "Новый:", "lbl_pw_rep": "Повторить:", "btn_pw_set": "Задать",
        "btn_lock": "\U0001f512 Открыть", "btn_unlock": "\U0001f513 Закрыть",
        "btn_reset": "\u23f1 Сброс", "btn_quit": "\U0001f6aa Выход",
        "btn_autostart_on": "ВКЛ", "btn_autostart_off": "ВЫКЛ",
        "sb_allowed": "\U0001f513 Вход разрешён", "sb_denied": "\U0001f512 Вход запрещён",
        "msg_reset": "\U0001f504 Сброс лимита.",
        "msg_extended": "\u23f1 +{s}с добавлено.", "msg_reduced": "\u23f1 -{s}с убрано.",
        "msg_pw_set": "\u2705 Пароль задан.", "msg_pw_removed": "\U0001f513 Без пароля.",
        "msg_pw_mismatch": "\u274c Не совпадают.", "msg_pw_wrong": "\u274c Неверный пароль.",
        "msg_unlocked": "\U0001f513 Открыто.", "msg_no_pw": "\U0001f513 Без пароля.",
        "msg_cfg_err": "Ошибка конфига: {e}", "msg_err": "\u274c {e}",
        "msg_timeout": "\u23f0 Лимит!", "msg_blocked": "\u26d4 Запрет!",
        "msg_warn_min": "\u26a0\ufe0f Осталось {m} мин!", "tray_open": "\u2699 Открыть",
        "msg_time_invalid": "\u274c Неверный формат времени (ЧЧ:ММ).",
        "msg_autostart_on":  "\u2705 Автозапуск включён.",
        "msg_autostart_off": "\u274c Автозапуск отключён.",
        "msg_autostart_err": "\u274c Ошибка автозапуска: {e}",
        "days_short": "Пн|Вт|Ср|Чт|Пт|Сб|Вс",
        "days_full":  "Понедельник|Вторник|Среда|Четверг|Пятница|Суббота|Воскресенье",
        "date_fmt": "{day}, {dt}",
        "unit_d": "д", "unit_h": "ч", "unit_m": "м", "unit_s": "с",
        "action_lock": "Блок", "action_logoff": "Выход",
    },
}

# ---------------------------------------------------------------------------
# 5. Frontend – GUI geometry (top→bottom, left→right within each panel)
# ---------------------------------------------------------------------------

# Window title
WIN_TITLE: str = APP_NAME

# Default time strings pre-filled in day entries
DAY_DEFAULT_START: str = "08:00"
DAY_DEFAULT_END:   str = "20:00"

# Password entry width (characters)
PW_ENTRY_WIDTH: int = 18

# Status-bar message priority: lower number = higher priority (red overrides all)
MSG_PRIO: dict[str, int] = {"red": 0, "orange": 1, "blue": 2, "green": 3}

# Widget widths (Tkinter character units) – settings frame, left→right
W_DAY:      int = 6   # day-cycle button
W_ROW:      int = 7   # row-header label (From/To/Limit/[min])
W_ENTRY_TIME: int = 6 # start/end time entry
W_DAY_LIMIT:  int = 6 # per-day limit spinbox
W_SPINLBL:  int = 12  # right-panel label column
W_LANG:     int = 7   # language cycle button
W_AUTOSTART: int = 7  # autostart toggle button
W_ACTION:   int = 7   # action cycle button
W_SPINBOX:  int = 6   # takt spinbox

# Widget widths – password row
W_PW_LBL: int = 12    # "New:" / "Repeat:" labels
W_PWSET:  int = 7     # "Set" button

# Widget widths – adjust frame
W_EXT: int = 8        # extend / reduce buttons

# Widget widths – bottom action row
W_LOCK: int = 7       # lock/unlock button
W_SIDE: int = 15      # Reset / Quit buttons

# Widget widths – status bar
W_STATUSBAR_DT:  int = 20
W_STATUSBAR_REM: int = 14

# Padding (pixels / Tkinter units)
PAD_OUTER: int = 8    # outer frame margin
PAD_INNER: int = 5    # inner frame padding
PAD_ROW:   int = 1    # row spacing in day grid
PAD_BTN:   int = 3    # horizontal button gap
BTN_PAD:   int = 4    # ipady for LBtn (vertical height)

# ---------------------------------------------------------------------------
# 6. Frontend – fonts, colours, timings
# ---------------------------------------------------------------------------

FONT_NORMAL:  tuple = ("", 9)
FONT_BOLD:    tuple = ("", 9, "bold")
FONT_ROW_HDR: tuple = ("", 8, "bold")
FONT_REM:     tuple = ("", 9, "bold")

C_BLUE:   str = "#3498db"
C_GREEN:  str = "#27ae60"
C_RED:    str = "#e74c3c"
C_GRAY_N: str = "#d9d9d9"
C_WHITE:  str = "#ffffff"
C_BLACK:  str = "#000000"
C_DIS_BG: str = "#b5b5b5"   # disabled background
C_DIS_FG: str = "#707070"   # disabled foreground

# GUI tick interval
TICK_MS: int = 1_000

# Status-bar message auto-clear delay
STATUS_DURATION_MS:  int = 4_000
# Enforcement trigger message stays longer
TRIGGER_DURATION_MS: int = 8_000

# Warn-zone: foreground-enforcement poll interval
WARN_FRONT_INTERVAL_MS: int = 1_000

# After iconify() wait before withdraw() to avoid taskbar flash
STARTUP_HIDE_DELAY_MS: int = 100

# Topmost lifted after this many ms to release focus grab
TOPMOST_RELEASE_MS: int = 200

# ---------------------------------------------------------------------------
# 7. Frontend – asset paths (relative to base dir)
# ---------------------------------------------------------------------------
ICON_ICO_PATH: tuple[str, ...] = ("img", "icon.ico")
TRAY_ICO_PATH: tuple[str, ...] = ("img", "icon.ico")
TRAY_ICON_SIZE: tuple[int, int] = (64, 64)
