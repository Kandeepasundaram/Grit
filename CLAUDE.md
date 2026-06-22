# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What This Project Is

**Grit** is a cross-platform background daemon with system tray integration that manages multiple Git identities (name, email, GPG key, SSH key) across repositories. It uses session-based profile memory (default 8-hour TTL) to automatically apply the right profile per repository, prompting the user just-in-time when a new repository is encountered.

## Development Commands

```bash
pip install -e ".[dev]"       # install in editable mode with dev dependencies

# Run tests
pytest tests/unit/            # unit tests (fast, no git or daemon required)
pytest tests/unit/ --cov=grit --cov-report=term  # with coverage
pytest -m integration         # integration tests (requires real git binary)
pytest -m e2e --timeout=60    # end-to-end tests (CI only — start/stop daemon)
pytest tests/unit/test_profile_store.py::TestAdd::test_add_and_retrieve  # single test

# Code quality
ruff check src/ tests/        # lint
ruff format src/ tests/       # format
mypy src/                     # type check

# Run the daemon in foreground (for development)
python -m grit.daemon.server --verbose
# Or via CLI:
grit daemon start --foreground --verbose
```

## Architecture

### Key design decisions
- **`GRIT_CONFIG_DIR` env var**: overrides all config/data paths. Tests set this to `tmp_path` via the `tmp_config_dir` fixture in `tests/conftest.py` — no mocking of filesystem I/O needed.
- **Atomic writes**: all JSON storage writes go to `.tmp` then `os.replace()` — crash-safe.
- **IPC transport**: Unix domain socket (`~/.local/share/grit/grit.sock`) on macOS/Linux; Named Pipe on Windows (Phase 1C).
- **Git interception**: per-repo git hooks (not OS syscall trapping). `git/hook.py` injects a `pre-commit` hook that calls `grit hook pre-commit --repo <path>` → IPC → daemon.
- **Session TTL**: default 8 hours, configurable. Expired sessions purged lazily on every read.

### Module map

```
src/grit/
├── config/
│   ├── paths.py          # all path resolution; reads GRIT_CONFIG_DIR env var
│   └── app_config.py     # AppConfig dataclass, persisted to config.json
├── models/
│   ├── profile.py        # Profile dataclass (id, name, email, gpg_key_id, ssh_key_path, patterns)
│   └── session.py        # Session dataclass (repo_path, profile_id, expires_at, locked)
├── storage/
│   ├── _lock.py          # cross-platform file locking (fcntl / msvcrt)
│   ├── profile_store.py  # CRUD on profiles.json
│   └── session_store.py  # CRUD on sessions.json; lazy TTL purge on every read
├── ipc/
│   ├── protocol.py       # encode/decode newline-delimited JSON messages
│   ├── client.py         # synchronous client (used by CLI + hooks)
│   └── server.py         # asyncio server (runs inside daemon)
├── daemon/
│   ├── server.py         # gritd entry point; registers IPC handlers; wires asyncio loop
│   ├── pid.py            # PID file read/write/check via psutil
│   ├── watchdog.py       # filesystem observer for .git/COMMIT_EDITMSG
│   ├── hook_manager.py   # watched_repos.json registry + hook install
│   └── recovery.py       # stale PID/socket detection and cleanup
├── git/
│   ├── repo.py           # find_repo_root(), get_remote_url()
│   ├── config.py         # read/write/unset git config; apply_profile()
│   ├── hook.py           # install/uninstall pre-commit hook; sentinel: GRIT_HOOK_v1
│   ├── gpg.py            # list GPG keys; configure_signing()
│   └── ssh.py            # write core.sshCommand to git config
├── session/
│   ├── engine.py         # SessionEngine: resolve → create → apply → invalidate
│   └── detector.py       # auto-detect profile: .grit file > path patterns > remote URL
├── cli/
│   ├── main.py           # root `grit` Click group
│   ├── cmd_profile.py    # grit profile add/list/show/edit/delete
│   ├── cmd_session.py    # grit session show/set/clear/list
│   ├── cmd_daemon.py     # grit daemon start/stop/status/restart
│   ├── cmd_config.py     # grit config get/set/list/reset
│   ├── cmd_hook.py       # grit hook pre-commit (internal, called by git hook)
│   ├── cmd_setup.py      # grit setup (first-run onboarding wizard)
│   ├── cmd_auth.py       # grit auth login/logout/status (Phase 2 cloud auth)
│   ├── cmd_sync.py       # grit sync push/pull/status (Phase 2 cloud sync)
│   ├── cmd_enterprise.py # grit enterprise config/sso-login/sso-status/sso-logout (Phase 3)
│   ├── cmd_audit.py      # grit audit show/export/clear (Phase 3)
│   ├── cmd_compliance.py # grit compliance report/hooks/gpg (Phase 3)
│   └── cmd_service.py    # grit service install/uninstall/start/stop/status (Phase 3, Windows)
├── ui/
│   ├── tray.py           # pystray system tray icon + menu
│   ├── popup.py          # profile picker dialog (PyQt6 → tkinter fallback)
│   └── notifications.py  # plyer desktop notifications
├── platform/
│   ├── base.py              # PlatformBase ABC + get_platform() factory
│   ├── linux.py             # XDG autostart + systemd user unit
│   ├── macos.py             # LaunchAgent plist
│   ├── windows.py           # HKCU registry Run key
│   └── windows_service.py   # Phase 3: pywin32 NT Service for enterprise multi-user; data in %PROGRAMDATA%\Grit
├── cloud/                          # Phase 2: Freemium
│   ├── auth.py           # device-flow OAuth2 (GitHub/Google); token storage in tokens.json
│   ├── client.py         # REST client for api.grit.dev; raises OfflineError gracefully
│   ├── sync.py           # SyncEngine: push/pull profiles+sessions; last-write-wins merge; 5s debounce auto-sync
│   └── license_public.pem  # RSA public key for JWT verification (generated via scripts/generate_license_keys.py)
└── enterprise/
    ├── audit.py          # append-only JSON-lines audit log; log_profile_switch/session_create/git_config_write
    ├── sso.py            # EnterpriseConfig + SSOSession dataclasses; OIDC device flow; SAML 2.0 response parsing
    └── compliance.py     # check_hook_inventory / check_gpg_enforcement / generate_report → JSON compliance report
```

