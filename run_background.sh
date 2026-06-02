#!/bin/bash
# Run Cinema City Watcher in background
# Usage: bash run_background.sh [start|stop|status|log]

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
LOG_FILE="$HOME/CinemaCityWatcher/log.txt"
PID_FILE="$HOME/CinemaCityWatcher/watcher.pid"

start() {
    if [ -f "$PID_FILE" ] && kill -0 "$(cat "$PID_FILE")" 2>/dev/null; then
        echo "Watcher is already running (PID: $(cat "$PID_FILE"))"
        return 1
    fi

    echo "Starting Cinema City Watcher..."
    nohup python "$SCRIPT_DIR/cinema_watcher.py" > "$LOG_FILE" 2>&1 &
    echo $! > "$PID_FILE"
    echo "Started with PID: $(cat "$PID_FILE")"
    echo "Log: $LOG_FILE"
}

stop() {
    if [ -f "$PID_FILE" ]; then
        PID=$(cat "$PID_FILE")
        if kill -0 "$PID" 2>/dev/null; then
            kill "$PID"
            rm "$PID_FILE"
            echo "Watcher stopped (PID: $PID)"
        else
            rm "$PID_FILE"
            echo "Process was not running. Cleaned up PID file."
        fi
    else
        echo "No PID file found. Trying pkill..."
        pkill -f "cinema_watcher.py"
    fi
}

status() {
    if [ -f "$PID_FILE" ] && kill -0 "$(cat "$PID_FILE")" 2>/dev/null; then
        echo "Running (PID: $(cat "$PID_FILE"))"
        echo "Last log entries:"
        tail -5 "$LOG_FILE" 2>/dev/null
    else
        echo "Not running"
    fi
}

log() {
    tail -f "$LOG_FILE"
}

case "${1:-start}" in
    start)  start ;;
    stop)   stop ;;
    status) status ;;
    log)    log ;;
    *)      echo "Usage: $0 {start|stop|status|log}" ;;
esac
