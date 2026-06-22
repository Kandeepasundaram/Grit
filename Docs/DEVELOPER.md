# Grit — Developer Guide

## Project Layout

```
grit/
├── src/grit/              # Python package (pip install -e ".[dev]")
│   ├── config/            # paths, app config, subscription/licensing
│   ├── models/            # pure dataclasses — Profile, Session
│   ├── storage/           # JSON file CRUD with atomic writes + file locking
│   ├── ipc/               # newline-delimited JSON over Unix socket / Named Pipe
│   ├── daemon/            # asyncio server, PID management, watchdog, recovery
│   ├── git/               # subprocess wrappers for git config, hooks, GPG, SSH
│   ├── session/           # SessionEngine (resolve/create/apply/invalidate) + detector
│   ├── cli/               # Click command groups, one file per subcommand
│   ├── ui/                # pystray tray, profile picker popup, notifications
│   ├── platform/          # per-OS autostart + Windows Service
│   ├── cloud/             # Phase 2: OAuth, REST client, sync engine, license
│   └── enterprise/        # Phase 3: SSO, audit log, compliance
├── backend/               # FastAPI + SQLAlchemy async + PostgreSQL + Redis
│   └── app/
│       ├── api/           # route handlers (auth, sync, license, enterprise, stripe)
│       ├── models/        # SQLAlchemy ORM models
│       └── services/      # business logic (license JWT signing)
├── admin-ui/              # Vite + React 18 + TypeScript admin dashboard
│   └── src/
│       ├── api/           # axios client, auth store, enterprise API wrappers
│       ├── pages/         # one file per page (Org, TeamProfiles, AuditLog, etc.)
│       └── components/    # shared UI components
├── vscode-extension/      # TypeScript VS Code extension
│   └── src/
│       ├── extension.ts   # activate/deactivate, command registration
│       ├── ipcClient.ts   # mirrors Python ipc/client.py over net.Socket
│       └── statusBar.ts   # profile name in VS Code status bar
├── tests/
│   ├── conftest.py        # tmp_config_dir + git_repo fixtures
│   ├── unit/              # fast, no git binary, no daemon
│   └── integration/       # real git binary, mocked daemon/cloud
├── Docs/                  # PRD, BRD, SETUP, this file
└── scripts/               # generate_license_keys.py
```

---

## Environment Setup

```bash
# Clone and install with all dev dependencies
git clone https://github.com/your-org/grit
cd grit
pip install -e ".[dev]"

# Verify
grit --version
gritd --help
```

For the backend:
```bash
cd backend
cp .env.example .env
python ../scripts/generate_license_keys.py   # once — writes RSA key pair
docker-compose up                            # postgres:16 + redis:7 + uvicorn
```

For the admin UI:
```bash
cd admin-ui
npm install
npm run dev   # http://localhost:3000, proxies /v1 → localhost:8000
```

---

## Running Tests

```bash
# Fast unit tests (no git, no daemon, no network)
pytest tests/unit/

# With coverage (enforced ≥ 80%)
pytest tests/unit/ --cov=grit --cov-report=term

# Integration tests (require real git binary)
pytest -m integration

# E2E tests (start/stop real daemon — CI only)
pytest -m e2e --timeout=60

# Single test
pytest tests/unit/test_profile_store.py::TestAdd::test_add_and_retrieve

# Phase-specific
pytest tests/unit/phase2/
pytest tests/unit/phase3/
```

All tests are isolated via the `tmp_config_dir` fixture:

```python
# tests/conftest.py
@pytest.fixture
def tmp_config_dir(tmp_path, monkeypatch):
    monkeypatch.setenv("GRIT_CONFIG_DIR", str(tmp_path))
    return tmp_path
```

Every module that reads or writes files resolves paths through `grit.config.paths`, which checks `GRIT_CONFIG_DIR` first — so tests get fresh isolated directories with zero filesystem mocking.

---

## Code Quality