### Data flows

**Commit hook flow** (primary path):
```
git commit → .git/hooks/pre-commit →
  grit hook pre-commit --repo <path> →
    IPC: {"type": "pre-commit", "payload": {"repo_path": "..."}} →
      daemon: SessionEngine.resolve() → apply profile to git config → {"needs_profile": false}
```

**Detection priority** (in `session/detector.py`):
1. `.grit` file in repo root (`profile = "Work"`)
2. `path_patterns` glob match (e.g. `~/work/*`)
3. `remote_patterns` match on `git remote get-url origin`
4. → `None` (prompt user)

### Phase 2 module responsibilities
- **`config/subscription.py`**: `load_license()` reads `license.json` (JWT verified with bundled RSA public key). Falls back to free tier if absent. `enforce_profile_limit(current_count)` raises `ValueError` — called by `ProfileStore.add()`. `require_pro(feature_name)` gates cloud sync / team profiles / SSO.
- **`cloud/auth.py`**: `start_device_flow(provider)` + `poll_device_flow(...)` — tokens stored in `tokens.json` (chmod 600 on POSIX). `get_access_token()` refreshes transparently.
- **`cloud/client.py`**: All methods raise `OfflineError` (not a crash) when unreachable — callers continue local operation. Reads `GRIT_API_URL` env var for on-premise overrides.
- **`cloud/sync.py`**: `SyncEngine.sync()` does full bidirectional merge. Team profiles stored read-only in `team_profiles.json`. `schedule_sync()` debounces 5s before triggering background upload.
- **`backend/`**: FastAPI + PostgreSQL + Redis + Stripe. Run with `docker-compose up` in `backend/`. Generate license keys first with `python scripts/generate_license_keys.py`.

