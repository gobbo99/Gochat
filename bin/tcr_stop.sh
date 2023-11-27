#!/bin/bash
# Filename: tcr_stop.sh

PID=$(pgrep -f "/usr/bin/python3.11 /usr/bin/tcr.py")

if [ -n "$PID" ]; then
    echo "Stopping the chatroom server..."
    kill "$PID"
    exit 0
else
    echo "Chatroom server is not running."
    exit 0
fi

