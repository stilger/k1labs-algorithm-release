#!/bin/bash
# ==============================================================================
# K1Labs Management CGI Backend for Osprey E300 / Zynq-7000
# Handles shellinabox installation/removal/status, command execution, and rollback.
# ==============================================================================

echo "Content-Type: application/json"
echo "Access-Control-Allow-Origin: *"
echo "Cache-Control: no-cache, no-store, must-revalidate"
echo ""

# Helper to output JSON safely
json_output() {
    local status="$1"
    local msg="$2"
    local extra="$3"

    if command -v python >/dev/null 2>&1; then
        python -c '
import sys, json
status = sys.argv[1]
msg = sys.argv[2]
extra = sys.argv[3] if len(sys.argv) > 3 and sys.argv[3] else "{}"
try:
    data = json.loads(extra)
except Exception:
    data = {}
data["status"] = status
data["output"] = msg
print(json.dumps(data))
' "$status" "$msg" "$extra"
    elif command -v python3 >/dev/null 2>&1; then
        python3 -c '
import sys, json
status = sys.argv[1]
msg = sys.argv[2]
extra = sys.argv[3] if len(sys.argv) > 3 and sys.argv[3] else "{}"
try:
    data = json.loads(extra)
except Exception:
    data = {}
data["status"] = status
data["output"] = msg
print(json.dumps(data))
' "$status" "$msg" "$extra"
    else
        # Fallback simple escape
        local clean_msg
        clean_msg=$(echo "$msg" | sed -e 's/\\/\\\\/g' -e 's/"/\\"/g' -e ':a;N;$!ba;s/\n/\\n/g' -e 's/\r//g' -e 's/\t/\\t/g')
        echo "{\"status\":\"$status\",\"output\":\"$clean_msg\"}"
    fi
}

# Parse POST or GET data
REQ_BODY=""
if [ "$REQUEST_METHOD" = "POST" ]; then
    if [ -n "$CONTENT_LENGTH" ] && [ "$CONTENT_LENGTH" -gt 0 ]; then
        read -n "$CONTENT_LENGTH" REQ_BODY
    fi
elif [ "$REQUEST_METHOD" = "GET" ]; then
    REQ_BODY="$QUERY_STRING"
fi

# Extract parameters
ACTION=""
CMD=""

if command -v python >/dev/null 2>&1; then
    eval "$(python -c '
import sys, urllib.parse if sys.version_info[0] >= 3 else urllib, json
raw = sys.argv[1]
action = ""
cmd = ""
try:
    if raw.startswith("{"):
        d = json.loads(raw)
        action = d.get("action", "")
        cmd = d.get("cmd", "")
    else:
        qs = urllib.parse.parse_qs(raw) if sys.version_info[0] >= 3 else urllib.parse.parse_qs(raw)
        action = qs.get("action", [""])[0]
        cmd = qs.get("cmd", [""])[0]
except Exception:
    pass

import shlex
print("ACTION=" + shlex.quote(action))
print("CMD=" + shlex.quote(cmd))
' "$REQ_BODY" 2>/dev/null)"
elif command -v python3 >/dev/null 2>&1; then
    eval "$(python3 -c '
import sys, urllib.parse, json, shlex
raw = sys.argv[1]
action = ""
cmd = ""
try:
    if raw.startswith("{"):
        d = json.loads(raw)
        action = d.get("action", "")
        cmd = d.get("cmd", "")
    else:
        qs = urllib.parse.parse_qs(raw)
        action = qs.get("action", [""])[0]
        cmd = qs.get("cmd", [""])[0]
except Exception:
    pass
print("ACTION=" + shlex.quote(action))
print("CMD=" + shlex.quote(cmd))
' "$REQ_BODY" 2>/dev/null)"
else
    # Simple regex fallback
    ACTION=$(echo "$REQ_BODY" | grep -oP '(?<=action=)[^&]*' || echo "$REQ_BODY" | grep -oP '(?<="action":")[^"]*' || true)
    CMD=$(echo "$REQ_BODY" | grep -oP '(?<=cmd=)[^&]*' || echo "$REQ_BODY" | grep -oP '(?<="cmd":")[^"]*' || true)
