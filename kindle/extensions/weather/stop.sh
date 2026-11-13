#!/bin/sh
DIR="$(cd "$(dirname "$0")" && pwd)"
[ -f "$DIR/loop.pid" ] && kill "$(cat "$DIR/loop.pid")" 2>/dev/null
rm -f "$DIR/loop.pid"
lipc-set-prop com.lab126.powerd preventScreenSaver 0 2>/dev/null
killall -CONT cvm 2>/dev/null
# redraw the normal Kindle UI
lipc-set-prop com.lab126.appmgrd start app://com.lab126.booklet.home 2>/dev/null
