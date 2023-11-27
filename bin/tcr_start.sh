#!/bin/bash
set -a
if [[ $# -lt 2 ]]; then
    echo "Invalid arguments. Use like ${0} <host> <port>"
    exit 1
fi
CHATROOM_HOST=$1
CHATROOM_PORT=$2
/usr/bin/python3.11 /usr/bin/tcr.py > /dev/null 2>&1 &
sleep 1
exit 0
