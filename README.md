<p align="center">
  <img src="assets/grit_logo_hi_res.png" alt="Grit — Git Profile Manager" width="320" />
</p>

<h1 align="center">Grit</h1>

<p align="center">
  <strong>Session-based Git profile manager — right identity, every commit.</strong>
</p>

<p align="center">
  <a href="https://pypi.org/project/grit-cli/"><img src="https://img.shields.io/pypi/v/grit-cli?color=1a2f5e&label=grit-cli" alt="PyPI version" /></a>
  <img src="https://img.shields.io/badge/python-3.8%2B-1a2f5e" alt="Python 3.8+" />
  <img src="https://img.shields.io/badge/platform-macOS%20%7C%20Linux%20%7C%20Windows-1a2f5e" alt="Platform" />
  <img src="https://img.shields.io/badge/license-MIT-1a2f5e" alt="MIT License" />
</p>

---

## What is Grit?

Grit is a cross-platform background daemon that manages multiple Git identities — name, email, GPG signing key, SSH key — across all your repositories. It uses **session-based memory** to automatically apply the right profile per repository, prompting you just-in-time when a new repository is first encountered.

No more wrong-account commits. No global `git config` juggling. Grit handles it silently in the background.

---

## Features

### Free Tier (Phase 1)
- **Session memory** — remembers your active profile per repository for a configurable TTL (default 8 hours)
- **Auto-detection** — `.grit` file in repo root, path patterns (`~/work/*`), remote URL patterns, or user default
- **Git hook integration** — installs `pre-commit` hook that applies the correct identity before every commit
- **System tray** — live profile indicator with one-click profile switching
- **VS Code extension** — active profile in status bar, switch profiles from command palette
- **GPG signing** — per-profile commit signing key, configured automatically
- **SSH keys** — per-profile `core.sshCommand` configured via `ssh -i <key>`
- **HTTPS credentials** — per-profile GitHub account routing for HTTPS `git push/pull`
- **Up to 5 profiles** — no account required, fully offline

### Pro Tier (Phase 2) — Coming Soon
- **Unlimited profiles** — add as many Git identities as you need
- **Cloud sync** — sync profiles and sessions across all your machines
- **Team profiles** — organization-wide read-only profiles managed from cloud dashboard
- **Automatic sync** — changes propagate across devices in real-time (5s debounce)

### Enterprise Tier (Phase 3) — Coming Soon
- **SSO login** — OIDC and SAML 2.0 single sign-on
- **Enforce SSO** — require valid org SSO session for all commits (compliance)
- **Audit logs** — append-only SIEM-ready audit trail of all profile switches
- **Compliance reporting** — hook inventory, GPG enforcement, SSO compliance reports
- **Windows Service** — run Grit as NT Service for multi-user enterprise deployments

---

## Installation

```bash
pip install grit-cli
```

> The distribution is published as **`grit-cli`** on PyPI (the `grit` name was
> already taken), but it still installs the **`grit`** command you use everywhere
> below.

**Requirements:** Python 3.8+, Git 2.x

**Optional extras (Free tier):**

```bash
pip install "grit-cli[ui-qt]"          # PyQt6 profile picker dialog
pip install "grit-cli[linux-keyring]"  # keyring integration on Linux
pip install "grit-cli[windows]"        # pywin32 for Windows Credential Manager
```

**Pro & Enterprise (Phase 2/3 — not yet published):**

```bash
pip install "grit-cli[pro]"            # cloud sync, team profiles (coming soon)
pip install "grit-cli[enterprise]"     # SSO, audit logs, compliance (coming soon)
```

---

## Quick Start

```bash
# First-time setup (creates config, first profile, installs autostart)
grit setup

# Add more profiles
grit profile add

# Activate a profile in the current repository
grit session set Work

# See which profile is active here
grit session show

# List all profiles (active one is highlighted)
grit profile list
```

---

## How It Works

```
git commit
  └─▶ .git/hooks/pre-commit
        └─▶ grit hook pre-commit --repo <path>
              └─▶ IPC → daemon
                    └─▶ SessionEngine.resolve()
                          ├─ session cache hit → apply profile → done
                          ├─ auto-detect (.grit / path pattern / remote) → create session → apply
                          └─ no match → prompt user via popup / tray
```

Profile data is written directly to the repository's local `git config` — no wrapper scripts, no shims.

### Profile resolution order

When you commit in a repo, Grit tries profiles in this order:

1. **Active session** (if not expired and not pinned) — remembered choice from previous commits
2. **Enterprise SSO** (if `enforce_sso=True` and valid SSO session exists) — matches profile by SSO identity
3. **Auto-detection** (if `auto_detect=true`):
   - `.grit` file in repo root (`profile = Work`)
   - Path pattern match (`~/work/*` → Work profile)
   - Remote URL pattern match (`github.com/my-company/*` → Work profile)
