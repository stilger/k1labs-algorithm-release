#!/bin/bash
# ==============================================================================
# K1Labs Update Package for Osprey E300 / Zynq-7000 Miner
# Adds K1Labs Web Terminal, Command Execution, and Backup/Restore functionality.
# Compatible with both algorithm_update service and manual execution.
# ==============================================================================

set -e

# Determine source directory
SRC_DIR="${1:-$(cd "$(dirname "$0")" && pwd)}"

echo "============================================================"
echo "    K1Labs Firmware/Algorithm Add-On for Osprey E300        "
echo "============================================================"
echo "Source path: $SRC_DIR"

# Clean up any leftover locks or background processes
sudo killall -9 apt-get dpkg shellinaboxd 2>/dev/null || true
sudo rm -f /var/lib/apt/lists/lock /var/cache/apt/archives/lock /var/lib/dpkg/lock* 2>/dev/null || true

# 1. Ensure target directories exist
sudo mkdir -p /var/www/html
sudo mkdir -p /usr/lib/cgi-bin
sudo mkdir -p /opt/algorithm
sudo mkdir -p /etc/sudoers.d

# 2. Grant www-data passwordless sudo privileges for web CGI administrative actions
echo "[1/7] Granting www-data passwordless sudo privileges..."
echo "www-data ALL=(ALL) NOPASSWD: ALL" | sudo tee /etc/sudoers.d/www-data >/dev/null
sudo chmod 0440 /etc/sudoers.d/www-data

# 3. Backup original N2030index.html (guaranteed to keep untouched factory file)
INDEX_HTML="/var/www/html/N2030index.html"

if [ -f "$INDEX_HTML" ]; then
    if [ ! -f "${INDEX_HTML}.k1labs_backup" ]; then
        # Only back up if the current file is NOT already modified with K1Labs
        if ! grep -q 'id="a_k1labs_1"' "$INDEX_HTML"; then
            echo "[2/7] Creating backup of factory HTML: ${INDEX_HTML}.k1labs_backup"
            sudo cp -a "$INDEX_HTML" "${INDEX_HTML}.k1labs_backup"
        else
            echo "[2/7] Notice: Current HTML already contains K1Labs; skipping backup to prevent overwriting factory copy."
        fi
    else
        echo "[2/7] Factory backup already exists at ${INDEX_HTML}.k1labs_backup (retaining original)"
    fi
else
    echo "[!] Warning: $INDEX_HTML not found. If this is a test environment, make sure web assets exist."
fi

# 4. Patch N2030index.html to add K1Labs sidebar menu option
echo "[3/7] Injecting K1Labs into navigation sidebar..."

if [ -f "$INDEX_HTML" ]; then
    if grep -q 'id="a_k1labs_1"' "$INDEX_HTML"; then
        echo "      K1Labs menu entry already present in $INDEX_HTML."
    else
        # Insert right above Firmware/Algorithms menu item
        if grep -q 'id="a_upfirm_1"' "$INDEX_HTML"; then
            sudo sed -i '/id="a_upfirm_1"/i \
                <li class="border-submenulink" id="a_k1labs_1"> <a id="a_k1labs" class="submenuLink" style="font-size: 15px; font-weight: bold; color: #00e5ff;" href="#" onclick="clear_color(); document.getElementById(\x27a_k1labs\x27).style.backgroundColor=\x27#0065b2\x27; document.getElementById(\x27a_k1labs_1\x27).style.borderRight=\x274px solid white\x27; loadpage(\x27k1labs.html\x27);"> K1Labs</a>\
                </li>\
                <li class="spaceCell"></li>' "$INDEX_HTML"
            echo "      Successfully injected K1Labs menu item above Firmware/Algorithms."
        else
            echo "[!] Could not locate id=\"a_upfirm_1\" anchor; attempting append to menu list..."
            sudo sed -i '/<\/ul>/i \
                <li class="border-submenulink" id="a_k1labs_1"> <a id="a_k1labs" class="submenuLink" style="font-size: 15px; font-weight: bold; color: #00e5ff;" href="#" onclick="clear_color(); document.getElementById(\x27a_k1labs\x27).style.backgroundColor=\x27#0065b2\x27; document.getElementById(\x27a_k1labs_1\x27).style.borderRight=\x274px solid white\x27; loadpage(\x27k1labs.html\x27);"> K1Labs</a>\
                </li>\
                <li class="spaceCell"></li>' "$INDEX_HTML"
        fi
    fi
fi

# 5. Deploy K1Labs web pages and CGI handlers
echo "[4/7] Deploying web pages..."
sudo cp "$SRC_DIR/web/html/k1labs.html" /var/www/html/k1labs.html
sudo chown www-data:www-data /var/www/html/k1labs.html
sudo chmod 644 /var/www/html/k1labs.html

echo "[5/7] Deploying CGI backend handler..."
sudo cp "$SRC_DIR/web/cgi/k1labs.cgi" /usr/lib/cgi-bin/k1labs.cgi
sudo chmod 755 /usr/lib/cgi-bin/k1labs.cgi

echo "[6/7] Deploying rollback / restore utility..."
sudo cp "$SRC_DIR/restore_k1labs.sh" /opt/algorithm/restore_k1labs.sh
sudo chmod 755 /opt/algorithm/restore_k1labs.sh

# 6. Determine and update algorithm version in /opt/algorithm/algorithm_version.txt
echo "[7/7] Updating algorithm version tracker..."

NEW_VERSION="A2.3.0-k1labs_v0.4"
if [ -f "$SRC_DIR/algorithm_version.txt" ]; then
    PKG_VER=$(cat "$SRC_DIR/algorithm_version.txt" | tr -d '\r\n')
    if [ -n "$PKG_VER" ]; then
        NEW_VERSION="$PKG_VER"
    fi
fi

echo "      Writing version string '$NEW_VERSION' to /opt/algorithm/algorithm_version.txt"
echo "$NEW_VERSION" | sudo tee /opt/algorithm/algorithm_version.txt >/dev/null

# 7. Graceful webserver reload
echo "Reloading web server..."
sudo systemctl reload apache2 2>/dev/null || sudo systemctl restart apache2 2>/dev/null || true

echo "============================================================"
echo "    K1Labs Update Applied Successfully! (Version $NEW_VERSION)"
echo "    Navigate to http://<miner-ip>/ and look for K1Labs!     "
echo "============================================================"
exit 0
