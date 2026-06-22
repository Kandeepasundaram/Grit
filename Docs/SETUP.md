# Grit — Setup Guide

## Requirements

- Python 3.8 or later
- Git 2.x
- Windows 10+, macOS 12+, or a Linux distro with a desktop session (for tray icon)

Optional:
- GPG (for commit signing)
- A custom SSH key per profile

---

## Installation

### From PyPI (recommended)

```bash
pip install grit
```

### From source

```bash
git clone https://github.com/your-org/grit
cd grit
pip install -e ".[dev]"
```

---

## First-Run Setup

Run the interactive onboarding wizard:

```bash
grit setup
```

This will:
1. Create the Grit config directory (platform-specific, or `GRIT_CONFIG_DIR` if set)
2. Prompt you to create your first profile (name + email)
3. Install the daemon autostart entry for your platform
4. Optionally start the daemon immediately

---

## Creating Profiles

```bash
# Add a profile
grit profile add --name "Work" --email "you@company.com"

# Add with GPG signing
grit profile add --name "Work" --email "you@company.com" --gpg-key-id ABC123

# Add with a dedicated SSH key
grit profile add --name "Work" --email "you@company.com" --ssh-key "~/.ssh/id_work"

# Add with path pattern (auto-apply when inside ~/work/*)
grit profile add --name "Work" --email "you@company.com" --path-pattern "~/work/*"

# List all profiles
grit profile list

# Edit an existing profile
grit profile edit Work --email "new@company.com"

# Delete a profile
grit profile delete Personal
```

---

## Starting the Daemon

```bash
# Start in the background (normal use)
grit daemon start

# Start in foreground (debugging)
grit daemon start --foreground --verbose

# Check status
grit daemon status

# Stop
grit daemon stop

# Restart after config changes
grit daemon restart
```

The daemon starts automatically on login after `grit setup` completes.

---

## Per-Repository Sessions

Grit remembers which profile you used per repository. Sessions default to **8 hours** TTL.

```bash
# Show the active session for the current repo
grit session show

# Manually set a profile for the current repo
grit session set Work

# Clear the active session (forces re-prompt on next commit)
grit session clear

# List all active sessions across all repos
grit session list
```

---

## Git Hook Installation

Grit intercepts commits via a `pre-commit` hook. Hooks are installed automatically when the daemon first sees a new repo. You can also manage them manually:

```bash
# Install hook in a repo
cd /path/to/repo
grit hook install    # (if exposed — otherwise daemon installs automatically)

# The hook calls:
#   grit hook pre-commit --repo <path>
# which resolves the active profile and writes it to local git config
# before the commit proceeds.
```

### Auto-detection

If no session exists for a repo, Grit tries to detect the right profile in this order:

1. `.grit` file in the repo root — highest priority
   ```ini
   profile = Work
   ```
2. **Path patterns** — e.g. `~/work/*` matches `/home/alice/work/project`
3. **Remote URL patterns** — e.g. `github.com/my-company/*`
4. → **Prompt** — a picker dialog appears and the choice is remembered

---

## Configuration

```bash
# View all settings
grit config list

# Common settings
grit config set session_ttl_hours 12       # session timeout (default: 8)
grit config set auto_detect true           # enable path/remote pattern detection
grit config set notifications_enabled true # desktop notifications on profile switch
grit config set default_profile_id <id>   # fallback profile if none matches

# Reset a setting to its default
grit config reset session_ttl_hours
```

---

## Cloud Sync (Pro)

Requires a Grit Pro subscription ($5/month).

```bash
# Authenticate
grit auth login

# Push local profiles to the cloud
grit sync push

# Pull profiles from the cloud (merge, last-write-wins)
grit sync pull

# Show sync status
grit sync status

# Sign out
grit auth logout
```

---

## Enterprise SSO

Requires a Grit Enterprise subscription.

### Configuration

```bash
# OIDC
grit enterprise config \
  --idp-type oidc \
  --idp-url https://accounts.your-company.com \
  --client-id grit-client-id \
  --org-id your-org \
  --org-name "Acme Corp" \
  --ttl-hours 8 \
  --enforce-sso

# SAML
grit enterprise config \
  --idp-type saml \
  --idp-url https://sso.your-company.com/saml \
  --org-id your-org
```

### Login

```bash
grit enterprise sso-login
# OIDC: opens browser device flow
# SAML: prints URL to open, then paste SAMLResponse

# Check session
grit enterprise sso-status

# Log out
grit enterprise sso-logout
```

When `--enforce-sso` is set, Grit will automatically select the profile matching your SSO identity on every commit — no manual profile switching required.

---

## Compliance Reporting

```bash
# Full JSON compliance report
grit compliance report

# Save to file
grit compliance report --output report.json

# Check hook installation across all watched repos
grit compliance hooks

# Check GPG signing across all profiles
grit compliance gpg
```

---

## Audit Log

```bash
# Show recent entries
grit audit show

# Filter by action and time
grit audit show --action profile_switch --since 2025-01-01T00:00:00Z

# Export as CSV
grit audit export --format csv --output audit.csv

# Clear the log (irreversible)
grit audit clear
```

---

## Windows Service (Enterprise, multi-user)

Run as Administrator:

```powershell
grit service install    # installs as NT Service (auto-start)
grit service start
grit service status
grit service stop
grit service uninstall
```

Data is stored in `%PROGRAMDATA%\Grit` when running as a service, allowing all users on the machine to share the daemon.

---

## Troubleshooting

### Daemon is not running
```bash
grit daemon status
grit daemon start
```

### Hook not firing
```bash
# Verify the hook is installed in your repo
cat .git/hooks/pre-commit
# Should contain a line with: grit hook pre-commit
```

### Profile not being applied
```bash
# Check the active session
grit session show

# Force-set the profile
grit session set "Work"

# Verify git config was written
git config --local user.email
```

### SSO login fails
- Ensure `grit enterprise config --idp-url` points to a reachable endpoint
- For OIDC, check that the device flow endpoint is enabled on your IdP
- For SAML, verify your org's SP metadata is registered

### Reset everything
```bash
grit daemon stop
# macOS/Linux
rm -rf ~/.config/grit ~/.local/share/grit
# Windows
rmdir /s /q "%APPDATA%\grit"
grit setup
```

---

## Data Locations

| Platform | Config & data |
|----------|---------------|
| Linux | `~/.config/grit/` |
| macOS | `~/Library/Application Support/grit/` |
| Windows | `%APPDATA%\grit\` |
| Enterprise (Windows Service) | `%PROGRAMDATA%\Grit\` |
| Override (all platforms) | Set `GRIT_CONFIG_DIR` env var |

Key files:

| File | Contents |
|------|----------|
| `profiles.json` | All profiles |
| `sessions.json` | Active sessions with TTL |
| `config.json` | App settings |
| `grit.sock` | IPC socket (macOS/Linux) |
| `grit.pid` | Daemon PID |
| `license.json` | Pro/Enterprise license JWT |
| `tokens.json` | OAuth tokens (chmod 600) |
| `enterprise.json` | SSO configuration |
| `sso_session.json` | Active SSO session |
| `audit.log` | Append-only audit log (JSON lines) |
| `team_profiles.json` | Read-only team profiles from cloud |
