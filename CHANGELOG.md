# Changelog

All notable changes to this project are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.1.0a0] - 2026-06-23

First public alpha of the open-source Grit core.

### Added
- **Background daemon** (`gritd`) with crash-safe atomic JSON storage and lazy
  session TTL purging (default 8-hour sessions).
- **CLI** (`grit`) with commands for profiles, sessions, daemon control, config,
  first-run setup, and per-profile HTTPS credential login.
- **Profile management** — name, email, GPG key, SSH key, and path/remote match
  patterns, persisted to `profiles.json`.
- **Session engine** — per-repository profile resolution with auto-detection
  (`.grit` file → path patterns → remote URL) and just-in-time prompting.
- **Git integration** — per-repo `pre-commit` hook injection, git config
  apply/backup/restore, GPG signing configuration, and `core.sshCommand` setup.
- **IPC transport** — Unix domain socket on macOS/Linux, named pipe (TCP) on
  Windows, with newline-delimited JSON messaging.
- **System tray** (pystray) with a profile picker and desktop notifications.
- **Cross-platform autostart** — XDG/systemd (Linux), LaunchAgent (macOS),
  and registry Run key (Windows).

### Notes
- Pro/Enterprise features (cloud sync, team profiles, SSO, audit, compliance)
  live in the separate optional `grit-pro` package; the core ships thin
  re-export shims that degrade gracefully when it is not installed.

[Unreleased]: https://github.com/Kandeepasundaram/Grit/compare/v0.1.0a0...HEAD
[0.1.0a0]: https://github.com/Kandeepasundaram/Grit/releases/tag/v0.1.0a0
