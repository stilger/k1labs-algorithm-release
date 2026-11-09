# K1Labs Management Add-On for Osprey E300 (Zynq-7000)

Custom algorithm/firmware add-on that adds a **K1Labs** management suite to the Osprey E300 web interface with:
1. **Shellinabox In-Browser Terminal**: Install, configure, remove, or launch a root web terminal on port `4200` directly over HTTP (no SSL warnings).
2. **Custom Command Runner**: Execute any shell command directly from the web browser with live stdout/stderr display.
3. **Automatic Backups & One-Click Rollback**: Automatically backs up original system files (`N2030index.html.k1labs_backup`) and includes a one-click rollback button (or script) to restore factory web pages and reset the Git update path back to official PachiraMining.
4. **Custom Versioning**: Sets algorithm version to `A2.3.0-k1labs_v0.1` (or your chosen tag increment like `v0.2`, `v0.3`, etc.).

---

## Repository Structure

```text
k1labs-algorithm-update/
├── .gitattributes             # Enforces Unix LF line endings
├── update.sh                 # Main update script invoked by algorithm_update service
├── restore_k1labs.sh         # Rollback script to revert back to factory defaults
├── algorithm_version.txt     # Release version string (A2.3.0-k1labs_v0.1)
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
2. Commit your changes to `main` with a message like: `Release A2.3.0-k1labs_v0.1`.
3. Tag the commit:
   - In the **History** tab, right-click the commit &rarr; select **Create Tag...**
   - Enter:
     ```text
     A2.3.0-k1labs_v0.1
     ```
   - Click **Create Tag**.
4. Click **Push origin** (with tags) to push to your repository.

---

### Step 2: Update on Your Osprey E300

1. Go to your miner's web UI: `http://<miner-ip>/N206upfirmware.html`
2. Under **Algorithm settings/status**:
   * **Git Link**: `https://github.com/<your-username>/<your-repo-name>.git`
   * **Git Key**: *(Leave empty if public, or enter your GitHub PAT if private)*
3. Click **Save**.

The miner will detect tag **`A2.3.0-k1labs_v0.1`**, run `update.sh`, update the displayed algorithm version to **`A2.3.0-k1labs_v0.1`**, and deploy K1Labs.

For future updates, you can simply increment the tag:
- `A2.3.0-k1labs_v0.2`
- `A2.3.0-k1labs_v0.3`
...and update `algorithm_version.txt` to match!

---

## Rollback / Restore Defaults

If you ever want to revert back to official factory defaults:
- **From Web UI**: Scroll to the bottom of the K1Labs page and click **"Restore Defaults & Remove K1Labs"**.
- **From Terminal**: Run `sudo /bin/bash /opt/algorithm/restore_k1labs.sh`.

Both will:
1. Restore `/var/www/html/N2030index.html` from the backup.
2. Delete K1Labs web and CGI files.
3. Strip `-k1labs*` from `/opt/algorithm/algorithm_version.txt` (returning it to `A2.3.0`).
4. Reset Git repo URL in `algo_config.json` and `algorithm_update.service` back to `https://github.com/PachiraMining/Algorithm-official-release-v2.git`.
5. Restart the `algorithm_update` service and Apache webserver.
