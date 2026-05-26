#!/bin/bash
# Monitor — starts and watches all 3 autoresearch groups
# Usage: bash monitor.sh

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
CHECK_INTERVAL=600
STALL_THRESHOLD=900

echo "========================================"
echo " Autoresearch Monitor"
echo " Directory: $SCRIPT_DIR"
echo " Check interval: ${CHECK_INTERVAL}s"
echo "========================================"

# Start each group's run.sh in background
start_group() {
    local name=$1
    local dir="${SCRIPT_DIR}/${name}"
    if [ ! -f "${dir}/run.sh" ]; then
        echo "[MONITOR] ERROR: ${dir}/run.sh not found"
        return 1
    fi
    echo "[MONITOR] Starting ${name}..."
    cd "$dir"
    bash run.sh > run_monitor.log 2>&1 &
    echo $! > "${dir}/.monitor_pid"
    cd "$SCRIPT_DIR"
    echo "[MONITOR] ${name} started (PID: $(cat ${dir}/.monitor_pid))"
}

check_group() {
    local name=$1
    local dir="${SCRIPT_DIR}/${name}"
    local pidfile="${dir}/.monitor_pid"

    if [ ! -f "$pidfile" ]; then
        echo "[MONITOR] ${name}: no PID file, restarting..."
        start_group "$name"
        return
    fi

    local pid=$(cat "$pidfile")

    if ! kill -0 "$pid" 2>/dev/null; then
        echo "[MONITOR] ${name} (PID $pid) DEAD. Restarting..."
        start_group "$name"
        return
    fi

    # Count experiments
    local n_exp=0
    if [ -f "${dir}/results.tsv" ]; then
        n_exp=$(wc -l < "${dir}/results.tsv")
        n_exp=$((n_exp - 1))
    fi

    # Check last git activity
    local last_commit=$(cd "$dir" && git log -1 --format=%ct 2>/dev/null || echo 0)
    local now=$(date +%s)
    local age=$((now - last_commit))

    if [ $age -gt $STALL_THRESHOLD ] && [ $n_exp -gt 0 ]; then
        echo "[MONITOR] ${name} STALLED (${age}s). Killing PID $pid..."
        kill "$pid" 2>/dev/null
        sleep 2
        kill -9 "$pid" 2>/dev/null
        start_group "$name"
    else
        echo "[MONITOR] ${name} OK — PID=$pid, experiments=$n_exp, last_activity=${age}s ago"
    fi
}

# Start all
for g in autoresearch-forex autoresearch-commod autoresearch-index; do
    start_group "$g"
    sleep 3
done

echo ""
echo "[MONITOR] All groups started. Checking every ${CHECK_INTERVAL}s..."
echo "[MONITOR] Press Ctrl+C to stop all."
echo ""

# Cleanup on exit
trap 'echo "[MONITOR] Stopping all..."; for g in autoresearch-forex autoresearch-commod autoresearch-index; do pid=$(cat "${SCRIPT_DIR}/${g}/.monitor_pid" 2>/dev/null); kill $pid 2>/dev/null; done; echo "[MONITOR] Done."; exit 0' INT TERM

# Monitor loop
while true; do
    sleep $CHECK_INTERVAL
    echo ""
    echo "=== Monitor check at $(date) ==="
    for g in autoresearch-forex autoresearch-commod autoresearch-index; do
        check_group "$g"
    done
done
