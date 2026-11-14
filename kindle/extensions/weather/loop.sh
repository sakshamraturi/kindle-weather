#!/bin/sh
DIR="$(cd "$(dirname "$0")" && pwd)"
. "$DIR/weather.conf"
IMG="$DIR/weather.png"
LOG="$DIR/log.txt"

log() {
  echo "$(date '+%Y-%m-%d %H:%M:%S') $*" >> "$LOG"
  # keep the log small
  [ "$(wc -c < "$LOG" 2>/dev/null || echo 0)" -gt 20000 ] && tail -n 60 "$LOG" > "$LOG.tmp" && mv -f "$LOG.tmp" "$LOG"
}

wifi_connected() { [ "$(lipc-get-prop com.lab126.wifid cmState 2>/dev/null)" = "CONNECTED" ]; }

# Wi-Fi is kept ON all the time (no airplane mode). This only makes sure it is
# enabled and connected, and waits up to ~2 minutes for the connection.
wifi_on() {
  lipc-set-prop com.lab126.cmd wirelessEnable 1 2>/dev/null
  i=0
  while [ $i -lt 60 ]; do
    wifi_connected && return 0
    sleep 2; i=$((i+1))
  done
  return 1
}

# Last resort when the connection is stuck: turn Wi-Fi off and on again.
wifi_reset() {
  log "resetting Wi-Fi"
  lipc-set-prop com.lab126.cmd wirelessEnable 0 2>/dev/null
  sleep 5
  lipc-set-prop com.lab126.cmd wirelessEnable 1 2>/dev/null
}

case "$URL" in *example.com*) log "URL not configured, exiting"; exit 1;; esac
FROZEN=0
FAILS=0
log "loop started (interval ${INTERVAL}s, Wi-Fi stays on)"

while true; do
  # keep the device awake and the screen from switching to the screensaver
  lipc-set-prop com.lab126.powerd preventScreenSaver 1 2>/dev/null

  if wifi_on && curl -fsS -m 40 -o "$IMG.tmp" "$URL" 2>>"$LOG"; then
    mv -f "$IMG.tmp" "$IMG"
    FAILS=0
    log "fetched ok ($(wc -c < "$IMG") bytes)"
    if [ $FROZEN -eq 0 ]; then
      # only take over the screen once we actually have an image to show
      killall -STOP cvm 2>/dev/null
      FROZEN=1
    fi
    if [ $FROZEN -eq 1 ] && [ -f "$IMG" ]; then
      eips -c >/dev/null 2>&1   # clear to reduce ghosting
      eips -g "$IMG"
    fi
    sleep "$INTERVAL"
  else
    FAILS=$((FAILS+1))
    log "fetch failed (#$FAILS), keeping last image, retrying in 60s"
    rm -f "$IMG.tmp"
    [ $FAILS -ge 3 ] && wifi_reset && FAILS=0
    sleep 60
  fi
done