fi

# Default action if empty
if [ -z "$ACTION" ]; then
    ACTION="status"
fi

case "$ACTION" in
    status)
        INSTALLED=false
        RUNNING=false

        if command -v shellinaboxd >/dev/null 2>&1 || [ -f /usr/bin/shellinaboxd ]; then
            INSTALLED=true
        fi

        if pgrep -x shellinaboxd >/dev/null 2>&1 || systemctl is-active --quiet shellinabox 2>/dev/null; then
            RUNNING=true
        fi

        BACKUP_EXISTS=false
        if [ -f /var/www/html/N2030index.html.k1labs_backup ]; then
            BACKUP_EXISTS=true
        fi

        CURRENT_ALGO_VER="Unknown"
        if [ -f /opt/algorithm/algorithm_version.txt ]; then
            CURRENT_ALGO_VER=$(cat /opt/algorithm/algorithm_version.txt | tr -d '\r\n')
        fi

        CURRENT_GIT="Default"
        if [ -f /opt/algorithm/algo_config.json ]; then
            CURRENT_GIT=$(grep -oP '(?<="path":\s*")[^"]*' /opt/algorithm/algo_config.json 2>/dev/null || echo "Config present")
        fi

        EXTRA="{\"installed\":$INSTALLED,\"running\":$RUNNING,\"port\":4200,\"backup_exists\":$BACKUP_EXISTS,\"algo_version\":\"$CURRENT_ALGO_VER\",\"git_path\":\"$CURRENT_GIT\"}"
        json_output "ok" "Status checked" "$EXTRA"
        ;;

    install_shellinabox)
        OUT=$(
            export DEBIAN_FRONTEND=noninteractive
            echo "--- Updating Package Lists ---"
            sudo apt-get update -y 2>&1
            echo "--- Installing shellinabox ---"
            sudo apt-get install -y --allow-unauthenticated shellinabox 2>&1
            echo "--- Configuring & Starting Service ---"
            sudo systemctl enable shellinabox 2>&1 || true
            sudo systemctl restart shellinabox 2>&1 || sudo /etc/init.d/shellinabox restart 2>&1 || true
            echo "--- Done ---"
        )
        json_output "ok" "$OUT"
        ;;

    remove_shellinabox)
        OUT=$(
            export DEBIAN_FRONTEND=noninteractive
            echo "--- Stopping Service ---"
            sudo systemctl stop shellinabox 2>&1 || true
            sudo killall shellinaboxd 2>/dev/null || true
            echo "--- Removing shellinabox ---"
            sudo apt-get remove -y --purge shellinabox 2>&1
            sudo apt-get autoremove -y 2>&1
            echo "--- Removed Successfully ---"
        )
        json_output "ok" "$OUT"
        ;;

    restart_shellinabox)
        OUT=$(
            sudo systemctl restart shellinabox 2>&1 || sudo /etc/init.d/shellinabox restart 2>&1 || true
            echo "Service restart issued."
        )
        json_output "ok" "$OUT"
        ;;

    run_cmd)
        if [ -z "$CMD" ]; then
            json_output "error" "No command specified"
            exit 0
        fi

        # Run command with 30s timeout
        OUT=$(timeout 30 bash -c "$CMD" 2>&1)
        EXIT_CODE=$?
        if [ $EXIT_CODE -eq 124 ]; then
            OUT="$OUT [Command timed out after 30 seconds]"
        fi
        json_output "ok" "$OUT" "{\"exit_code\":$EXIT_CODE}"
        ;;

    restore_defaults)
        if [ -f /opt/algorithm/restore_k1labs.sh ]; then
            OUT=$(sudo /bin/bash /opt/algorithm/restore_k1labs.sh 2>&1)
            json_output "ok" "$OUT"
        else
            json_output "error" "Restore script /opt/algorithm/restore_k1labs.sh not found."
        fi
        ;;

    *)
        json_output "error" "Unknown action: $ACTION"
        ;;
esac
