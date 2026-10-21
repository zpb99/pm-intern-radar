#!/usr/bin/env bash
# Run the PM-intern radar once and send a macOS notification with the result.
# Called weekly by launchd (see scripts/install_schedule.sh); safe to run by hand.
set -uo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
LOG_DIR="$ROOT/data/radar/logs"
mkdir -p "$LOG_DIR"
LOG="$LOG_DIR/run-$(date +%Y-%m-%d).log"

notify() {
  # $1 = message. Quotes are stripped so the message can't break the AppleScript string.
  local msg="${1//\"/}"
  /usr/bin/osascript -e "display notification \"$msg\" with title \"PM intern radar\"" || true
}

cd "$ROOT" || exit 1
"$ROOT/.venv/bin/python" -m jd_analyzer.radar > "$LOG" 2>&1
rc=$?

if [ "$rc" -ne 0 ]; then
  notify "Run FAILED (exit $rc). See data/radar/logs/$(basename "$LOG")"
  exit "$rc"
fi

new_roles="$(head -n 1 "$ROOT/data/radar/last_summary.txt" 2>/dev/null || echo "?")"
if [ "$new_roles" = "0" ]; then
  notify "No new PM intern roles this week."
else
  notify "$new_roles new PM intern roles. Open data/radar/latest.md"
fi
