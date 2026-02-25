"""YourTime – application-wide constants (geometry, colours, timings, i18n)."""

# --- cycles / keys -----------------------------------------------------------
LANGS: list[str] = ["DE", "EN", "RU"]
DEFAULT_LANG:   str = "EN"
ACTION_KEYS:    list[str] = ["lock", "logoff"]
DEFAULT_ACTION: str = "lock"
ACTION_NEXT: dict[str, str] = {
    k: ACTION_KEYS[(i + 1) % len(ACTION_KEYS)] for i, k in enumerate(ACTION_KEYS)
}
DAYS_EN: list[str] = ["Monday","Tuesday","Wednesday","Thursday","Friday","Saturday","Sunday"]
DAY_CYCLE:  dict[str, str] = {"on": "range", "range": "off", "off": "on"}
DAY_COLORS: dict[str, str] = {"on": "#2ecc71", "range": "#f1c40f", "off": "#e74c3c"}

# --- priorities / sentinels --------------------------------------------------
MSG_PRIO: dict[str, int] = {"red": 0, "orange": 1, "blue": 2, "green": 3}
UNLIMITED: int = -1

# --- watchdog ----------------------------------------------------------------
WATCHDOG_SAVE_INTERVAL: int = 10

# --- autostart registry paths ------------------------------------------------
AUTOSTART_KEY          = r"Software\Microsoft\Windows\CurrentVersion\Run"
AUTOSTART_APPROVED_KEY = (r"Software\Microsoft\Windows\CurrentVersion"
                           r"\Explorer\StartupApproved\Run")
AUTOSTART_NAME         = "YourTime"
AUTOSTART_ENABLED_DATA = bytes([0x02]) + bytes(11)

# --- GUI widths (Tkinter character units) ------------------------------------
W_LANG    = 4; W_DAY     = 6; W_ACTION  = 10; W_SIDE    = 13; W_LOCK    = 10
W_EXT     = 9; W_PWSET   = 8; W_PW_LBL  = 13; W_SPINLBL = 20; W_ROW    = 7
W_SPINBOX = 6; W_ENTRY_TIME = 6; W_DAY_LIMIT = 6; W_AUTOSTART = 10
W_STATUSBAR_DT = 24; W_STATUSBAR_REM = 18

# --- padding -----------------------------------------------------------------
BTN_PAD = 3; PAD_OUTER = 10; PAD_INNER = 6; PAD_ROW = 2; PAD_BTN = 4

# --- per-day limit defaults --------------------------------------------------
DEFAULT_DAY_LIMIT_MIN = 60
DAY_LIMIT_MIN_LO = 1
DAY_LIMIT_MIN_HI = 1440

# --- fonts -------------------------------------------------------------------
FONT_NORMAL  = ("", 9)
FONT_BOLD    = ("", 9, "bold")
FONT_ROW_HDR = ("", 8, "bold")
FONT_REM     = ("", 9, "bold")

# --- timings (ms) ------------------------------------------------------------
TICK_MS               = 1000
STATUS_DURATION_MS    = 4000
TRIGGER_DURATION_MS   = 8000
WARN_FRONT_INTERVAL_MS = 1000
TRAY_ICON_SIZE: tuple[int, int] = (64, 64)
STARTUP_HIDE_DELAY_MS = 100

# --- colours -----------------------------------------------------------------
C_BLUE   = "#3498db"; C_GREEN  = "#27ae60"; C_RED    = "#e74c3c"
C_GRAY_N = "#d9d9d9"; C_WHITE  = "#ffffff"; C_BLACK  = "#000000"
C_DIS_BG = "#b5b5b5"; C_DIS_FG = "#707070"

# --- asset paths (relative to base dir) -------------------------------------
ICON_ICO_PATH: tuple[str, ...] = ("img", "icon.ico")
TRAY_ICO_PATH: tuple[str, ...] = ("img", "icon.ico")

# --- default config ----------------------------------------------------------
DEFAULT_CFG: dict = {
    "check_interval_seconds": 30, "extend_seconds": 30,
    "target_user": "", "password_hash": "",
    "language": DEFAULT_LANG, "action": DEFAULT_ACTION,
}

