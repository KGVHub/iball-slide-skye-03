#!/bin/bash
# Print the accelerometer values Android receives (m/s^2), once a second.
# usage: accel_watch.sh <seconds>
for i in $(seq 1 "${1:-60}"); do
    v=$(adb shell dumpsys sensorservice 2>/dev/null | grep -A1 'Accelerometer: last' | tail -1 | sed 's/.*) //')
    echo "$(date +%T) $v"
    sleep 1
done
