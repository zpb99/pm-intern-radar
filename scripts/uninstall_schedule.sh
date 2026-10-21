#!/usr/bin/env bash
# Remove the weekly radar launchd job.
set -euo pipefail
LABEL="com.zacharybergman.jd-analyzer.radar"
/bin/launchctl bootout "gui/$(id -u)/$LABEL" 2>/dev/null || true
rm -f "$HOME/Library/LaunchAgents/$LABEL.plist"
echo "Removed $LABEL"
