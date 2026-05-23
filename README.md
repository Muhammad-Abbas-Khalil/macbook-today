# MacBook Today 🖥️

A beautiful, interactive personal dashboard that summarizes everything you did on your MacBook today — files modified, terminal commands, git commits, Spotify activity, disk/battery stats, and more. Runs locally on macOS and displays a stunning glassmorphic web UI.

**Live Demo:** [macbooktoday.netlify.app](https://macbooktoday.netlify.app)

---

## What It Does

Every time you run it, `dashboard_collector.py` scans your machine and generates a snapshot of your day:

- 📁 **Files modified** in the last 24 hours across Desktop, Downloads, and Documents
- 🖥️ **Terminal commands** from your `~/.zsh_history`
- 🔀 **Git commits** across all local repositories
- 🎵 **Spotify** — currently playing track + today's listening history
- 🗑️ **Trash** contents with sizes
- 📊 **System stats** — battery, disk usage
- ⏱️ **Active time estimate** based on file edit patterns
- 🌈 **Work vibe** — auto-detected mood based on your activity

The data is written to `dashboard_data.js` which the frontend (`index.html`) reads and renders.

---

## Screenshots

> The dashboard running with live data on macOS.

![MacBook Today Dashboard](screenshot.png)

---

## Tech Stack

| Layer | Technology |
|---|---|
| Data Collector | Python 3 (stdlib only — no pip installs needed) |
| Frontend | HTML5, CSS3, Vanilla JavaScript |
| Styling | Tailwind CSS (CDN), custom glassmorphism CSS |
| Icons | Lucide Icons (CDN) |
| Fonts | Google Fonts — Inter, Outfit, Fira Code |
| Shell Script | Bash (`view_today.sh`) |
| Deployment | Netlify (Live Demo mode with sample data) |
| Platform | macOS only (uses `osascript`, `pmset`, `sysctl`) |

---

## Project Structure

```
macbook-today/
├── dashboard_collector.py   # Python script — collects all activity data
├── index.html               # Frontend dashboard UI
├── view_today.sh            # One-command launcher script
├── .gitignore
└── README.md
```

> `dashboard_data.js` is generated at runtime and is gitignored. It is never committed.

---

## Prerequisites

- macOS (required — the collector uses macOS-specific tools)
- Python 3.6 or higher
- Zsh shell (for terminal history parsing)
- A modern browser (Chrome, Safari, Firefox)

No external Python packages are required. The collector uses only Python's standard library.

---

## Setup & Installation

### 1. Clone the repository

```bash
git clone https://github.com/Muhammad-Abbas-Khalil/macbook-today.git
cd macbook-today
```

### 2. Configure your scan paths

Open `dashboard_collector.py` and update the paths at the top to match your username:

```python
SCAN_PATHS = [
    "/Users/YOUR_USERNAME/Desktop",
    "/Users/YOUR_USERNAME/Downloads",
    "/Users/YOUR_USERNAME/Documents"
]
```

Also update these functions inside the file:

- `get_git_commits()` — update `search_dirs` list
- `get_system_stats()` — update the `shutil.disk_usage()` path
- `get_trash_details()` — uses `~/.Trash` automatically (no change needed)

> **Tip:** You can replace all `/Users/Abbas/` occurrences with your own username using find-and-replace.

### 3. Make the shell script executable

```bash
chmod +x view_today.sh
```

### 4. Update the shell script paths

Open `view_today.sh` and update the two paths:

```bash
python3 /Users/YOUR_USERNAME/path/to/dashboard_collector.py
open /Users/YOUR_USERNAME/path/to/index.html
```

---

## Running It

### Option A — One command (recommended)

```bash
./view_today.sh
```

This runs the collector and opens the dashboard in your default browser automatically.

### Option B — Manual

```bash
python3 dashboard_collector.py
open index.html
```

---

## Auto-Run on Login (Optional)

To have the dashboard refresh automatically, you can set up a macOS `launchd` job.

Create a file at `~/Library/LaunchAgents/com.macbook-today.plist`:

```xml
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN"
  "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.macbook-today</string>
    <key>ProgramArguments</key>
    <array>
        <string>/usr/bin/python3</string>
        <string>/Users/YOUR_USERNAME/path/to/dashboard_collector.py</string>
    </array>
    <key>StartInterval</key>
    <integer>1800</integer> <!-- runs every 30 minutes -->
    <key>RunAtLoad</key>
    <true/>
</dict>
</plist>
```

Then load it:

```bash
launchctl load ~/Library/LaunchAgents/com.macbook-today.plist
```

---

## How the Collector Works

```
dashboard_collector.py
│
├── get_modified_files()      → scans Desktop/Downloads/Documents for files touched in last 24h
├── get_zsh_history()         → parses ~/.zsh_history for recent commands
├── get_git_commits()         → runs `git log --since=midnight` in detected repos
├── get_system_stats()        → disk via shutil, battery via pmset, RAM via sysctl
├── get_spotify_status()      → queries Spotify via osascript (AppleScript)
├── get_trash_details()       → scans ~/.Trash
├── calculate_active_time()   → estimates productive hours from file edit timestamps
├── get_day_segments()        → breaks activity into Morning/Afternoon/Evening/Night
└── get_active_workspaces()   → detects which project folders were most active
```

All data is written as `window.dashboardData = {...}` into `dashboard_data.js`.

---

## What Gets Ignored

The collector automatically skips:

- `node_modules`, `.git`, `.venv`, `venv`, `__pycache__`
- `Library`, `Applications`
- Hidden files and directories (starting with `.`)
- Temp files starting with `~$`
- Directories deeper than 4 levels

---

## .gitignore

The following are excluded from the repo:

```
dashboard_data.js
dashboard_data.json
.spotify_history.json
*.pyc
__pycache__/
```

---

## Notes

- **Spotify integration** uses AppleScript and only works if Spotify is installed. If it's not running, the section is gracefully skipped.
- **Battery info** uses `pmset` which is macOS-only.
- **zsh history timestamps** — if your zsh history doesn't have timestamps enabled, commands will show as "Recently" without an exact time. To enable timestamps, add `setopt EXTENDED_HISTORY` to your `~/.zshrc`.
- The Netlify deployment shows a **Live Demo** mode with sample data since `dashboard_data.js` is not committed.

---

## License

MIT — feel free to fork, modify, and make it your own.

---

## Author

**Muhammad Abbas Khalil**
[GitHub](https://github.com/Muhammad-Abbas-Khalil) 