4. **Pinned session** (if auto-detect found nothing) — permanent fallback for this repo
5. **Default profile** (if set and no pin exists) — global fallback
6. **Prompt user** — profile picker dialog; choice is remembered for the session TTL

---

## Commands

All free-tier commands work offline. Pro and Enterprise features require authentication via `grit auth login`.

### Profiles

```bash
grit profile add                  # create a profile (interactive wizard)
grit profile add -n Work -e work@company.com --gpg-key ABC123
grit profile list                 # list all profiles; active one marked
grit profile show <name>          # show full details
grit profile edit <name> --email new@email.com
grit profile delete <name>
grit profile set-default <name>   # set the default profile when auto-detection fails
grit profile unset-default        # remove default profile
```

### Sessions

```bash
grit session show                 # active profile in this repo
grit session set <profile>        # activate a profile in this repo
grit session list                 # all active sessions
grit session clear                # end the session for this repo
grit session pin <profile>        # pin a profile to this repo (survives TTL)
grit session unpin                # remove the pin from this repo
```

### HTTPS Credentials (Free tier)

Store per-profile GitHub credentials in your OS credential store:

```bash
grit credential login <profile>       # save credentials for a profile to OS store
grit credential remove <profile>      # remove saved credentials
grit credential list                  # list all saved credentials
```

When a Git profile is active, `git push/pull` over HTTPS will automatically use the stored credentials for that profile's GitHub account.

### Daemon

```bash
grit daemon start                 # start background daemon
grit daemon start --foreground    # run in foreground (development)
grit daemon stop
grit daemon status
grit daemon restart
```

### Config

Get or set app-level configuration:

```bash
grit config get <key>            # read a setting
grit config set <key> <value>    # write a setting
grit config list                  # all settings
grit config reset <key>           # restore default
```

Common settings:
- `session_ttl_hours` (default: 8) — how long sessions stay active
- `auto_detect` (default: true) — enable profile auto-detection
- `cloud_sync_enabled` (default: false) — enable Pro cloud sync

### Setup & Info

```bash
grit setup                        # first-run wizard
grit about                        # version, plan, contact
grit upgrade                      # feature comparison: Free / Pro / Enterprise
```

---

## Pro Features (Phase 2)

Pro tier adds cloud sync, team profiles, and unlimited accounts. Install with `pip install grit-cli[pro]`.

### Cloud Authentication

Device-flow OAuth2 login (no password in terminal):

```bash
grit auth login --provider github    # authenticate with GitHub
grit auth login --provider google    # authenticate with Google
grit auth status                      # show logged-in account
grit auth logout                      # sign out
```

### Cloud Sync

Upload and download profiles across machines:

```bash
grit sync push                        # upload profiles to cloud
grit sync push --sessions             # also upload active sessions
grit sync pull                        # download profiles from cloud
grit sync pull --team                 # also download org-wide team profiles
grit sync status                      # check cloud connection
```

Team profiles are read-only on local machines and managed from your cloud dashboard.

---

## Enterprise Features (Phase 3)

Enterprise tier adds SSO (OIDC/SAML), audit logs, compliance reporting, and Windows Service. Install with `pip install grit-cli[enterprise]`.

### Enterprise SSO Configuration

```bash
grit enterprise config --show                    # display current SSO config
grit enterprise config --idp-type oidc           # set to OIDC
grit enterprise config --idp-type saml           # set to SAML 2.0
grit enterprise config --idp-url https://...    # set IdP endpoint
grit enterprise config --client-id <id>         # set OIDC client ID
grit enterprise config --org-id <uuid>          # set organization UUID
grit enterprise config --enforce-sso             # require valid SSO session for all commits
grit enterprise config --no-enforce-sso         # allow commits without SSO (grace period)
grit enterprise sso-login                        # authenticate via org SSO
grit enterprise sso-status                       # check SSO session expiration
grit enterprise sso-logout                       # sign out of SSO
```

When `enforce_sso` is enabled, Grit will block commits until you authenticate with your organization's SSO provider.

### Audit Logs

View and export the append-only audit trail:

```bash
grit audit show                                  # display recent audit entries (default: last 50)
grit audit show --since 2026-01-01T00:00:00Z   # entries from specific date
grit audit show --action profile_switch         # filter by event type
grit audit show --limit 100                     # show last 100 entries
grit audit show --json                          # output as JSON array

grit audit export                               # export all entries to stdout (default: JSONL)
grit audit export --format json                # export as JSON array
grit audit export --format csv                 # export as CSV
grit audit export --format jsonl               # export as newline-delimited JSON
grit audit export --output audit.jsonl         # save to file
```

