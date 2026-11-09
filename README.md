# K1Labs Management Add-On for Osprey E300 (Zynq-7000)

Custom algorithm/firmware add-on that adds a **K1Labs** management suite to the Osprey E300 web interface with:
1. **Shellinabox In-Browser Terminal**: Install, configure, remove, or launch a root web terminal on port `4200` (`https://<miner-ip>:4200`).
2. **Custom Command Runner**: Execute any shell command directly from the web browser with stdout/stderr display.
3. **Automatic Backups & One-Click Rollback**: Automatically backs up original system files (`N2030index.html.k1labs_backup`) and includes a one-click rollback button (or script) to restore factory web pages and reset the Git update path back to official PachiraMining.

---

## Repository Structure

```text
k1labs-algorithm-update/
├── update.sh                 # Main update script invoked by algorithm_update service
├── restore_k1labs.sh         # Rollback script to revert back to factory defaults
├── algorithm_version.txt     # Release version tag (1.0.0)
├── web/
│   ├── html/
│   │   └── k1labs.html       # K1Labs web dashboard
│   └── cgi/
│       └── k1labs.cgi        # Backend CGI handler for shellinabox & commands
└── README.md
```

---

## Quick Setup: Deploying via GitHub to your Osprey E300

### Step 1: Create a GitHub Repository
1. Log in to GitHub and create a new repository (e.g. `k1labs-e300-release` or any name you prefer). It can be **Public** or **Private**.

### Step 2: Push this Repository and Create Release Tag `1.0.0`
In this directory (`k1labs-algorithm-update`), run:

```bash
git init
git add .
git commit -m "Initial K1Labs release v1.0.0"
git branch -M main
git remote add origin https://github.com/<your-username>/<your-repo-name>.git
git push -u origin main

# Create the semantic version tag (required by algorithm_update service)
git tag 1.0.0
git push origin 1.0.0
```

> **Note:** The `algorithm_update` service looks for numerical semantic version tags (e.g., `1.0.0`, `1.0.1`, etc.). Tagging your commit is what triggers the miner to update.

---

### Step 3: Point Your Osprey E300 to Your Repository

You can trigger the update either through the Web UI or via SSH/CLI:

#### Option A: Via Web UI (Easiest)
1. Open your miner's web UI: `http://<miner-ip>/N206upfirmware.html`
2. Scroll to **Algorithm settings/status**:
   - **Git Link**: `https://github.com/<your-username>/<your-repo-name>.git`
   - **Git Key**: If the repository is private, enter your GitHub Personal Access Token (PAT). If public, leave empty.
3. Click **Save**.
4. The miner restarts the `algorithm_update` service, queries your Git repo tags, clones branch `1.0.0`, and runs `update.sh`.

#### Option B: Via SSH Command Line
Log in to the miner as `root` (or sudo) and run:
```bash
# 1. Update the algorithm service configuration
sudo cat << 'EOF' > /tmp/algo_config.json
{
  "gitlink": "https://github.com/<your-username>/<your-repo-name>.git",
  "gitpassword": "",
  "path": "https://github.com/<your-username>/<your-repo-name>.git"
}
EOF
sudo mv /tmp/algo_config.json /opt/algorithm/algo_config.json

# 2. Update the systemd unit
sudo sed -i 's|ExecStart=.*|ExecStart=/opt/algorithm/algorithm_update /opt/algorithm/ https://github.com/<your-username>/<your-repo-name>.git|' /etc/systemd/system/algorithm_update.service

# 3. Reload and restart
sudo systemctl daemon-reload
sudo systemctl restart algorithm_update.service
```

---

## How It Works

1. The `algorithm_update` background daemon queries `git ls-remote --tags` every 5 minutes.
2. When tag `1.0.0` is detected, it clones the repo to `/tmp/algorithm_update/` and runs `sudo /tmp/algorithm_update/update.sh /tmp/algorithm_update/`.
3. `update.sh`:
   - Backs up `/var/www/html/N2030index.html` &rarr; `/var/www/html/N2030index.html.k1labs_backup`
   - Injects the **K1Labs** menu item into the left sidebar above *Firmware/Algorithms*.
   - Installs `k1labs.html` into `/var/www/html/` and `k1labs.cgi` into `/usr/lib/cgi-bin/`.
   - Writes `1.0.0` to `/opt/algorithm/algorithm_version.txt`.
   - Reloads Apache2.

---

## Using K1Labs

Refresh your browser at `http://<miner-ip>/` and click the new **K1Labs** item in the sidebar:

1. **Install Shellinabox**: Click *Install Shellinabox*. It runs `apt-get install -y shellinabox` and starts the service.
2. **Access Web Terminal**: Click *Open Terminal (Port 4200)* &rarr; opens `https://<miner-ip>:4200`.
   *(Note: Accept your browser's self-signed SSL warning on first visit).*
3. **Execute Custom Commands**: Enter commands like `uptime`, `dmesg`, `ifconfig`, or `systemctl status` to monitor and manage the board in real time.
4. **Remove Shellinabox**: Click *Remove Shellinabox* to stop and cleanly purge the service.

---

## Rollback / Restore Defaults

If you ever want to revert everything:
- **From Web UI**: Scroll to the bottom of the K1Labs page and click **"Restore Defaults & Remove K1Labs"**.
- **From Terminal**: Run `sudo /opt/algorithm/restore_k1labs.sh`.

Both will:
1. Restore `/var/www/html/N2030index.html` from the backup.
2. Delete K1Labs web and CGI files.
3. Reset Git repo URL in `algo_config.json` and `algorithm_update.service` back to `https://github.com/PachiraMining/Algorithm-official-release-v2.git`.
4. Restart the `algorithm_update` service and Apache webserver.
