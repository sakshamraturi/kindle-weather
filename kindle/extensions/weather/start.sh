#!/bin/sh
DIR="$(cd "$(dirname "$0")" && pwd)"
# already running? (check the pid really is our loop, pids get reused after reboot)
if [ -f "$DIR/loop.pid" ]; then
  P="$(cat "$DIR/loop.pid")"
  if kill -0 "$P" 2>/dev/null && tr '\0' ' ' < "/proc/$P/cmdline" 2>/dev/null | grep -q "loop.sh"; then exit 0; fi
fi
nohup sh "$DIR/loop.sh" >"$DIR/log.txt" 2>&1 &
echo $! > "$DIR/loop.pid"
