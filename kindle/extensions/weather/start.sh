#!/bin/sh
DIR="$(cd "$(dirname "$0")" && pwd)"
# already running?
if [ -f "$DIR/loop.pid" ] && kill -0 "$(cat "$DIR/loop.pid")" 2>/dev/null; then exit 0; fi
nohup sh "$DIR/loop.sh" >"$DIR/log.txt" 2>&1 &
echo $! > "$DIR/loop.pid"
