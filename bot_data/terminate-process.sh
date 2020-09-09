#1/usr/bin/env sh

PID="$1"
sleep 15
kill -2 $PID >/dev/null 2>&1 || exit 0
rm -f bot.lock >/dev/null 2>&1
sleep 30
kill -15 $PID >/dev/null 2>&1 || exit 0
sleep 30
kill -9 $PID >/dev/null 2>&1 || exit 0
