#!/usr/bin/env bash
# Install (or reinstall) a launchd job that runs scripts/run_radar.sh every Monday at 08:00.
# If the Mac is asleep then, launchd runs it at the next wake. Undo: scripts/uninstall_schedule.sh
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
LABEL="com.zacharybergman.jd-analyzer.radar"
PLIST="$HOME/Library/LaunchAgents/$LABEL.plist"

mkdir -p "$HOME/Library/LaunchAgents" "$ROOT/data/radar/logs"
cat > "$PLIST" <<PLIST
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
  <key>Label</key><string>$LABEL</string>
  <key>ProgramArguments</key>
  <array>
    <string>/bin/bash</string>
    <string>$ROOT/scripts/run_radar.sh</string>
  </array>
  <key>StartCalendarInterval</key>
  <dict>
    <key>Weekday</key><integer>1</integer>
    <key>Hour</key><integer>8</integer>
    <key>Minute</key><integer>0</integer>
  </dict>
  <key>StandardOutPath</key><string>$ROOT/data/radar/logs/launchd.out</string>
  <key>StandardErrorPath</key><string>$ROOT/data/radar/logs/launchd.err</string>
</dict>
</plist>
PLIST

/bin/launchctl bootout "gui/$(id -u)/$LABEL" 2>/dev/null || true
/bin/launchctl bootstrap "gui/$(id -u)" "$PLIST"
echo "Installed $LABEL: runs Mondays 08:00. Plist: $PLIST"