Actions logged: `profile_switch`, `session_create`, `git_config_write`.

### Compliance Reporting

Generate compliance reports for auditors and regulators:

```bash
grit compliance report                           # display report summary
grit compliance report --output report.json     # save as JSON
grit compliance report --json                   # print raw JSON
```

Reports include:
- Hook inventory (% of repos with Grit hooks installed)
- GPG enforcement status
- SSO compliance
- Audit summary (profile switches, config changes)

### Windows Service (Windows only)

Run Grit as a Windows NT Service for multi-user enterprise deployments:

```bash
grit service install                 # install GritDaemon service (requires admin)
grit service uninstall               # remove the service
grit service start                   # start the service
grit service stop                    # stop the service
grit service status                  # check if running
```

Service data is stored in `%PROGRAMDATA%\Grit` (shared across all users).

---

## Configuration

Config is stored in the platform-specific user directory:

| Platform | Path |
|---|---|
| macOS | `~/Library/Application Support/grit/` |
| Linux | `~/.config/grit/` |
| Windows | `%APPDATA%\grit\` |

Override with the `GRIT_CONFIG_DIR` environment variable (useful for testing).

**Key settings** (`grit config set <key> <value>`):

| Key | Default | Description |
|---|---|---|
| `session_ttl_hours` | `8` | How long a session stays active |
| `auto_detect` | `true` | Enable profile auto-detection |
| `cloud_sync_enabled` | `false` | Enable cloud sync (Pro) |

---

## Data Files

| File | Contents |
|---|---|
| `profiles.json` | Your Git identity profiles |
| `sessions.json` | Active sessions per repository |
| `config.json` | App configuration |
| `grit.pid` | Daemon PID |
| `grit.sock` | IPC socket (macOS / Linux) |

All writes are atomic (`.tmp` → `os.replace()`).

---

## Platform Support

| Feature | macOS | Linux | Windows |
|---|---|---|---|
| Core daemon + CLI | ✓ | ✓ | ✓ |
| System tray | ✓ | ✓ (X11) | ✓ |
| Autostart | LaunchAgent | XDG / systemd user | Registry Run key |
| IPC | Unix socket | Unix socket | TCP loopback |
| GPG signing | ✓ | ✓ | ✓ |
| SSH key routing | ✓ | ✓ | ✓ |
| Windows Credential Manager | — | — | ✓ |

---

## Development

```bash
git clone <repo>
cd grit
pip install -e ".[dev]"

# Run tests
pytest tests/unit/                        # fast unit tests
pytest tests/unit/ --cov=grit             # with coverage
pytest -m integration                     # requires real git binary
pytest -m e2e --timeout=60               # full end-to-end (CI only)

# Code quality
ruff check src/ tests/
ruff format src/ tests/
mypy src/
```

---

## Roadmap: Pro & Enterprise

Grit is in **Phase 1 (Free)** with Phase 2 (Pro) and Phase 3 (Enterprise) in active development.

**Phase 2 (Pro)** — in development
- Unlimited profiles, cloud sync, team profiles
- OAuth2-based device-flow authentication
- Bidirectional cloud sync with conflict resolution

**Phase 3 (Enterprise)** — in development
- OIDC / SAML SSO login
- Append-only audit logs with export/filtering
- Compliance reporting for regulators
- Windows NT Service for multi-user deployments
- Organization/team management dashboard

These features are implemented in the codebase but require the optional `grit-pro` and `grit-enterprise` packages, which are not yet published to PyPI. Pre-register to be notified when they launch:

**kandeepasundaram+GRIT@gmail.com**

---

## Release Notes

Full changelogs for every release are on the [GitHub Releases](https://github.com/Kandeepasundaram/Grit/releases) page.

| Version | Highlights |
|---|---|
| [0.1.0a4](https://github.com/Kandeepasundaram/Grit/releases/tag/v0.1.0a4) | Auto-tag CI step made idempotent |
| [0.1.0a3](https://github.com/Kandeepasundaram/Grit/releases/tag/v0.1.0a3) | Auto-generated release notes; fully automated release pipeline |
| [0.1.0a2](https://github.com/Kandeepasundaram/Grit/releases/tag/v0.1.0a2) | Platform-specific tray threading; headless Linux display guard |
| [0.1.0a1](https://github.com/Kandeepasundaram/Grit/releases/tag/v0.1.0a1) | Tray icon wired; pre-commit profile application fixed |
| [0.1.0a0](https://github.com/Kandeepasundaram/Grit/releases/tag/v0.1.0a0) | Initial release |

---

## License

MIT — see [LICENSE](LICENSE).

---

<p align="center">Made with grit.</p>