### Phase 3 module responsibilities
- **`enterprise/sso.py`**: `EnterpriseConfig` (idp_type/idp_url/client_id/org_id/enforce_sso) persisted to `enterprise.json`. `SSOSession` with `is_expired()`. OIDC: `start_oidc_login()` + `poll_oidc_token()` (device flow via `_oidc_discover()` metadata endpoint). SAML: `get_saml_login_url()` + `process_saml_response()` (requires `python3-saml`). `resolve_profile_for_sso(session, profiles)` matches profiles by SSO identity.
- **`enterprise/audit.py`**: `_append()` writes JSON lines to `audit.log` atomically (open mode `"a"`). `export_entries(since=)` reads and filters. Wired into `SessionEngine.create()` (session_create), `SessionEngine.apply()` (profile_switch), and `git.config.apply_profile()` (git_config_write). All calls wrapped in try/except — audit failures never break the commit flow.
- **`enterprise/compliance.py`**: `generate_report()` calls `check_hook_inventory()`, `check_gpg_enforcement()`, `check_sso_compliance()`, `audit_summary()`. Returns `{"compliant": bool, "sections": {...}}`. `write_report(path)` serialises to JSON file.
- **`platform/windows_service.py`**: `_build_service_class()` factory (deferred import so pywin32 is optional). `install_service()`, `uninstall_service()`, `start_service()`, `stop_service()`, `query_service_status()`. Service sets `GRIT_CONFIG_DIR=%PROGRAMDATA%\Grit` before starting the asyncio daemon.
- **`backend/app/models/user.py`**: Added `Organization`, `OrgMember`, `AuditEvent` SQLAlchemy models.
- **`backend/app/api/enterprise.py`**: org CRUD (`/v1/enterprise/orgs/*`), member management, team profile CRUD, audit log query/ingest (`/v1/enterprise/audit`), SSO config endpoint (`/v1/enterprise/sso/{org_id}/config`). All org endpoints check `_require_org_role()` (member/admin/owner hierarchy).
- **`admin-ui/`**: Vite + React 18 + TypeScript + TanStack Query. Auth via device flow stored in localStorage. Pages: `OrgPage` (SSO config + member management), `TeamProfilesPage` (team profile CRUD), `AuditLogPage` (filterable table + CSV export), `SubscriptionPage`. Dev proxy at `/v1` → `localhost:8000`. Build: `cd admin-ui && npm run build`.

### Session resolution order (updated for Phase 3)
When `SessionEngine.resolve(repo_path)` is called:
1. Session cache hit (not expired) → return immediately
2. Enterprise SSO: if `enforce_sso=True` and valid SSO session exists → match profile via `resolve_profile_for_sso()` → create session
3. Auto-detect if `app_config.auto_detect=True`: `.grit` file > `path_patterns` > `remote_patterns`
4. Return `None` → daemon prompts user via popup

### IPC message types
`ping`, `pre-commit`, `get-session`, `set-session`, `delete-session`, `list-sessions`, `list-profiles`, `switch-profile`, `daemon-status`

### Testing patterns
- **Unit tests**: set `GRIT_CONFIG_DIR=tmp_path` via `tmp_config_dir` fixture — no mocking of file I/O
- **Git tests**: use `git_repo` fixture which runs `git init` in `tmp_path`
- **CLI tests**: use Click's `CliRunner` + `--config-dir` option; mock `grit.ipc.client.send_request` for daemon-dependent commands
- **Daemon tests**: start daemon as subprocess with `GRIT_CONFIG_DIR` set; wait for `ping()`
- **Time-dependent (TTL)**: use `freezegun` or monkeypatch `datetime.now`
- Marks: `@pytest.mark.integration` (needs git), `@pytest.mark.e2e` (needs daemon), `@pytest.mark.slow`

## Business Phases

- **Phase 1 (complete):** Open source, free — daemon + CLI + tray + VS Code extension (Months 1–12)
- **Phase 2 (complete):** Freemium — Pro tier ($5/mo), cloud sync, team profiles. `src/grit/cloud/` + `backend/` (Months 13–24)
- **Phase 3 (complete):** Enterprise — SSO (OIDC/SAML), audit logs, compliance reporting, Windows Service, backend enterprise org API, React admin UI. `src/grit/enterprise/`, `admin-ui/` (Months 25–36)

## Backend Development (Phase 2+3)

```bash
cd backend
cp .env.example .env        # fill in credentials
python ../scripts/generate_license_keys.py  # generate RSA key pair (once)
docker-compose up           # start postgres + redis + api

# Without Docker:
pip install -e ".[dev]"
uvicorn app.main:app --reload
```

API docs available at `http://localhost:8000/docs` when running.

## Admin UI Development (Phase 3)

```bash
cd admin-ui
npm install
npm run dev          # dev server at http://localhost:3000 (proxies /v1 → :8000)
npm run build        # production build to admin-ui/dist/
npm run type-check   # TypeScript validation
```

Set `grit_org_id` in browser localStorage to the organisation UUID to use the admin UI.

## Docs

- `Docs/PRD.md` — all functional/non-functional requirements, user stories, UI spec, data flows
- `Docs/BRD.md` — market analysis, business model, phase timelines, revenue targets