```bash
ruff check src/ tests/     # lint (E, F, W, I, UP, B, C4, SIM)
ruff format src/ tests/    # auto-format
mypy src/                  # strict type checking (Python 3.8 target)
```

CI runs all three on every PR across Python 3.8 / 3.11 / 3.12 × ubuntu / macos / windows.

---

## Key Design Decisions

### Atomic storage writes
Every JSON file is written to a `.tmp` sibling then renamed via `os.replace()`. This guarantees readers never see a partial write, even on a power failure.

```python
# storage/profile_store.py pattern
tmp = self._path.with_suffix(".tmp")
tmp.write_text(json.dumps(data, indent=2))
os.replace(tmp, self._path)
```

### Cross-platform file locking
`storage/_lock.py` abstracts `fcntl.flock` (POSIX) and `msvcrt.locking` (Windows) behind a context manager. All mutating storage operations acquire the lock.

### IPC protocol
Messages are newline-delimited JSON with a fixed envelope:
```json
{"type": "pre-commit", "payload": {"repo_path": "/home/alice/work/project"}}
{"ok": true, "payload": {"needs_profile": false, "profile_name": "Work"}}
```
Transport: Unix domain socket on macOS/Linux; Named Pipe (`\\.\pipe\grit-daemon`) on Windows. Client is synchronous; server is asyncio.

### Adding a new IPC message type
1. Add a handler in `daemon/server.py` using the `@register("my-type")` decorator
2. Call `send_request("my-type", {...})` from the CLI or hook
3. Add a unit test with a mocked `send_request`

### Session resolution order
`SessionEngine.resolve(repo_path)` checks in this order:
1. Existing unexpired session in `sessions.json`
2. Enterprise SSO (if `enforce_sso=True` and a valid `SSOSession` exists)
3. Auto-detect: `.grit` file → `path_patterns` glob → `remote_patterns` URL match
4. Returns `None` — daemon displays the profile picker popup

### Audit log safety contract
Every call to `log_*` in `enterprise/audit.py` is wrapped in `try/except` at the call site. Audit failures **must never** propagate to the caller or block a commit.

---

## Adding a New CLI Command

1. Create `src/grit/cli/cmd_<name>.py` with a Click group or command:

```python
import click

@click.group("myfeature")
def myfeature() -> None:
    """Short description."""

@myfeature.command("do-thing")
@click.argument("target")
def do_thing(target: str) -> None:
    """Do the thing."""
    ...
```

2. Register in `src/grit/cli/main.py`:

```python
from grit.cli.cmd_myfeature import myfeature
cli.add_command(myfeature)
```

3. Write CLI tests using Click's `CliRunner`:

```python
from click.testing import CliRunner
from grit.cli.main import cli

def test_do_thing(tmp_config_dir):
    runner = CliRunner()
    result = runner.invoke(cli, ["myfeature", "do-thing", "some-target"])
    assert result.exit_code == 0
```

---

## Adding a New Backend Endpoint

1. Create or extend a router in `backend/app/api/`:

```python
from fastapi import APIRouter, Depends
from app.api.deps import get_current_user

router = APIRouter()

@router.get("/my-resource")
async def get_my_resource(user=Depends(get_current_user)):
    ...
```

2. Register in `backend/app/main.py`:

```python
from app.api import my_module
app.include_router(my_module.router, prefix="/v1/my-resource", tags=["my-resource"])
```

3. Add the corresponding API call in `admin-ui/src/api/enterprise.ts` if the admin UI needs it.

---

## Adding a New Admin UI Page

1. Create `admin-ui/src/pages/MyPage.tsx`
2. Add a route in `admin-ui/src/App.tsx`:

```tsx
import MyPage from './pages/MyPage'
// inside <Routes>:
<Route path="/my-page" element={<MyPage />} />
```

3. Add a nav link in `NavBar` inside `App.tsx`:

```tsx
<NavLink to="/my-page" className={linkCls}>My Page</NavLink>
```

---

## Adding a New Platform

1. Subclass `PlatformBase` in `src/grit/platform/myplatform.py`:

