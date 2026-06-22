<p align="center">
  <img src="assets/grit_logo_hi_res.png" alt="Grit — Git Profile Manager" width="320" />
</p>

<h1 align="center">Grit</h1>

<p align="center">
  <strong>Session-based Git profile manager — right identity, every commit.</strong>
</p>

<p align="center">
  <a href="https://pypi.org/project/grit/"><img src="https://img.shields.io/pypi/v/grit?color=1a2f5e&label=grit" alt="PyPI version" /></a>
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

- **Session memory** — remembers your active profile per repository for a configurable TTL (default 8 hours)
- **Auto-detection** — `.grit` file in the repo root, path glob patterns (`~/work/*`), or remote URL patterns select the right profile automatically
- **Git hook integration** — installs a `pre-commit` hook that applies the correct identity before every commit
- **System tray** — live profile indicator with one-click profile switching
- **VS Code extension** — active profile in the status bar, switch profiles from the command palette
- **GPG signing** — per-profile commit signing key, configured automatically
- **SSH keys** — per-profile `core.sshCommand` configured via `ssh -i <key>`
- **HTTP credentials** — per-profile GitHub username routing for HTTPS remotes
- **Up to 5 profiles** — free tier, no account required, fully offline

---

## Installation

```bash
pip install grit
```

**Requirements:** Python 3.8+, Git 2.x

**Optional extras:**

```bash
pip install "grit[ui-qt]"       # PyQt6 profile picker dialog
pip install "grit[linux-keyring]"  # keyring integration on Linux
pip install "grit[windows]"     # pywin32 for Windows Credential Manager
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

### Auto-detection priority

1. `.grit` file in the repo root (`profile = Work`)
2. Path pattern match (`~/work/*` → Work profile)
3. Remote URL pattern match (`github.com/my-company/*` → Work profile)
4. Prompt — one-time selection, then remembered for the session TTL

---

## Commands

### Profiles

```bash
grit profile add                  # create a profile (interactive wizard)
grit profile add -n Work -e work@company.com --gpg-key ABC123
grit profile list                 # list all profiles; active one marked
grit profile show <name>          # show full details
grit profile edit <name> --email new@email.com
grit profile delete <name>
```

### Sessions

```bash
grit session show                 # active profile in this repo
grit session set <profile>        # activate a profile in this repo
grit session list                 # all active sessions
grit session clear                # end the session for this repo
```

### Daemon

```bash
grit daemon start                 # start background daemon
grit daemon start --foreground    # run in foreground (development)
grit daemon stop
grit daemon status
grit daemon restart
```

### Setup & Info

```bash
grit setup                        # first-run wizard
grit about                        # version, plan, contact
grit upgrade                      # feature comparison: Free / Pro / Enterprise
```

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

## Grit Pro — Coming Soon

Grit Pro adds:

- **Unlimited profiles** (free tier: 5)
- **Cloud sync** — profiles and sessions across all your machines
- **Team profiles** — org-wide read-only profiles pushed from your admin dashboard
- **Enterprise SSO** — OIDC and SAML 2.0 login
- **Audit logs** — SIEM-ready append-only log of every profile switch
- **Compliance reporting** — hook inventory, GPG enforcement, SSO compliance

Grit Pro is not yet available. Pre-register to be notified at launch:

**kandeepasundaram+GRIT@gmail.com**

---

## License

MIT — see [LICENSE](LICENSE).

---

<p align="center">Made with grit.</p>
