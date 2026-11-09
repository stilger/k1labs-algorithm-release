#!/bin/bash
# ==============================================================================
# K1Labs Restore / Rollback Script for Osprey E300
# Reverts web UI modifications and restores default PachiraMining Git path.
# ==============================================================================

set -e

echo "=== [K1Labs Rollback] Starting restore to factory defaults ==="

# 1. Restore HTML backup
if [ -f /var/www/html/N2030index.html.k1labs_backup ]; then
    echo "Restoring /var/www/html/N2030index.html from backup..."
    sudo cp -f /var/www/html/N2030index.html.k1labs_backup /var/www/html/N2030index.html
    sudo rm -f /var/www/html/N2030index.html.k1labs_backup
else
    echo "Backup file not found. Stripping K1Labs menu entry manually..."
    sudo sed -i '/a_k1labs_1/,/spaceCell/d' /var/www/html/N2030index.html || true
fi

# 2. Remove K1Labs web and CGI files
echo "Cleaning up K1Labs files..."
sudo rm -f /var/www/html/k1labs.html
sudo rm -f /usr/lib/cgi-bin/k1labs.cgi
sudo rm -f /opt/algorithm/restore_k1labs.sh

# 3. Strip -k1labs suffix from algorithm version in /opt/algorithm/algorithm_version.txt
if [ -f /opt/algorithm/algorithm_version.txt ]; then
    echo "Restoring base algorithm version string in /opt/algorithm/algorithm_version.txt..."
    CUR_VER=$(cat /opt/algorithm/algorithm_version.txt | tr -d '\r\n')
    CLEAN_VER="${CUR_VER%-k1labs}"
    [ -z "$CLEAN_VER" ] && CLEAN_VER="A2.3.0"
    echo "$CLEAN_VER" | sudo tee /opt/algorithm/algorithm_version.txt >/dev/null
fi

# 4. Restore default PachiraMining algorithm configuration
echo "Resetting /opt/algorithm/algo_config.json to official default..."
sudo cat << 'EOF' > /tmp/default_algo_config.json
{
  "gitlink": "",
  "gitpassword": "",
  "path": "https://github.com/PachiraMining/Algorithm-official-release-v2.git"
}
EOF
sudo mv /tmp/default_algo_config.json /opt/algorithm/algo_config.json
sudo chmod 644 /opt/algorithm/algo_config.json

# 5. Restore algorithm_update.service with default official Git URL
echo "Restoring /etc/systemd/system/algorithm_update.service..."
sudo cat << 'EOF' > /tmp/algorithm_update.service
[Unit]
Description=algorithm_update
Wants=network.target
After=syslog.target network-online.target

[Service]
Type=simple
ExecStartPre=/bin/sleep 8
ExecStart=/opt/algorithm/algorithm_update /opt/algorithm/ https://github.com/PachiraMining/Algorithm-official-release-v2.git
Restart=always
WatchdogSec=12000
KillMode=control-group

[Install]
WantedBy=multi-user.target
EOF
sudo mv /tmp/algorithm_update.service /etc/systemd/system/algorithm_update.service
sudo chmod 644 /etc/systemd/system/algorithm_update.service

# 6. Reload systemd and restart algorithm update service
echo "Reloading systemd daemon and restarting algorithm_update..."
sudo systemctl daemon-reload
sudo systemctl restart algorithm_update.service || true

# 7. Restart webserver to ensure cache is cleared
echo "Restarting webserver..."
sudo systemctl restart apache2 || true

echo "=== [K1Labs Rollback] Successfully restored factory defaults! ==="