```python
from grit.platform.base import PlatformBase

class MyPlatform(PlatformBase):
    def install_autostart(self) -> None: ...
    def uninstall_autostart(self) -> None: ...
    def is_autostart_installed(self) -> bool: ...
```

2. Register in `pyproject.toml`:

```toml
[project.entry-points."grit.platforms"]
myplatform = "grit.platform.myplatform:MyPlatform"
```

---

## Data Model Reference

### Profile (`models/profile.py`)
| Field | Type | Notes |
|-------|------|-------|
| `id` | `str` | uuid4 hex, stable identifier |
| `name` | `str` | Display name, unique per store |
| `email` | `str` | Git `user.email` |
| `gpg_key_id` | `str \| None` | Short key ID; enables `commit.gpgsign=true` |
| `ssh_key_path` | `str \| None` | Path written to `core.sshCommand` |
| `path_patterns` | `List[str]` | Glob patterns matched against repo path |
| `remote_patterns` | `List[str]` | Patterns matched against `git remote get-url origin` |
| `created_at` | `str` | ISO 8601 UTC |
| `updated_at` | `str` | ISO 8601 UTC; updated by `touch()` |

### Session (`models/session.py`)
| Field | Type | Notes |
|-------|------|-------|
| `repo_path` | `str` | Canonical absolute path — the map key |
| `profile_id` | `str` | FK → `Profile.id` |
| `created_at` | `str` | ISO 8601 UTC |
| `last_used_at` | `str` | Refreshed on every `resolve()` hit |
| `expires_at` | `str` | ISO 8601 UTC; checked by `is_expired()` |
| `locked` | `bool` | If true, session is never auto-expired |

### EnterpriseConfig (`enterprise/sso.py`)
| Field | Type | Default |
|-------|------|---------|
| `idp_type` | `"none" \| "oidc" \| "saml"` | `"none"` |
| `idp_url` | `str \| None` | — |
| `client_id` | `str \| None` | — |
| `org_id` | `str \| None` | — |
| `org_name` | `str \| None` | — |
| `enforce_sso` | `bool` | `False` |
| `sso_ttl_hours` | `int` | `8` |

---

## IPC Message Reference

| Type | Direction | Payload fields | Response fields |
|------|-----------|----------------|-----------------|
| `ping` | CLI→daemon | — | `{"pong": true}` |
| `daemon-status` | CLI→daemon | — | `uptime_seconds`, `session_count`, `version` |
| `pre-commit` | hook→daemon | `repo_path` | `needs_profile`, `profile_name` |
| `get-session` | CLI→daemon | `repo_path` | `session` dict or `null` |
| `set-session` | CLI→daemon | `repo_path`, `profile_id` | `session` dict |
| `delete-session` | CLI→daemon | `repo_path` | `deleted` bool |
| `list-sessions` | CLI→daemon | — | `sessions` list |
| `list-profiles` | CLI→daemon | — | `profiles` list |
| `switch-profile` | CLI→daemon | `repo_path`, `profile_id` | `session` dict |

---

## Backend API Reference

Base URL: `http://localhost:8000` (dev) / `https://api.grit.dev` (prod)

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| `POST` | `/oauth/device/start` | — | Start device OAuth flow |
| `POST` | `/oauth/device/poll` | — | Poll for token |
| `GET` | `/v1/license` | Bearer | Get/refresh license JWT |
| `GET` | `/v1/sync/profiles` | Bearer | Pull profiles |
| `POST` | `/v1/sync/profiles` | Bearer | Push profiles |
| `GET` | `/v1/account` | Bearer | Account + subscription info |
| `POST` | `/webhooks/stripe` | Signature | Stripe event handler |
| `POST` | `/v1/enterprise/orgs` | Bearer | Create organisation |
| `GET` | `/v1/enterprise/orgs/{id}` | Bearer | Get org + SSO config |
| `PATCH` | `/v1/enterprise/orgs/{id}` | Bearer | Update org config |
| `GET` | `/v1/enterprise/orgs/{id}/members` | Bearer | List members |
| `POST` | `/v1/enterprise/orgs/{id}/members` | Bearer | Add member |
| `DELETE` | `/v1/enterprise/orgs/{id}/members/{uid}` | Bearer | Remove member |
| `GET` | `/v1/enterprise/orgs/{id}/profiles` | Bearer | List team profiles |
| `POST` | `/v1/enterprise/orgs/{id}/profiles` | Bearer | Create team profile |
| `PUT` | `/v1/enterprise/orgs/{id}/profiles/{pid}` | Bearer | Update team profile |
| `DELETE` | `/v1/enterprise/orgs/{id}/profiles/{pid}` | Bearer | Delete team profile |
| `GET` | `/v1/enterprise/orgs/{id}/audit` | Bearer | Query audit log |
| `POST` | `/v1/enterprise/audit` | Bearer | Ingest client audit events |
| `GET` | `/v1/enterprise/sso/{id}/config` | — | Get SSO config (public, for client onboarding) |

