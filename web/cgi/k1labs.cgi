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

    if command -v python >/dev/null 2>&1 || command -v python3 >/dev/null 2>&1; then
        local py_bin="python"
        command -v python >/dev/null 2>&1 || py_bin="python3"
        "$py_bin" -c '
import sys, json
status = sys.argv[1]
msg = sys.argv[2]
extra_str = sys.argv[3] if len(sys.argv) > 3 and sys.argv[3] else "{}"
try:
    data = json.loads(extra_str)
except Exception:
    data = {}
data["status"] = status
data["output"] = msg
print(json.dumps(data))
' "$status" "$msg" "$extra"
    else
        local clean_msg
        clean_msg=$(printf '%s' "$msg" | sed -e 's/\\/\\\\/g' -e 's/"/\\"/g' -e ':a;N;$!ba;s/\n/\\n/g' -e 's/\r//g' -e 's/\t/\\t/g')
        echo "{\"status\":\"$status\",\"output\":\"$clean_msg\"}"
    fi
}

# Read request body
REQ_BODY=""
if [ "$REQUEST_METHOD" = "POST" ]; then
    if [ -n "$CONTENT_LENGTH" ] && [ "$CONTENT_LENGTH" -gt 0 ]; then
        read -n "$CONTENT_LENGTH" REQ_BODY
    fi
elif [ "$REQUEST_METHOD" = "GET" ]; then
    REQ_BODY="$QUERY_STRING"
fi

# Parse parameters reliably
ACTION=""
CMD=""

if command -v python >/dev/null 2>&1 || command -v python3 >/dev/null 2>&1; then
    local_py="python"
    command -v python >/dev/null 2>&1 || local_py="python3"
    eval "$("$local_py" -c '
import sys, json

raw = sys.argv[1] if len(sys.argv) > 1 else ""
action = ""
cmd = ""

try:
    raw_str = raw.strip()
    if raw_str.startswith("{"):
        d = json.loads(raw_str)
        action = d.get("action", "")
        cmd = d.get("cmd", "")
    else:
        try:
            from urllib.parse import parse_qs
        except ImportError:
            from urlparse import parse_qs
        qs = parse_qs(raw_str)
        action = qs.get("action", [""])[0]
        cmd = qs.get("cmd", [""])[0]
except Exception:
    pass

try:
    from shlex import quote
except ImportError:
    from pipes import quote

print("ACTION=" + quote(action))
print("CMD=" + quote(cmd))
' "$REQ_BODY" 2>/dev/null)"
fi

# Fallback regex if python parsing was empty
if [ -z "$ACTION" ]; then
    ACTION=$(echo "$REQ_BODY" | grep -oP '(?<="action":")[^"]*' || echo "$REQ_BODY" | grep -oP '(?<=action=)[^&]*' || true)
fi
if [ -z "$CMD" ]; then
    CMD=$(echo "$REQ_BODY" | grep -oP '(?<="cmd":")[^"]*' || echo "$REQ_BODY" | grep -oP '(?<=cmd=)[^&]*' || true)
fi

# Default action if still empty
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

            echo "--- Configuring shellinabox with --disable-ssl ---"
            if [ -f /etc/default/shellinabox ]; then
                sudo sed -i 's/^SHELLINABOX_ARGS=.*/SHELLINABOX_ARGS="--no-beep --disable-ssl"/' /etc/default/shellinabox 2>/dev/null || true
                if ! grep -q 'disable-ssl' /etc/default/shellinabox; then
                    echo 'SHELLINABOX_ARGS="--no-beep --disable-ssl"' | sudo tee -a /etc/default/shellinabox >/dev/null
                fi
            fi

            # Systemd service override to ensure --disable-ssl is passed
            if [ -d /etc/systemd/system ]; then
                sudo mkdir -p /etc/systemd/system/shellinabox.service.d
                cat << 'EOF' > /tmp/shellinabox_override.conf
[Service]
ExecStart=
ExecStart=/usr/bin/shellinaboxd -q -p 4200 --no-beep --disable-ssl
EOF
                sudo mv /tmp/shellinabox_override.conf /etc/systemd/system/shellinabox.service.d/override.conf
                sudo systemctl daemon-reload 2>&1 || true
            fi

            echo "--- Starting Shellinabox Service (HTTP port 4200) ---"
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
            sudo rm -rf /etc/systemd/system/shellinabox.service.d || true
            sudo systemctl daemon-reload 2>&1 || true
            echo "--- Removing shellinabox ---"
            sudo apt-get remove -y --purge shellinabox 2>&1
            sudo apt-get autoremove -y 2>&1
            echo "--- Removed Successfully ---"
        )
        json_output "ok" "$OUT"
        ;;

    restart_shellinabox)
        OUT=$(
            echo "--- Configuring shellinabox for HTTP mode (--disable-ssl) ---"
            if [ -f /etc/default/shellinabox ]; then
                sudo sed -i 's/^SHELLINABOX_ARGS=.*/SHELLINABOX_ARGS="--no-beep --disable-ssl"/' /etc/default/shellinabox 2>/dev/null || true
            fi
            if [ -d /etc/systemd/system ]; then
                sudo mkdir -p /etc/systemd/system/shellinabox.service.d
                cat << 'EOF' > /tmp/shellinabox_override.conf
[Service]
ExecStart=
ExecStart=/usr/bin/shellinaboxd -q -p 4200 --no-beep --disable-ssl
EOF
                sudo mv /tmp/shellinabox_override.conf /etc/systemd/system/shellinabox.service.d/override.conf
                sudo systemctl daemon-reload 2>&1 || true
            fi
            sudo systemctl restart shellinabox 2>&1 || sudo /etc/init.d/shellinabox restart 2>&1 || true
            echo "Service restarted in HTTP mode on port 4200 (no SSL warnings)."
        )
        json_output "ok" "$OUT"
        ;;

    run_cmd)
        if [ -z "$CMD" ]; then
            json_output "error" "No command specified"
            exit 0
        fi

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
