#!/bin/sh
# "on": start the dashboard by itself after every boot. "off": don't.
# The boot job is /etc/upstart/weather-dashboard.conf and only acts while the flag file exists.
DIR=/mnt/us/extensions/weather
JOB=/etc/upstart/weather-dashboard.conf
if [ "$1" = on ]; then
    if [ ! -f "$JOB" ]; then
        mntroot rw && cp "$DIR/weather-boot.conf" "$JOB"
        mntroot ro
    fi
    if [ -f "$JOB" ]; then
        touch "$DIR/autostart"
        msg="Autostart ON: weather starts 90 s after each boot."
    else
        msg="Autostart FAILED: could not install the boot job."
    fi
else
    rm -f "$DIR/autostart"
    msg="Autostart OFF."
fi
eips 4 10 "$msg" 2>/dev/null
echo "$msg"