Full interactive docs at `http://localhost:8000/docs` when the backend is running.

---

## Testing Patterns

### Storage test (no mocking needed)
```python
def test_add_profile(tmp_config_dir):
    store = ProfileStore()
    p = store.add(Profile(name="Work", email="work@co.com"))
    assert store.get_by_id(p.id).email == "work@co.com"
```

### Git integration test
```python
@pytest.mark.integration
def test_hook_installed(git_repo):
    install(str(git_repo))
    assert is_installed(str(git_repo))
    hook = (git_repo / ".git" / "hooks" / "pre-commit").read_text()
    assert "GRIT_HOOK_v1" in hook
```

### CLI test
```python
from click.testing import CliRunner
from grit.cli.main import cli

def test_profile_list(tmp_config_dir):
    runner = CliRunner()
    result = runner.invoke(cli, ["profile", "list", "--json"])
    assert result.exit_code == 0
    assert json.loads(result.output) == []
```

### Time-dependent (TTL)
```python
from freezegun import freeze_time

def test_session_expires(tmp_config_dir):
    session = Session(repo_path="/r", profile_id="p1")
    with freeze_time(datetime.now(timezone.utc) + timedelta(hours=9)):
        assert session.is_expired()
```

### Mocking the daemon (CLI commands that use IPC)
```python
def test_session_set(tmp_config_dir, mocker):
    mocker.patch("grit.ipc.client.send_request", return_value={"ok": True, "payload": {...}})
    runner = CliRunner()
    result = runner.invoke(cli, ["session", "set", "Work"])
    assert result.exit_code == 0
```

---

## Performance Targets

| Metric | Target | How to measure |
|--------|--------|----------------|
| IPC round-trip (`pre-commit`) | < 50 ms | `time grit hook pre-commit --repo .` |
| `session_store.get()` | < 5 ms | `pytest-benchmark` |
| Daemon idle RAM | < 50 MB | `tracemalloc` in daemon startup |
| Profile picker popup | < 200 ms to appear | Manual / E2E test |

Benchmarks run on a weekly CI schedule. A ≥20% regression in any metric raises an alert.

---

## Release Process

1. Bump version in `pyproject.toml` (`version = "x.y.z"`)
2. Update `CHANGELOG.md`
3. Push and tag: `git tag vx.y.z && git push --tags`
4. CI publishes to PyPI automatically on `v*` tags via `hatch build && twine upload`
5. Update Homebrew tap formula (`homebrew-grit` repo)
6. Submit winget manifest update to `winget-pkgs`

For the backend, bump the image tag in `docker-compose.yml` and redeploy.

---

## Generating License Keys

Run once before first backend deploy:

```bash
python scripts/generate_license_keys.py
# Writes:
#   backend/license_private.pem  (keep secret — signs JWTs)
#   src/grit/cloud/license_public.pem  (bundled in client — verifies JWTs)
```

The client falls back to trusting stored JWT claims (without cryptographic verification) if the public key file contains the `PLACEHOLDER` marker — used in development without a real key pair.
