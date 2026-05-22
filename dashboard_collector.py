#!/usr/bin/env python3
import os
import sys
import json
import time
import datetime
import shutil
import subprocess
import re

# Folders to scan
SCAN_PATHS = [
    "/Users/Abbas/Desktop",
    "/Users/Abbas/Downloads",
    "/Users/Abbas/Documents"
]

# Folders to ignore entirely
IGNORE_DIRS = {
    "node_modules", ".git", ".venv", "venv", "env", "__pycache__", 
    "Library", "Applications", ".gemini", ".antigravity", "Photo Booth Library",
    "Photos Library.photoslibrary"
}

def format_timestamp(epoch):
    dt = datetime.datetime.fromtimestamp(epoch)
    return dt.strftime("%Y-%m-%d %I:%M %p")

def is_today(epoch):
    dt = datetime.datetime.fromtimestamp(epoch)
    today = datetime.datetime.today()
    return dt.date() == today.date()

def classify_file(filename, filepath):
    ext = os.path.splitext(filename)[1].lower()
    name_lower = filename.lower()
    path_lower = filepath.lower()
    
    # 1. Screenshots
    if name_lower.startswith("screenshot") or "screen shot" in name_lower:
        return "Screenshot"
        
    # 2. Academic
    academic_keywords = ["assignment", "lab", "quiz", "exam", "lecture", "course", "project", "presentation", "practices", "midterm"]
    academic_dirs = ["academic", "myassignments", "ariyan_assignments", "cc", "hci", "ml", "pp", "dsa", "dsa-lab", "ml-lab"]
    
    is_academic = False
    if any(kw in name_lower for kw in academic_keywords):
        is_academic = True
    if any(d in path_lower.split(os.sep) for d in academic_dirs):
        is_academic = True
        
    # 3. Code & Dev
    code_extensions = {".py", ".ipynb", ".js", ".ts", ".jsx", ".tsx", ".html", ".css", ".json", ".sh", ".cpp", ".h", ".java", ".go", ".php", ".tar", ".gz", ".zip"}
    if ext in code_extensions:
        if is_academic:
            return "Academic Code"
        return "Development"
        
    # Classification by extension
    if ext in {".fig", ".xd", ".sketch", ".psd", ".ai"}:
        return "Design"
    
    if ext in {".pdf", ".docx", ".doc", ".xlsx", ".xls", ".pptx", ".ppt", ".txt", ".md"}:
        if is_academic:
            return "Academic Document"
        return "Document"
        
    if ext in {".png", ".jpg", ".jpeg", ".heic", ".gif", ".tiff"}:
        return "Image"
        
    if ext in {".mp4", ".mov", ".avi", ".mkv", ".mp3", ".wav", ".m4a"}:
        return "Media"
        
    return "Other"

def get_modified_files():
    modified_files = []
    cutoff_time = time.time() - 24 * 3600  # Last 24 hours
    
    for base_path in SCAN_PATHS:
        if not os.path.exists(base_path):
            continue
            
        for root, dirs, files in os.walk(base_path):
            # Prune directories we want to ignore
            dirs[:] = [d for d in dirs if d not in IGNORE_DIRS and not d.startswith(".")]
            
            # Check directory depth
            depth = root[len(base_path):].count(os.sep)
            if depth > 4:
                dirs.clear() # don't go deeper
                continue
                
            for file in files:
                if file.startswith(".") or file.startswith("~$") or file in ("dashboard_data.json", "dashboard_data.js"):
                    continue
                    
                file_path = os.path.join(root, file)
                try:
                    mtime = os.path.getmtime(file_path)
                    if mtime >= cutoff_time:
                        size = os.path.getsize(file_path)
                        category = classify_file(file, file_path)
                        modified_files.append({
                            "name": file,
                            "path": file_path,
                            "mtime": mtime,
                            "readable_time": format_timestamp(mtime),
                            "size_bytes": size,
                            "readable_size": format_size(size),
                            "category": category
                        })
                except Exception as e:
                    # Ignore permission errors or broken symlinks
                    continue
                    
    # Sort by mtime descending
    modified_files.sort(key=lambda x: x["mtime"], reverse=True)
    return modified_files

def format_size(size):
    for unit in ['B', 'KB', 'MB', 'GB']:
        if size < 1024.0:
            return f"{size:.1f} {unit}"
        size /= 1024.0
    return f"{size:.1f} TB"

