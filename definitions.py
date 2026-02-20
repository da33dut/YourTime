LANGS = ["DE", "EN", "RU"]
ACTION_KEYS = ["lock", "logoff"]
ACTION_NEXT = {k: ACTION_KEYS[(i + 1) % len(ACTION_KEYS)] for i, k in enumerate(ACTION_KEYS)}
DAYS_EN = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
DAY_CYCLE = {"on": "range", "range": "off", "off": "on"}
DAY_COLORS = {"on": "#2ecc71", "range": "#f1c40f", "off": "#e74c3c"}
MSG_PRIO = {"red": 0, "orange": 1, "blue": 2, "green": 3}
UNLIMITED = -1

W_LANG = 4; W_DAY = 6; W_ACTION = 10; W_SIDE = 13; W_LOCK = 16
W_EXT = 9; W_PWSET = 8; W_PW_LBL = 13; W_SPINLBL = 20; W_ROW = 7; BTN_PAD = 3

C_BLUE = "#3498db"; C_GREEN = "#27ae60"; C_RED = "#e74c3c"
C_GRAY_N = "#d9d9d9"; C_WHITE = "#ffffff"; C_BLACK = "#000000"
C_DIS_BG = "#b5b5b5"; C_DIS_FG = "#707070"

DEFAULT_CFG = {
    "logout_after_minutes": 60, "check_interval_seconds": 30,
    "extend_seconds": 30, "target_user": "", "password_hash": "",
    "language": "DE", "action": "lock",
}

