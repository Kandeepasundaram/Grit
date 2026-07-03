# Grit Free Tier — Help Guide

Grit is a session-based Git profile manager for macOS, Linux, and Windows. It runs as a background daemon and automatically applies the right Git identity (name, email, GPG key, SSH key) per repository, so you commit as the correct person every time.

---

## Installation

```bash
pip install grit-cli
```

Requires Python 3.8+ and Git 2.x. Works on Windows, macOS, and Linux.

> The distribution is published as `grit-cli` on PyPI, but installs the `grit` command.

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

A profile is a named Git identity. The free tier supports **up to 5 profiles**; Pro tier adds unlimited.

```bash
# Create a profile
grit profile add --name "Work" --email "you@company.com"
grit profile add --name "Personal" --email "you@gmail.com"

# Add GPG commit signing
grit profile add --name "Work" --email "you@company.com" --gpg-key-id ABC12345

# Add a dedicated SSH key
grit profile add --name "Work" --email "you@company.com" --ssh-key "~/.ssh/id_work"

# Add an HTTP username for HTTPS git push/pull
grit profile edit Work --http-username your-github-username

# List all profiles
grit profile list

# Show one profile
grit profile show Work

# Edit a profile
grit profile edit Work --email "new@company.com"

# Delete a profile
grit profile delete Personal

# Set a default profile (fallback when auto-detection finds nothing)
grit profile set-default Work

# Remove the default
grit profile unset-default
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

Drop a `.grit` file in a repo root to assign it to a specific profile:

```
profile = Work
```

### Detection order

When you commit in a repo with no active session, Grit checks in this order:

1. `.grit` file in the repo root
2. Path pattern match
3. Remote URL pattern match
4. Default profile (if set)
5. → Opens a profile picker dialog (your choice is remembered for 8 hours)

---

## Sessions

A session ties a profile to a repo for **8 hours** (configurable). After that, Grit re-prompts.

```bash
# Show the active session for the current repo
grit session show

# Manually switch profiles for this repo (creates a new session)
grit session set Work

# List all active sessions
grit session list

# Clear the session (forces re-prompt on next commit)
grit session clear

# Pin a profile to this repo as a fallback (survives session TTL)
# Unlike a session, a pin is only used if auto-detect finds no match
grit session pin Work

# Remove a pin
grit session unpin
```

---

## HTTPS Credentials

Store GitHub credentials per profile in your OS credential store for seamless HTTPS `git push/pull`:

```bash
# Save credentials for a profile (opens a browser for GitHub OAuth)
grit credential login Work

# Remove saved credentials
grit credential remove Personal

# List all saved credentials
grit credential list
```

When an active Grit session's profile has stored credentials, Git automatically uses them for HTTPS operations.

---

## The Daemon

The daemon is a lightweight background process that handles all profile resolution.

```bash
grit daemon start                      # start in background
grit daemon start --foreground --verbose   # for debugging
grit daemon status                     # uptime, active sessions
grit daemon stop
grit daemon restart
```

The daemon starts automatically on login after `grit setup`. To disable autostart:

```bash
# Linux
systemctl --user disable grit

# macOS
launchctl unload ~/Library/LaunchAgents/com.grit.daemon.plist

# Windows
# Uninstall the registry entry via regedit, or run:
grit setup   # and choose "no" when asked about autostart
```

---

## Git Hook

Grit intercepts commits using a `pre-commit` hook. The daemon installs hooks automatically when it first detects a new repository (by watching for `.git/COMMIT_EDITMSG`).

Verify the hook is present:

```bash
cat .git/hooks/pre-commit
# Should include a line with: GRIT_HOOK_v1
```

If a repo was cloned before Grit was running, trigger hook installation by making any commit — the daemon will catch it — or:

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

# Reset a setting to its default
grit config reset session_ttl_hours
```

---

## System Tray

After `grit daemon start`, a tray icon appears in your system tray showing:

- The active profile for the foremost Git repo (if detectable)
- A menu to switch profiles or clear the current session
- A link to open the repository in your file manager

The icon color is stable per profile, so you can tell at a glance which identity is active.

---

## VS Code Extension

Install the **Grit** extension from the VS Code Marketplace. It adds:

- A status bar item showing the active profile for the current workspace
- `Grit: Switch Profile` command (via Ctrl/Cmd + Shift + P)
- `Grit: Show Session` and `Grit: Invalidate Session` commands

The extension communicates with the running daemon. No extra configuration is needed.

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

The popup requires a display server (X11, Wayland, or a Windows/macOS desktop session). On headless servers, set the profile manually:

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

Or pin a profile to this repo so it's not forgotten:

```bash
grit session pin Work
```

### Profile limit reached (free tier)

The free tier supports up to 5 profiles. Delete an unused one:

```bash
grit profile delete OldProfile
```

Or upgrade to Grit Pro for unlimited profiles (coming soon).

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

## Pro & Enterprise Tiers (Coming Soon)

Grit Pro ($5/month) adds:

- Unlimited profiles
- Cloud sync across machines (auto-sync every 5 seconds)
- Team profiles (read-only org-wide profiles)
- Device-flow OAuth2 login

Grit Enterprise adds:

- OIDC and SAML 2.0 single sign-on
- Enforce SSO requirement (compliance)
- Audit logs (append-only SIEM-ready trail)
- Compliance reporting
- Windows NT Service for multi-user deployments

See the main [README.md](../README.md) for more details on Pro and Enterprise features.

---

## Getting Help

- Main documentation: [README.md](../README.md)
- PRD & roadmap: [Docs/PRD.md](./PRD.md)
- Report issues: [GitHub Issues](https://github.com/Kandeepasundaram/Grit/issues)
- Email: kandeepasundaram+GRIT@gmail.com