def get_zsh_history():
    history_file = os.path.expanduser("~/.zsh_history")
    if not os.path.exists(history_file):
        return []
        
    commands = []
    try:
        # Read the file with latin-1 to avoid decoding issues on binary contents
        with open(history_file, "r", encoding="latin-1", errors="ignore") as f:
            lines = f.readlines()
            
        # Zsh history entries can be:
        # : 1716382103:0;command
        # Or multi-line or just plain commands
        pattern = re.compile(r"^:\s*(\d+):\d+;(.*)$")
        
        # We process from the end (most recent)
        for line in reversed(lines):
            line = line.strip()
            if not line:
                continue
                
            match = pattern.match(line)
            if match:
                timestamp = int(match.group(1))
                cmd = match.group(2)
                # Check if it was in the last 24 hours
                if time.time() - timestamp <= 24 * 3600:
                    commands.append({
                        "command": cmd,
                        "timestamp": timestamp,
                        "readable_time": format_timestamp(timestamp)
                    })
            else:
                # If no timestamp is present, we just take the last 50 commands from zsh history tail
                # and flag them as "recent" but without timestamp
                if len(commands) < 50:
                    commands.append({
                        "command": line,
                        "timestamp": None,
                        "readable_time": "Recently"
                    })
                    
    except Exception as e:
        print(f"Error parsing zsh history: {e}", file=sys.stderr)
        
    # If the user has timestamps, they'll be sorted. Otherwise keep original order
    if commands and commands[0]["timestamp"] is not None:
        commands.sort(key=lambda x: x["timestamp"], reverse=True)
        
    # Deduplicate consecutive identical commands
    deduped = []
    for cmd in commands:
        if not deduped or deduped[-1]["command"] != cmd["command"]:
            deduped.append(cmd)
            
    return deduped[:60] # return top 60 recent commands

def get_git_commits():
    # Scan standard directories for git repositories
    git_repos = []
    # We look in Desktop/My Projects, Documents, etc.
    search_dirs = [
        "/Users/Abbas/Desktop/My Projects",
        "/Users/Abbas/Desktop",
        "/Users/Abbas/Downloads",
        "/Users/Abbas/Documents"
    ]
    
    found_repos = []
    for base in search_dirs:
        if not os.path.exists(base):
            continue
        # Scan immediate children for .git
        try:
            for item in os.listdir(base):
                full_path = os.path.join(base, item)
                if os.path.isdir(full_path) and item not in IGNORE_DIRS:
                    git_dir = os.path.join(full_path, ".git")
                    if os.path.exists(git_dir) and os.path.isdir(git_dir):
                        found_repos.append((item, full_path))
        except Exception:
            continue
            
    commits = []
    for name, repo_path in found_repos:
        try:
            # Get git commits since midnight
            res = subprocess.run(
                ["git", "log", "--since=midnight", "--oneline", "--format=%h|%ar|%s"],
                cwd=repo_path,
                capture_output=True,
                text=True,
                check=False
            )
            if res.returncode == 0 and res.stdout.strip():
                lines = res.stdout.strip().split("\n")
                for line in lines:
                    parts = line.split("|")
                    if len(parts) >= 3:
                        commits.append({
                            "repo": name,
                            "path": repo_path,
                            "hash": parts[0],
                            "time_relative": parts[1],
                            "message": parts[2]
                        })
        except Exception:
            continue
            
    return commits

def get_system_stats():
    stats = {}
    
    # Disk Usage
    try:
        total, used, free = shutil.disk_usage("/Users/Abbas")
        stats["disk_total"] = format_size(total)
        stats["disk_used"] = format_size(used)
        stats["disk_free"] = format_size(free)
        stats["disk_percent"] = round((used / total) * 100, 1)
    except Exception:
        stats["disk_free"] = "Unknown"
        stats["disk_percent"] = 0
        
    # Battery Level
    try:
        res = subprocess.run(["pmset", "-g", "batt"], capture_output=True, text=True)
        battery_output = res.stdout
        # Match percentage e.g. "98%"
        match = re.search(r"(\d+)%", battery_output)
        if match:
            stats["battery_percent"] = int(match.group(1))
            stats["battery_charging"] = "charging" in battery_output.lower() or "attached" in battery_output.lower()
        else:
            stats["battery_percent"] = None
    except Exception:
        stats["battery_percent"] = None
        
    # RAM Usage (Mac specific)
    try:
        # Run top to get physical RAM free/used
        res = subprocess.run(["sysctl", "hw.memsize"], capture_output=True, text=True)
        total_ram = int(res.stdout.split(":")[1].strip())
        stats["ram_total"] = format_size(total_ram)
    except Exception:
        stats["ram_total"] = "Unknown"
        
    return stats