LANG = {
    "DE": {
        "frm_settings": "Einstellungen", "frm_password": "Passwort", "frm_adjust": "Anpassen",
        "lbl_logout": "Tageslimit (Min):", "lbl_interval": "Pruefen (Sek):", "lbl_extend": "Anpassen (Sek):",
        "row_from": "Von", "row_to": "Bis", "row_timer": "Timer",
        "lbl_pw_new": "Neu:", "lbl_pw_rep": "Wiederholen:", "btn_pw_set": "Setzen",
        "btn_save": "\U0001f4be Speichern", "btn_reset": "\u23f1 Reset", "btn_quit": "\U0001f6aa Beenden",
        "btn_lock": "\U0001f512 Entsperren", "btn_unlock": "\U0001f513 Sperren",
        "sb_allowed": "\U0001f513 Login entsperrt", "sb_denied": "\U0001f512 Login gesperrt",
        "msg_saved": "\u2705 Gespeichert.", "msg_reset": "\U0001f504 Timer zurueckgesetzt.",
        "msg_extended": "\u23f1 +{s}s hinzugefuegt.", "msg_reduced": "\u23f1 -{s}s abgezogen.",
        "msg_pw_set": "\u2705 Passwort gesetzt.", "msg_pw_removed": "\U0001f513 Kein Passwortschutz.",
        "msg_pw_mismatch": "\u274c Nicht gleich.", "msg_pw_wrong": "\u274c Falsches Passwort.",
        "msg_unlocked": "\U0001f513 Entsperrt.", "msg_no_pw": "\U0001f513 Kein Passwort.",
        "msg_cfg_err": "Config-Fehler: {e}", "msg_err": "\u274c {e}",
        "msg_timeout": "\u23f0 Tageslimit! Aktion...", "msg_blocked": "\u26d4 Sperrzeit! Aktion...",
        "msg_warn_min": "\u26a0\ufe0f Noch {m} Min!", "tray_open": "\u2699 Oeffnen",
        "days_short": "Mo|Di|Mi|Do|Fr|Sa|So",
        "days_full": "Montag|Dienstag|Mittwoch|Donnerstag|Freitag|Samstag|Sonntag",
        "date_fmt": "{day}, {dt}",
        "unit_d": "T", "unit_h": "h", "unit_m": "m", "unit_s": "s",
        "action_lock": "Sperren", "action_logoff": "Abmelden", "lbl_action": "Aktion:",
    },
    "EN": {
        "frm_settings": "Settings", "frm_password": "Password", "frm_adjust": "Adjust",
        "lbl_logout": "Daily limit (min):", "lbl_interval": "Check (sec):", "lbl_extend": "Adjust (sec):",
        "row_from": "From", "row_to": "To", "row_timer": "Timer",
        "lbl_pw_new": "New:", "lbl_pw_rep": "Repeat:", "btn_pw_set": "Set",
        "btn_save": "\U0001f4be Save", "btn_reset": "\u23f1 Reset", "btn_quit": "\U0001f6aa Quit",
        "btn_lock": "\U0001f512 Unlock", "btn_unlock": "\U0001f513 Lock",
        "sb_allowed": "\U0001f513 Login allowed", "sb_denied": "\U0001f512 Login blocked",
        "msg_saved": "\u2705 Saved.", "msg_reset": "\U0001f504 Timer reset.",
        "msg_extended": "\u23f1 +{s}s added.", "msg_reduced": "\u23f1 -{s}s reduced.",
        "msg_pw_set": "\u2705 Password set.", "msg_pw_removed": "\U0001f513 No password.",
        "msg_pw_mismatch": "\u274c Not equal.", "msg_pw_wrong": "\u274c Wrong password.",
        "msg_unlocked": "\U0001f513 Unlocked.", "msg_no_pw": "\U0001f513 No password.",
        "msg_cfg_err": "Config error: {e}", "msg_err": "\u274c {e}",
        "msg_timeout": "\u23f0 Time limit!", "msg_blocked": "\u26d4 Blocked!",
        "msg_warn_min": "\u26a0\ufe0f {m} min left!", "tray_open": "\u2699 Open",
        "days_short": "Mo|Tu|We|Th|Fr|Sa|Su",
        "days_full": "Monday|Tuesday|Wednesday|Thursday|Friday|Saturday|Sunday",
        "date_fmt": "{day}, {dt}",
        "unit_d": "d", "unit_h": "h", "unit_m": "m", "unit_s": "s",
        "action_lock": "Lock", "action_logoff": "Log off", "lbl_action": "Action:",
    },
    "RU": {
        "frm_settings": "\u041d\u0430\u0441\u0442\u0440\u043e\u0439\u043a\u0438",
        "frm_password": "\u041f\u0430\u0440\u043e\u043b\u044c",
        "frm_adjust": "\u041f\u043e\u0434\u0441\u0442\u0440\u043e\u0439\u043a\u0430",
        "lbl_logout": "\u041b\u0438\u043c\u0438\u0442 \u0434\u043d\u044f (\u043c\u0438\u043d):",
        "lbl_interval": "\u041f\u0440\u043e\u0432\u0435\u0440\u043a\u0430 (\u0441):",
        "lbl_extend": "\u041f\u043e\u0434\u0441\u0442\u0440\u043e\u0439\u043a\u0430 (\u0441):",
        "row_from": "\u0421", "row_to": "\u041f\u043e", "row_timer": "\u0422\u0430\u0439\u043c\u0435\u0440",
        "lbl_pw_new": "\u041d\u043e\u0432\u044b\u0439:", "lbl_pw_rep": "\u041f\u043e\u0432\u0442\u043e\u0440\u0438\u0442\u044c:",
        "btn_pw_set": "\u0417\u0430\u0434\u0430\u0442\u044c",
        "btn_save": "\U0001f4be \u0421\u043e\u0445\u0440\u0430\u043d\u0438\u0442\u044c",
        "btn_reset": "\u23f1 \u0421\u0431\u0440\u043e\u0441",
        "btn_quit": "\U0001f6aa \u0412\u044b\u0445\u043e\u0434",
        "btn_lock": "\U0001f512 \u041e\u0442\u043a\u0440\u044b\u0442\u044c",
        "btn_unlock": "\U0001f513 \u0417\u0430\u043a\u0440\u044b\u0442\u044c",
        "sb_allowed": "\U0001f513 \u0412\u0445\u043e\u0434 \u0440\u0430\u0437\u0440\u0435\u0448\u0451\u043d",
        "sb_denied": "\U0001f512 \u0412\u0445\u043e\u0434 \u0437\u0430\u043f\u0440\u0435\u0449\u0451\u043d",
        "msg_saved": "\u2705 \u0421\u043e\u0445\u0440\u0430\u043d\u0435\u043d\u043e.",
        "msg_reset": "\U0001f504 \u0421\u0431\u0440\u043e\u0441 \u0442\u0430\u0439\u043c\u0435\u0440\u0430.",
        "msg_extended": "\u23f1 +{s}\u0441 \u0434\u043e\u0431\u0430\u0432\u043b\u0435\u043d\u043e.",
        "msg_reduced": "\u23f1 -{s}\u0441 \u0443\u0431\u0440\u0430\u043d\u043e.",
        "msg_pw_set": "\u2705 \u041f\u0430\u0440\u043e\u043b\u044c \u0437\u0430\u0434\u0430\u043d.",
        "msg_pw_removed": "\U0001f513 \u0411\u0435\u0437 \u043f\u0430\u0440\u043e\u043b\u044f.",
        "msg_pw_mismatch": "\u274c \u041d\u0435 \u0441\u043e\u0432\u043f\u0430\u0434\u0430\u044e\u0442.",
        "msg_pw_wrong": "\u274c \u041d\u0435\u0432\u0435\u0440\u043d\u044b\u0439 \u043f\u0430\u0440\u043e\u043b\u044c.",
        "msg_unlocked": "\U0001f513 \u041e\u0442\u043a\u0440\u044b\u0442\u043e.",
        "msg_no_pw": "\U0001f513 \u0411\u0435\u0437 \u043f\u0430\u0440\u043e\u043b\u044f.",
        "msg_cfg_err": "\u041e\u0448\u0438\u0431\u043a\u0430 \u043a\u043e\u043d\u0444\u0438\u0433\u0430: {e}",
        "msg_err": "\u274c {e}",
        "msg_timeout": "\u23f0 \u041b\u0438\u043c\u0438\u0442!",
        "msg_blocked": "\u26d4 \u0417\u0430\u043f\u0440\u0435\u0442!",
        "msg_warn_min": "\u26a0\ufe0f \u041e\u0441\u0442\u0430\u043b\u043e\u0441\u044c {m} \u043c\u0438\u043d!",
        "tray_open": "\u2699 \u041e\u0442\u043a\u0440\u044b\u0442\u044c",
        "days_short": "\u041f\u043d|\u0412\u0442|\u0421\u0440|\u0427\u0442|\u041f\u0442|\u0421\u0431|\u0412\u0441",
        "days_full": "\u041f\u043e\u043d\u0435\u0434\u0435\u043b\u044c\u043d\u0438\u043a|\u0412\u0442\u043e\u0440\u043d\u0438\u043a|\u0421\u0440\u0435\u0434\u0430|\u0427\u0435\u0442\u0432\u0435\u0440\u0433|\u041f\u044f\u0442\u043d\u0438\u0446\u0430|\u0421\u0443\u0431\u0431\u043e\u0442\u0430|\u0412\u043e\u0441\u043a\u0440\u0435\u0441\u0435\u043d\u044c\u0435",
        "date_fmt": "{day}, {dt}",
        "unit_d": "\u0434", "unit_h": "\u0447", "unit_m": "\u043c", "unit_s": "\u0441",
        "action_lock": "\u0411\u043b\u043e\u043a\u0438\u0440\u043e\u0432\u043a\u0430",
        "action_logoff": "\u0412\u044b\u0445\u043e\u0434",
        "lbl_action": "\u0414\u0435\u0439\u0441\u0442\u0432\u0438\u0435:",
    },
}