# --- i18n --------------------------------------------------------------------
LANG: dict[str, dict[str, str]] = {
    "DE": {
        "frm_settings": "Einstellungen", "frm_password": "Passwort", "frm_adjust": "Anpassen",
        "lbl_interval": "Prüfen [s]:", "lbl_extend": "Anpassen [s]:",
        "row_from": "Von", "row_to": "Bis", "row_timer": "Limit", "row_limit_min": "[min]",
        "lbl_pw_new": "Neu:", "lbl_pw_rep": "Wiederholen:", "btn_pw_set": "Setzen",
        "btn_save": "\U0001f4be Speichern", "btn_reset": "\u23f1 Reset",
        "btn_quit": "\U0001f6aa Beenden",
        "btn_lock": "\U0001f512 Entsperren", "btn_unlock": "\U0001f513 Sperren",
        "sb_allowed": "\U0001f513 Login entsperrt", "sb_denied": "\U0001f512 Login gesperrt",
        "msg_saved": "\u2705 Gespeichert.", "msg_reset": "\U0001f504 Limit zurückgesetzt.",
        "msg_extended": "\u23f1 +{s}s hinzugefügt.", "msg_reduced": "\u23f1 -{s}s abgezogen.",
        "msg_pw_set": "\u2705 Passwort gesetzt.", "msg_pw_removed": "\U0001f513 Kein Passwortschutz.",
        "msg_pw_mismatch": "\u274c Nicht gleich.", "msg_pw_wrong": "\u274c Falsches Passwort.",
        "msg_unlocked": "\U0001f513 Entsperrt.", "msg_no_pw": "\U0001f513 Kein Passwort.",
        "msg_cfg_err": "Config-Fehler: {e}", "msg_err": "\u274c {e}",
        "msg_timeout": "\u23f0 Tageslimit! Aktion...", "msg_blocked": "\u26d4 Sperrzeit! Aktion...",
        "msg_warn_min": "\u26a0\ufe0f Noch {m} min!", "tray_open": "\u2699 Öffnen",
        "msg_time_invalid": "\u274c Ungültige Uhrzeit (HH:MM).",
        "days_short": "Mo|Di|Mi|Do|Fr|Sa|So",
        "days_full": "Montag|Dienstag|Mittwoch|Donnerstag|Freitag|Samstag|Sonntag",
        "date_fmt": "{day}, {dt}",
        "unit_d": "T", "unit_h": "h", "unit_m": "m", "unit_s": "s",
        "action_lock": "Sperren", "action_logoff": "Abmelden", "lbl_action": "Aktion:",
        "lbl_autostart": "Autostart:", "btn_autostart_on": "AN", "btn_autostart_off": "AUS",
        "msg_autostart_on": "\u2705 Autostart aktiviert.",
        "msg_autostart_off": "\u274c Autostart deaktiviert.",
        "msg_autostart_err": "\u274c Autostart-Fehler: {e}",
    },
    "EN": {
        "frm_settings": "Settings", "frm_password": "Password", "frm_adjust": "Adjust",
        "lbl_interval": "Check [s]:", "lbl_extend": "Adjust [s]:",
        "row_from": "From", "row_to": "To", "row_timer": "Limit", "row_limit_min": "[min]",
        "lbl_pw_new": "New:", "lbl_pw_rep": "Repeat:", "btn_pw_set": "Set",
        "btn_save": "\U0001f4be Save", "btn_reset": "\u23f1 Reset",
        "btn_quit": "\U0001f6aa Quit",
        "btn_lock": "\U0001f512 Unlock", "btn_unlock": "\U0001f513 Lock",
        "sb_allowed": "\U0001f513 Login allowed", "sb_denied": "\U0001f512 Login blocked",
        "msg_saved": "\u2705 Saved.", "msg_reset": "\U0001f504 Limit reset.",
        "msg_extended": "\u23f1 +{s}s added.", "msg_reduced": "\u23f1 -{s}s reduced.",
        "msg_pw_set": "\u2705 Password set.", "msg_pw_removed": "\U0001f513 No password.",
        "msg_pw_mismatch": "\u274c Not equal.", "msg_pw_wrong": "\u274c Wrong password.",
        "msg_unlocked": "\U0001f513 Unlocked.", "msg_no_pw": "\U0001f513 No password.",
        "msg_cfg_err": "Config error: {e}", "msg_err": "\u274c {e}",
        "msg_timeout": "\u23f0 Time limit!", "msg_blocked": "\u26d4 Blocked!",
        "msg_warn_min": "\u26a0\ufe0f {m} min left!", "tray_open": "\u2699 Open",
        "msg_time_invalid": "\u274c Invalid time format (HH:MM).",
        "days_short": "Mo|Tu|We|Th|Fr|Sa|Su",
        "days_full": "Monday|Tuesday|Wednesday|Thursday|Friday|Saturday|Sunday",
        "date_fmt": "{day}, {dt}",
        "unit_d": "d", "unit_h": "h", "unit_m": "m", "unit_s": "s",
        "action_lock": "Lock", "action_logoff": "Log off", "lbl_action": "Action:",
        "lbl_autostart": "Autostart:", "btn_autostart_on": "ON", "btn_autostart_off": "OFF",
        "msg_autostart_on": "\u2705 Autostart enabled.",
        "msg_autostart_off": "\u274c Autostart disabled.",
        "msg_autostart_err": "\u274c Autostart error: {e}",
    },
    "RU": {
        "frm_settings": "Настройки", "frm_password": "Пароль", "frm_adjust": "Подстройка",
        "lbl_interval": "Проверка [с]:", "lbl_extend": "Подстройка [с]:",
        "row_from": "С", "row_to": "По", "row_timer": "Лимит", "row_limit_min": "[мин]",
        "lbl_pw_new": "Новый:", "lbl_pw_rep": "Повторить:", "btn_pw_set": "Задать",
        "btn_save": "\U0001f4be Сохранить", "btn_reset": "\u23f1 Сброс",
        "btn_quit": "\U0001f6aa Выход",
        "btn_lock": "\U0001f512 Открыть", "btn_unlock": "\U0001f513 Закрыть",
        "sb_allowed": "\U0001f513 Вход разрешён", "sb_denied": "\U0001f512 Вход запрещён",
        "msg_saved": "\u2705 Сохранено.", "msg_reset": "\U0001f504 Сброс лимита.",
        "msg_extended": "\u23f1 +{s}с добавлено.", "msg_reduced": "\u23f1 -{s}с убрано.",
        "msg_pw_set": "\u2705 Пароль задан.", "msg_pw_removed": "\U0001f513 Без пароля.",
        "msg_pw_mismatch": "\u274c Не совпадают.", "msg_pw_wrong": "\u274c Неверный пароль.",
        "msg_unlocked": "\U0001f513 Открыто.", "msg_no_pw": "\U0001f513 Без пароля.",
        "msg_cfg_err": "Ошибка конфига: {e}", "msg_err": "\u274c {e}",
        "msg_timeout": "\u23f0 Лимит!", "msg_blocked": "\u26d4 Запрет!",
        "msg_warn_min": "\u26a0\ufe0f Осталось {m} мин!", "tray_open": "\u2699 Открыть",
        "msg_time_invalid": "\u274c Неверный формат времени (ЧЧ:ММ).",
        "days_short": "Пн|Вт|Ср|Чт|Пт|Сб|Вс",
        "days_full": "Понедельник|Вторник|Среда|Четверг|Пятница|Суббота|Воскресенье",
        "date_fmt": "{day}, {dt}",
        "unit_d": "д", "unit_h": "ч", "unit_m": "м", "unit_s": "с",
        "action_lock": "Блок", "action_logoff": "Выход", "lbl_action": "Действие:",
        "lbl_autostart": "Автозапуск:", "btn_autostart_on": "ВКЛ", "btn_autostart_off": "ВЫКЛ",
        "msg_autostart_on": "\u2705 Автозапуск включён.",
        "msg_autostart_off": "\u274c Автозапуск отключён.",
        "msg_autostart_err": "\u274c Ошибка автозапуска: {e}",
    },
}