def get_trash_details():
    trash_path = os.path.expanduser("~/.Trash")
    trash_files = []
    total_size = 0
    item_count = 0
    
    if os.path.exists(trash_path) and os.path.isdir(trash_path):
        try:
            for name in os.listdir(trash_path):
                if name.startswith("."):
                    continue
                full_path = os.path.join(trash_path, name)
                item_count += 1
                try:
                    mtime = os.path.getmtime(full_path)
                    readable_time = datetime.datetime.fromtimestamp(mtime).strftime("%I:%M %p")
                    
                    if os.path.islink(full_path):
                        continue
                    elif os.path.isdir(full_path):
                        # compute dir size recursively
                        dir_size = 0
                        for root, dirs, files in os.walk(full_path):
                            for f in files:
                                fp = os.path.join(root, f)
                                if not os.path.islink(fp):
                                    try:
                                        dir_size += os.path.getsize(fp)
                                    except OSError:
                                        pass
                        total_size += dir_size
                        trash_files.append({
                            "name": name,
                            "path": full_path,
                            "size": format_size(dir_size),
                            "size_bytes": dir_size,
                            "is_dir": True,
                            "mtime": mtime,
                            "time": readable_time
                        })
                    else:
                        file_size = os.path.getsize(full_path)
                        total_size += file_size
                        trash_files.append({
                            "name": name,
                            "path": full_path,
                            "size": format_size(file_size),
                            "size_bytes": file_size,
                            "is_dir": False,
                            "mtime": mtime,
                            "time": readable_time
                        })
                except Exception:
                    trash_files.append({
                        "name": name,
                        "path": full_path,
                        "size": "Unknown",
                        "size_bytes": 0,
                        "is_dir": os.path.isdir(full_path),
                        "mtime": 0,
                        "time": "Unknown"
                    })
        except Exception:
            pass
            
    trash_files.sort(key=lambda x: x.get("mtime", 0), reverse=True)
    
    return {
        "count": item_count,
        "total_size": format_size(total_size),
        "files": trash_files[:50]
    }

