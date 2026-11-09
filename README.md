# K1Labs Management Add-On for Osprey E300 (Zynq-7000)

Custom algorithm/firmware add-on that adds a **K1Labs** management suite to the Osprey E300 web interface with:
1. **Shellinabox In-Browser Terminal**: Install, configure, remove, or launch a root web terminal on port `4200` (`https://<miner-ip>:4200`).
2. **Custom Command Runner**: Execute any shell command directly from the web browser with stdout/stderr display.
3. **Automatic Backups & One-Click Rollback**: Automatically backs up original system files (`N2030index.html.k1labs_backup`) and includes a one-click rollback button (or script) to restore factory web pages and reset the Git update path back to official PachiraMining.
4. **Custom Versioning**: Reads `/opt/algorithm/algorithm_version.txt` and appends `-k1labs` (so `A2.3.0` becomes `A2.3.0-k1labs`) visible on the web UI and CLI.

---

## Repository Structure

```text
k1labs-algorithm-update/
├── .gitattributes             # Enforces Unix LF line endings
├── update.sh                 # Main update script invoked by algorithm_update service
├── restore_k1labs.sh         # Rollback script to revert back to factory defaults
├── algorithm_version.txt     # Target version string (A2.3.0-k1labs)
├── web/
│   ├── html/
│   │   └── k1labs.html       # K1Labs web dashboard
│   └── cgi/
│       └── k1labs.cgi        # Backend CGI handler for shellinabox & commands
└── README.md
```

---

## Deploying with GitHub Desktop to Your Osprey E300

### Step 1: Open in GitHub Desktop & Push
1. Open **GitHub Desktop**.
2. Click **File &rarr; Add Local Repository...** and select this folder:
   `C:\Users\stilger\.gemini\antigravity\scratch\k1labs-algorithm-update`
3. Click **Publish repository** to push it to your GitHub account (leave on `main` or `master` branch, no extra branches needed).
4. Create a tag named **`A2.3.0-k1labs`**:
   - In GitHub Desktop, right-click on the latest commit &rarr; **Create Tag...** &rarr; enter **`A2.3.0-k1labs`**.
   - Click **Push origin** (with tags) so the tag is pushed to GitHub.

> **Why the tag `A2.3.0-k1labs` is needed:** The Osprey's `algorithm_update` daemon looks for remote Git tags. When it sees `A2.3.0-k1labs` on your repo (and the miner is currently on `A2.3.0`), it triggers the update.

---

### Step 2: Point Your Osprey E300 to Your Repository

#### Option A: Through the Web UI (Recommended)
1. Open your miner's web UI: `http://<miner-ip>/N206upfirmware.html`
2. Scroll to the **Algorithm settings/status** section at the bottom.
3. In **Git Link**, enter your repository URL:
   `https://github.com/<your-username>/<your-repo-name>.git`
   *(If the repository is private, enter your GitHub Personal Access Token in **Git Key**).*
4. Click **Save**.
5. The miner restarts the `algorithm_update` service, fetches tag `A2.3.0-k1labs`, runs `update.sh`, and upgrades.

#### Option B: Immediate SSH Execution (Manual)
If you prefer not to wait for the 5-minute polling cycle:
```bash
git clone --branch A2.3.0-k1labs https://github.com/<your-username>/<your-repo-name>.git /tmp/k1labs
sudo chmod +x /tmp/k1labs/update.sh
sudo /tmp/k1labs/update.sh /tmp/k1labs/
```

---

## Verification & Usage

Refresh your browser at `http://<miner-ip>/`:
- The blue **Algorithm version** box under *Firmware/Algorithms* now reads: **`A2.3.0-k1labs`**.
- Click the new **K1Labs** item in the sidebar:
  1. **Install Shellinabox**: Click *Install Shellinabox* (installs and starts the terminal service).
  2. **Access Web Terminal**: Click *Open Terminal (Port 4200)* &rarr; opens `https://<miner-ip>:4200`.
     *(Note: Accept your browser's self-signed SSL warning on first visit).*
  3. **Execute Custom Commands**: Enter commands like `uptime`, `dmesg`, `ifconfig`, or `systemctl status` to monitor and manage the board in real time.
  4. **Remove Shellinabox**: Click *Remove Shellinabox* to stop and cleanly purge the service.

---

## Rollback / Restore Defaults

If you ever want to revert back to official factory defaults:
- **From Web UI**: Scroll to the bottom of the K1Labs page and click **"Restore Defaults & Remove K1Labs"**.
- **From Terminal**: Run `sudo /opt/algorithm/restore_k1labs.sh`.

Both will:
1. Restore `/var/www/html/N2030index.html` from the backup.
2. Delete K1Labs web and CGI files.
3. Strip `-k1labs` from `/opt/algorithm/algorithm_version.txt` (returning it to `A2.3.0`).
4. Reset Git repo URL in `algo_config.json` and `algorithm_update.service` back to `https://github.com/PachiraMining/Algorithm-official-release-v2.git`.
5. Restart the `algorithm_update` service and Apache webserver.
