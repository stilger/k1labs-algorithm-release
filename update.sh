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

# 1. Ensure target directories exist
sudo mkdir -p /var/www/html
sudo mkdir -p /usr/lib/cgi-bin
sudo mkdir -p /opt/algorithm

# 2. Backup original N2030index.html if not already backed up
INDEX_HTML="/var/www/html/N2030index.html"

if [ -f "$INDEX_HTML" ]; then
    if [ ! -f "${INDEX_HTML}.k1labs_backup" ]; then
        echo "[1/6] Creating backup: ${INDEX_HTML}.k1labs_backup"
        sudo cp -a "$INDEX_HTML" "${INDEX_HTML}.k1labs_backup"
    else
        echo "[1/6] Existing backup found at ${INDEX_HTML}.k1labs_backup (retaining original)"
    fi
else
    echo "[!] Warning: $INDEX_HTML not found. If this is a test environment, make sure web assets exist."
fi

# 3. Patch N2030index.html to add K1Labs sidebar menu option
echo "[2/6] Injecting K1Labs into navigation sidebar..."

K1_MENU_ITEM='                <li class="border-submenulink" id="a_k1labs_1"> <a id="a_k1labs" class="submenuLink" style="font-size: 15px; font-weight: bold; color: #00e5ff;" href="#" onclick="clear_color(); document.getElementById(\x27a_k1labs\x27).style.backgroundColor=\x27#0065b2\x27; document.getElementById(\x27a_k1labs_1\x27).style.borderRight=\x274px solid white\x27; loadpage(\x27k1labs.html\x27);"> K1Labs</a>\n                </li>\n                <li class="spaceCell"></li>'

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

# 4. Deploy K1Labs web pages and CGI handlers
echo "[3/6] Deploying web pages..."
sudo cp "$SRC_DIR/web/html/k1labs.html" /var/www/html/k1labs.html
sudo chown www-data:www-data /var/www/html/k1labs.html
sudo chmod 644 /var/www/html/k1labs.html

echo "[4/6] Deploying CGI backend handler..."
sudo cp "$SRC_DIR/web/cgi/k1labs.cgi" /usr/lib/cgi-bin/k1labs.cgi
sudo chmod 755 /usr/lib/cgi-bin/k1labs.cgi

echo "[5/6] Deploying rollback / restore utility..."
sudo cp "$SRC_DIR/restore_k1labs.sh" /opt/algorithm/restore_k1labs.sh
sudo chmod 755 /opt/algorithm/restore_k1labs.sh

# 5. Update local version tracking for algorithm_update service
echo "[6/6] Updating algorithm version tracker..."
NEW_VERSION="1.0.0"
if [ -f "$SRC_DIR/algorithm_version.txt" ]; then
    NEW_VERSION=$(cat "$SRC_DIR/algorithm_version.txt" | tr -d '\r\n')
fi
echo "$NEW_VERSION" | sudo tee /opt/algorithm/algorithm_version.txt >/dev/null

# 6. Graceful webserver reload
echo "Reloading web server..."
sudo systemctl reload apache2 2>/dev/null || sudo systemctl restart apache2 2>/dev/null || true

echo "============================================================"
echo "    K1Labs Update Applied Successfully! (Version $NEW_VERSION)  "
echo "    Navigate to http://<miner-ip>/ and look for K1Labs!     "
echo "============================================================"
exit 0
