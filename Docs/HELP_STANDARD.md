# Grit Standard Edition — Help Guide

Grit Standard is the free, open-source tier. It runs a background daemon that remembers which
Git identity (name, email, GPG key, SSH key) you use per repository, so the right profile is
applied automatically every time you commit.

---

## Installation

```bash
pip install grit
```

Requires Python 3.8+ and Git 2.x. Works on Windows, macOS, and Linux.

---

## First Run

```bash
grit setup
```

The wizard will:
- Create your config directory
- Create your first profile
- Install the daemon autostart entry for your OS
- Optionally start the daemon right away

---

## Profiles

A profile is a named Git identity. You can have up to **5 profiles** on the free tier.

```bash
# Create a profile
grit profile add --name "Work" --email "you@company.com"
grit profile add --name "Personal" --email "you@gmail.com"

# Add GPG commit signing to a profile
grit profile add --name "Work" --email "you@company.com" --gpg-key-id ABC12345

# Add a dedicated SSH key
grit profile add --name "Work" --email "you@company.com" --ssh-key "~/.ssh/id_work"

# List all profiles
grit profile list

# Show one profile
grit profile show Work

# Edit a profile
grit profile edit Work --email "new@company.com"

# Delete a profile
grit profile delete Personal
```

---

## Auto-Detection

Grit can pick the right profile automatically so you never have to think about it.

### Path patterns

Match repositories by folder path:

```bash
grit profile edit Work --path-pattern "~/work/*"
grit profile edit Personal --path-pattern "~/personal/*"
```

Any repo under `~/work/` will automatically use the Work profile.

### Remote URL patterns

Match by the repo's `git remote origin` URL:

```bash
grit profile edit Work --remote-pattern "github.com/my-company/*"
```

### `.grit` file (highest priority)

Drop a `.grit` file in a repo root to pin it to a specific profile:

```
profile = Work
```

### Detection order

When you commit in a repo with no active session, Grit checks in this order:

1. `.grit` file in the repo root
2. Path pattern match
3. Remote URL match
4. → Opens a profile picker dialog (your choice is remembered)

---

## Sessions

A session ties a profile to a repo for **8 hours** (configurable). After that, Grit re-prompts.

```bash
# Show the active session for the current repo
grit session show

# Manually switch profiles for this repo
grit session set Work

# Clear the session (forces re-prompt on next commit)
grit session clear

# See all active sessions
grit session list
```

---

## The Daemon

The daemon is a lightweight background process that handles all profile resolution.

```bash
grit daemon start          # start in background
grit daemon start --foreground --verbose   # for debugging
grit daemon status         # uptime, active sessions
grit daemon stop
grit daemon restart
```

The daemon starts automatically on login after `grit setup`. You can disable this:

```bash
# Linux
systemctl --user disable grit

# macOS
launchctl unload ~/Library/LaunchAgents/com.grit.daemon.plist

# Windows
grit daemon stop
# Remove the Run key via regedit or:
grit setup   # and choose "no" when asked about autostart
```

---

## Git Hook

Grit intercepts commits using a `pre-commit` hook. The daemon installs hooks automatically
when it first detects a new repository (by watching for `.git/COMMIT_EDITMSG`).

You can verify the hook is present:

```bash
cat .git/hooks/pre-commit
# Should include a line with: grit hook pre-commit
```

If a repo was cloned before Grit was running, you can trigger hook installation by making
any commit — the daemon will catch it — or by running:

```bash
grit daemon restart   # re-scans watched repos
```

---

## Configuration

```bash
# View all settings
grit config list

# Change session lifetime (default: 8 hours)
grit config set session_ttl_hours 4

# Turn off auto-detection (always prompt instead)
grit config set auto_detect false

# Enable/disable desktop notifications
grit config set notifications_enabled true

# Set a default profile used when nothing else matches
grit config set default_profile_id <profile-id>

# Reset a setting to its default
grit config reset session_ttl_hours
```

---

## System Tray

After `grit daemon start`, a tray icon appears in your system tray. It shows:

- The active profile for the foremost Git repo (if detectable)
- A menu to switch profiles or clear the current session
- A link to open this repository in your file manager

The icon colour changes per profile — stable, based on the profile ID — so you can
tell at a glance which identity is active.

---

## VS Code Extension

Install the **Grit** extension from the VS Code Marketplace. It adds:

- A status bar item showing the active profile for the current workspace
- `Grit: Switch Profile` command (Ctrl/Cmd + Shift + P)
- `Grit: Show Session` and `Grit: Invalidate Session` commands

The extension communicates with the running daemon over the same IPC channel as the CLI.
No extra configuration is needed beyond having the daemon running.

---

## Troubleshooting

### No profile is applied after committing

```bash
# Check the daemon is running
grit daemon status

# Check a session exists
grit session show

# Force-apply a profile
grit session set Work

# Verify git sees the right values
git config --local user.name
git config --local user.email
```

### The profile picker doesn't appear

The popup requires a display server (X11, Wayland, or a Windows/macOS desktop session).
On headless servers, set the profile manually:

```bash
grit session set Work
```

### The hook isn't installed

```bash
cat .git/hooks/pre-commit   # check if it exists and contains GRIT_HOOK_v1
grit daemon restart          # triggers re-scan of watched repos
```

### Session expires too quickly

```bash
grit config set session_ttl_hours 24
```

Or lock a session so it never expires:

```bash
grit session set Work --lock
```

### Profile limit reached (free tier)

The free tier supports up to 5 profiles. Delete an unused one:

```bash
grit profile delete OldProfile
```

Or upgrade to [Grit Pro](https://grit.dev/pricing) for unlimited profiles.

---

## Config & Data Locations

| Platform | Path |
|----------|------|
| Linux | `~/.config/grit/` |
| macOS | `~/Library/Application Support/grit/` |
| Windows | `%APPDATA%\grit\` |
| Override | Set the `GRIT_CONFIG_DIR` environment variable |

Key files:

| File | Contents |
|------|----------|
| `profiles.json` | All your profiles |
| `sessions.json` | Active sessions with TTL |
| `config.json` | App settings |
| `grit.pid` | Daemon process ID |
| `grit.sock` | IPC socket (macOS/Linux) |

---

## Upgrading to Pro

Grit Pro ($5/month) adds:

- Unlimited profiles
- Cloud sync across machines
- Team profile sharing

```bash
grit auth login   # connect your account
grit sync push    # push profiles to the cloud
grit sync pull    # pull profiles on another machine
```

See `Docs/SETUP.md` for the full Pro and Enterprise feature set.
