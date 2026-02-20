# ⏱️ YourTime
☕ If it saves you nerves, time, or family arguments — a small support is always appreciated:

[Paypal](https://www.paypal.com/ncp/payment/NACHHUCV8EQH4)
`bitcoin:56YBrHBxgohqf5zs5TUS9KkAcqGDm`

> ⚠️ **Friendly disclaimer:** YourTime can automatically lock or log off your Windows session.  
> If you misconfigure it (for example with strict autostart rules or always‑blocked times), it may cause repeated logouts that you can only undo from Windows Safe Mode or by manually removing the config/autostart entry.  
> By using this tool, you accept that you are responsible for your own configuration and any impact on your system.

## Take back control over screen time — yours or your kids'.

YourTime is a lightweight Windows app that quietly runs in the background and enforces daily time limits per user. Set allowed hours, a countdown timer, or simply block certain days entirely. When time is up, the PC locks itself or logs the user off — no way around it without a password.

---

## How it works

After starting, YourTime **disappears into the system tray** — look for the clock icon next to the clock in the Windows taskbar (bottom right). Double-click it to open the settings. Everything is password-protected so the person being limited can't just switch it off.

When the remaining time drops into the warning zone, the window forces itself to the front and stays there. Closing or minimising it? It comes right back. The only way out is to wait — or enter the admin password.

---

## Features

- ⏰ **Daily time limit** with persistent countdown (survives reboots)
- 📅 **Per-day config** — always on, time window (e.g. 15:00–21:00), or fully blocked
- ⏱️ Optional **timer per day** — counts down only within the allowed window
- 🔒 **Password protection** for the settings panel
- 🖥️ **System tray** — runs silently in the background
- 🔁 **Autostart** — registers itself on first save, re-enables itself if manually disabled
- 🌍 UI languages: 🇩🇪 German · 🇬🇧 English · 🇷🇺 Russian
- 🚪 Enforcement: **Lock workstation** or **Log off**
- 🪟 Window stays in foreground when time is running out

- New feature requests are appreciated

---

## Installation (from source)

**Requirements:** Windows 10/11, Python 3.10+

```bash
pip install pystray pillow
python backend.py
```

The app starts directly to the **system tray** — no window opens.  
Find the ⏱️ icon in the taskbar notification area (bottom right corner, you may need to click the `^` arrow).  
Double-click to open settings.

---

## Build standalone EXE (no Python needed on target PC)

```bat
build.bat
```

Output: `dist\YourTime.exe` — copy the entire `dist\` folder anywhere.

> **Note:** Windows Defender may flag PyInstaller-built executables as suspicious.  
> Add an exclusion for the `dist\` folder, or right-click → Properties → Unblock.

---

## First-time setup

1. Double-click the tray icon to open settings
2. Click **🔓 Unlock** (no password yet — just confirm)
3. Configure days, time windows, and daily limit
4. Set an **admin password** so the target user can't change settings
5. Click **💾 Save**

From this point on, YourTime starts automatically with Windows and enforces the rules silently.

---

## Configuration

Settings are stored in `config.json` next to the executable. A default file is created on first run. See `config.example.json` for the full schema.

| Field | Description |
|---|---|
| `target_user` | Windows username to enforce (set automatically on Save) |
| `logout_after_minutes` | Daily screen time limit in minutes |
| `check_interval_seconds` | How often the watchdog re-evaluates the situation |
| `extend_seconds` | Step size for the +/– quick-adjust buttons |
| `action` | `"lock"` or `"logoff"` when time runs out |
| `allowed_times` | Per-day rules (enabled, time window, timer on/off) |

---

## Project structure

```
YourTime/
├── backend.py         # Business logic, watchdog thread, entry point
├── frontend.py        # Tkinter GUI
├── definitions.py     # Constants, colours, i18n strings
├── build.bat          # PyInstaller one-click build
├── config.example.json
└── tools/
    icon.py
    icon.ico
```

---

## License

**MIT License** with **Commons Clause**

Free to use, modify, and share. You may **not** sell this software or offer it as a paid product or service. If you build something on top of it, same rules apply.

In short: use it freely, don't make money off it without asking first.

```
MIT License + Commons Clause (License Condition v1.0)

The Software is provided under the MIT License. The following condition is added:

Without the express written permission of the author, no person or organization
may sell, rent, or otherwise commercialize the Software or a Substantial Portion
of it. "Sell" means providing the Software to third parties for a fee, where the
primary value derives from the Software's functionality.
```
