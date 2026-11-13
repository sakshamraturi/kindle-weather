#!/bin/sh
DIR="$(cd "$(dirname "$0")" && pwd)"
echo "$(date): test ran, URL=$(. "$DIR/weather.conf"; echo $URL)" >> "$DIR/test.log"
eips 4 10 "Weather extension works!" 2>/dev/null
echo "Extension is working"
