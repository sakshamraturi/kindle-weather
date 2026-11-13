#!/bin/sh
DIR="$(cd "$(dirname "$0")" && pwd)"
. "$DIR/weather.conf"
IMG="$DIR/weather.png"

wifi_on() {
  lipc-set-prop com.lab126.cmd wirelessEnable 1
  i=0
  while [ $i -lt 45 ]; do
    [ "$(lipc-get-prop com.lab126.wifid cmState 2>/dev/null)" = "CONNECTED" ] && return 0
    sleep 2; i=$((i+1))
  done
  return 1
}

case "$URL" in *example.com*) echo "URL not configured, exiting"; exit 1;; esac
FROZEN=0

while true; do
  if wifi_on && curl -fsS -m 40 -o "$IMG.tmp" "$URL"; then
    mv -f "$IMG.tmp" "$IMG"
    if [ $FROZEN -eq 0 ]; then
      # only take over the screen once we actually have an image to show
      killall -STOP cvm 2>/dev/null
      lipc-set-prop com.lab126.powerd preventScreenSaver 1 2>/dev/null
      FROZEN=1
    fi
  else
    echo "$(date): fetch failed, keeping last image"
  fi
  lipc-set-prop com.lab126.cmd wirelessEnable 0
  if [ $FROZEN -eq 1 ] && [ -f "$IMG" ]; then
    eips -c >/dev/null 2>&1   # clear to reduce ghosting
    eips -g "$IMG"
  fi
  sleep "$INTERVAL"
done