def calculate_active_time(modified_files):
    timestamps = []
    now = datetime.datetime.now()
    midnight = datetime.datetime(now.year, now.month, now.day).timestamp()
    
    for f in modified_files:
        if f["mtime"] >= midnight:
            timestamps.append(f["mtime"])
            
    if not timestamps:
        return {
            "readable_active_time": "0m",
            "first_activity": "None",
            "last_activity": "None",
            "active_hours": 0.0
        }
        
    timestamps.sort()
    
    total_active_seconds = 0
    session_gap_limit = 45 * 60  # 45 minutes max gap to keep session active
    session_padding = 20 * 60    # assume 20 minutes of active work per edit
    
    session_start = timestamps[0]
    session_end = timestamps[0] + session_padding
    
    for t in timestamps[1:]:
        if t <= session_end + session_gap_limit:
            session_end = max(session_end, t + session_padding)
        else:
            total_active_seconds += (session_end - session_start)
            session_start = t
            session_end = t + session_padding
            
    total_active_seconds += (session_end - session_start)
    
    hours = int(total_active_seconds // 3600)
    minutes = int((total_active_seconds % 3600) // 60)
    
    readable = ""
    if hours > 0:
        readable += f"{hours}h "
    readable += f"{minutes}m"
    
    first_dt = datetime.datetime.fromtimestamp(timestamps[0])
    last_dt = datetime.datetime.fromtimestamp(timestamps[-1])
    
    return {
        "readable_active_time": readable,
        "first_activity": first_dt.strftime("%I:%M %p"),
        "last_activity": last_dt.strftime("%I:%M %p"),
        "active_hours": round(total_active_seconds / 3600.0, 2)
    }

def get_day_segments(modified_files):
    segments = {
        "Morning": 0,    # 6am - 12pm
        "Afternoon": 0,  # 12pm - 5pm
        "Evening": 0,    # 5pm - 9pm
        "Night": 0       # 9pm - 6am
    }
    
    now = datetime.datetime.now()
    midnight = datetime.datetime(now.year, now.month, now.day).timestamp()
    
    for f in modified_files:
        if f["mtime"] >= midnight:
            dt = datetime.datetime.fromtimestamp(f["mtime"])
            hour = dt.hour
            if 6 <= hour < 12:
                segments["Morning"] += 1
            elif 12 <= hour < 17:
                segments["Afternoon"] += 1
            elif 17 <= hour < 21:
                segments["Evening"] += 1
            else:
                segments["Night"] += 1
                
    return segments

def get_active_workspaces(modified_files):
    workspaces = {}
    
    for f in modified_files:
        filepath = f["path"]
        parts = filepath.split(os.sep)
        
        project_name = None
        project_path = None
        
        if "Desktop" in parts:
            idx = parts.index("Desktop")
            if idx + 1 < len(parts):
                next_part = parts[idx + 1]
                if next_part in ("My Projects", "MyAssignments", "Ariyan_Assignments"):
                    if idx + 2 < len(parts):
                        sub_part = parts[idx + 2]
                        if next_part == "MyAssignments" and sub_part in ("ML", "HCI", "CC", "PP") and idx + 3 < len(parts):
                            project_name = f"{sub_part}: {parts[idx+3]}"
                            project_path = os.sep.join(parts[:idx+4])
                        elif next_part == "Ariyan_Assignments" and sub_part in ("ML", "HCI", "CC", "PP") and idx + 3 < len(parts):
                            project_name = f"Ariyan {sub_part}: {parts[idx+3]}"
                            project_path = os.sep.join(parts[:idx+4])
                        else:
                            project_name = f"{next_part.replace('_', ' ')}: {sub_part}"
                            project_path = os.sep.join(parts[:idx+3])
                    else:
                        project_name = next_part.replace('_', ' ')
                        project_path = os.sep.join(parts[:idx+2])
                else:
                    if os.path.isdir(os.sep.join(parts[:idx+2])):
                        project_name = next_part
                        project_path = os.sep.join(parts[:idx+2])
        elif "Downloads" in parts:
            idx = parts.index("Downloads")
            if idx + 1 < len(parts) and os.path.isdir(os.sep.join(parts[:idx+2])):
                project_name = f"Downloads: {parts[idx+1]}"
                project_path = os.sep.join(parts[:idx+2])
            else:
                project_name = "Downloads Root"
                project_path = "/Users/Abbas/Downloads"
        elif "Documents" in parts:
            idx = parts.index("Documents")
            if idx + 1 < len(parts):
                project_name = f"Documents: {parts[idx+1]}"
                project_path = os.sep.join(parts[:idx+2])
            else:
                project_name = "Documents Root"
                project_path = "/Users/Abbas/Documents"
                
        if project_name and project_path:
            if project_path not in workspaces:
                workspaces[project_path] = {
                    "name": project_name,
                    "path": project_path,
                    "files_count": 0
                }
            workspaces[project_path]["files_count"] += 1
            
    workspace_list = list(workspaces.values())
    workspace_list.sort(key=lambda x: x["files_count"], reverse=True)
    return workspace_list[:6]

def get_spotify_status():
    spotify_data = {
        "is_running": False,
        "player_state": "stopped",
        "track": None,
        "artist": None,
        "album": None,
        "url": None,
        "history": []
    }
    
    # AppleScript query to inspect Spotify state securely without opening the app if closed
    script = '''
    if application "Spotify" is running then
        tell application "Spotify"
            try
                set pState to player state as string
                set tName to name of current track
                set tArtist to artist of current track
                set tAlbum to album of current track
                set tUrl to spotify url of current track
                return "running|" & pState & "|" & tName & "|" & tArtist & "|" & tAlbum & "|" & tUrl
            on error
                return "error"
            end try
        end tell
    else
        return "not_running"
    end if
    '''
    
    try:
        res = subprocess.run(
            ["osascript", "-e", script],
            capture_output=True,
            text=True,
            timeout=3.0
        )
        if res.returncode == 0:
            output = res.stdout.strip()
            if output.startswith("running|"):
                parts = output.split("|")
                if len(parts) >= 6:
                    spotify_data["is_running"] = True
                    spotify_data["player_state"] = parts[1].lower()
                    spotify_data["track"] = parts[2]
                    spotify_data["artist"] = parts[3]
                    spotify_data["album"] = parts[4]
                    
                    # Convert URI to URL (e.g. spotify:track:xxx -> open.spotify.com/track/xxx)
                    uri = parts[5]
                    if uri.startswith("spotify:track:"):
                        track_id = uri.split(":")[-1]
                        spotify_data["url"] = f"https://open.spotify.com/track/{track_id}"
                    else:
                        spotify_data["url"] = None
    except subprocess.TimeoutExpired:
        print("Spotify status check timed out.", file=sys.stderr)
    except Exception as e:
        print(f"Error checking Spotify status: {e}", file=sys.stderr)
        
    # Maintain history of tracks played today in a local JSON cache
    history_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".spotify_history.json")
    today_str = datetime.datetime.today().strftime("%Y-%m-%d")
    
    history_data = {}
    if os.path.exists(history_file):
        try:
            with open(history_file, "r", encoding="utf-8") as f:
                history_data = json.load(f)
        except Exception:
            pass
            
    # Keep only the last 7 days of history to prevent file size bloat
    days_to_keep = [(datetime.datetime.today() - datetime.timedelta(days=i)).strftime("%Y-%m-%d") for i in range(7)]
    history_data = {d: history_data[d] for d in days_to_keep if d in history_data}
    
    if today_str not in history_data:
        history_data[today_str] = []
        
    # If a song is actively playing, append it to today's history log if it is new
    if spotify_data["is_running"] and spotify_data["player_state"] == "playing" and spotify_data["track"]:
        today_songs = history_data[today_str]
        
        # Avoid duplicate logs for consecutive requests on the same song
        is_new_song = True
        if today_songs:
            last_song = today_songs[-1]
            if last_song["track"] == spotify_data["track"] and last_song["artist"] == spotify_data["artist"]:
                is_new_song = False
                
        if is_new_song:
            now_dt = datetime.datetime.now()
            today_songs.append({
                "time": now_dt.strftime("%I:%M %p"),
                "timestamp": now_dt.timestamp(),
                "track": spotify_data["track"],
                "artist": spotify_data["artist"],
                "url": spotify_data["url"]
            })
            
            try:
                with open(history_file, "w", encoding="utf-8") as f:
                    json.dump(history_data, f, indent=2)
            except Exception as e:
                print(f"Error saving Spotify history: {e}", file=sys.stderr)
                
    spotify_data["history"] = list(reversed(history_data[today_str]))
    return spotify_data

def main():
    print("Collecting MacBook activity statistics for today...")
    
    modified_files = get_modified_files()
    zsh_history = get_zsh_history()
    git_commits = get_git_commits()
    system_stats = get_system_stats()
    spotify_data = get_spotify_status()
    trash_data = get_trash_details()
    
    # Calculate screen time metrics
    active_time = calculate_active_time(modified_files)
    active_workspaces = get_active_workspaces(modified_files)
    day_segments = get_day_segments(modified_files)
    
    # Aggregate statistics
    categories_count = {}
    for f in modified_files:
        categories_count[f["category"]] = categories_count.get(f["category"], 0) + 1
        
    data = {
        "generated_at": format_timestamp(time.time()),
        "generated_epoch": time.time(),
        "summary": {
            "total_files_modified": len(modified_files),
            "total_commands_run": len(zsh_history),
            "total_git_commits": len(git_commits),
            "categories_breakdown": categories_count,
            "active_time": active_time,
            "active_workspaces": active_workspaces,
            "day_segments": day_segments
        },
        "system": system_stats,
        "files": modified_files,
        "commands": zsh_history,
        "commits": git_commits,
        "spotify": spotify_data,
        "trash": trash_data
    }
    
    output_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "dashboard_data.js")
    with open(output_path, "w", encoding="utf-8") as f:
        f.write("window.dashboardData = ")
        json.dump(data, f, indent=2)
        f.write(";\n")
        
    print(f"Data successfully compiled to {output_path}!")
    print(f"Summary: {len(modified_files)} files modified, {len(zsh_history)} terminal commands, {len(git_commits)} commits.")
    if spotify_data["is_running"] and spotify_data["player_state"] == "playing":
        print(f"Spotify: Playing \"{spotify_data['track']}\" by {spotify_data['artist']}.")
    else:
        print("Spotify: Idle.")

if __name__ == "__main__":
    main()

