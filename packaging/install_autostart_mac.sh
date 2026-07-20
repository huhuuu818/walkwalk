#!/usr/bin/env bash
# Make "Walk Walk" start automatically in the background at login (macOS, packaged app).
# Prerequisite: Walk Walk.app built with packaging/build_mac.sh
# Usage: bash packaging/install_autostart_mac.sh [path to Walk Walk.app, default /Applications/Walk Walk.app]
#
# Note: the "Start at login" checkbox in the Settings panel does the same thing (pointing
# at walkwalk.py directly, no packaging needed). Both write the same LaunchAgent —
# set it up one way or the other, not both.
set -euo pipefail

APP_PATH="${1:-/Applications/Walk Walk.app}"
EXEC_PATH="$APP_PATH/Contents/MacOS/Walk Walk"

if [ ! -x "$EXEC_PATH" ]; then
  echo "Not found: $EXEC_PATH"
  echo "Run packaging/build_mac.sh first and move the built \"Walk Walk.app\" to /Applications"
  echo "(or: bash packaging/install_autostart_mac.sh /path/to/Walk\\ Walk.app)"
  exit 1
fi

PLIST_DIR="$HOME/Library/LaunchAgents"
PLIST_PATH="$PLIST_DIR/com.walkwalk.app.plist"
mkdir -p "$PLIST_DIR"

cat > "$PLIST_PATH" <<EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.walkwalk.app</string>
    <key>ProgramArguments</key>
    <array>
        <string>$EXEC_PATH</string>
    </array>
    <key>RunAtLoad</key>
    <true/>
    <key>KeepAlive</key>
    <false/>
</dict>
</plist>
EOF

launchctl unload "$PLIST_PATH" 2>/dev/null || true
launchctl load "$PLIST_PATH"

echo ""
echo "Login autostart installed: $PLIST_PATH"
echo "Walk Walk will now run in the background at login (tip: switch Schedule to Always in Settings so the timer starts right at boot)."
echo ""
echo "To remove the autostart, run:"
echo "  launchctl unload \"$PLIST_PATH\" && rm \"$PLIST_PATH\""
