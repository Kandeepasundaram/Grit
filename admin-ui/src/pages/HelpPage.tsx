import { useState } from 'react'

// ── Shared helpers ────────────────────────────────────────────────────────────

function Pre({ children }: { children: string }) {
  return (
    <pre style={{
      background: '#f6f8fa', border: '1px solid #e1e4e8',
      borderRadius: 4, padding: '10px 14px',
      fontSize: 13, overflowX: 'auto', margin: '8px 0',
    }}>
      {children}
    </pre>
  )
}

function Th({ children }: { children: React.ReactNode }) {
  return <th style={{ textAlign: 'left', padding: '6px 10px', borderBottom: '1px solid #ddd', background: '#f5f5f5' }}>{children}</th>
}

function Td({ children }: { children: React.ReactNode }) {
  return <td style={{ padding: '6px 10px', borderBottom: '1px solid #eee' }}>{children}</td>
}

// ── Standard edition sections ─────────────────────────────────────────────────

const standardSections = [
  {
    id: 'profiles',
    title: 'Profiles',
    content: (
      <>
        <p>
          A profile is a named Git identity (name, email, optional GPG key and SSH key). The
          free tier supports up to <strong>5 profiles</strong>.
        </p>
        <Pre>{`grit profile add --name "Work" --email "you@company.com"
grit profile add --name "Personal" --email "you@gmail.com"
grit profile list
grit profile edit Work --email "new@company.com"
grit profile delete Personal`}</Pre>
        <h4>GPG commit signing</h4>
        <Pre>{`grit profile edit Work --gpg-key-id ABC12345`}</Pre>
        <h4>Dedicated SSH key</h4>
        <Pre>{`grit profile edit Work --ssh-key "~/.ssh/id_work"`}</Pre>
      </>
    ),
  },
  {
    id: 'auto-detect',
    title: 'Auto-Detection',
    content: (
      <>
        <p>Grit picks the right profile automatically using these rules, checked in order:</p>
        <ol>
          <li>
            <strong>.grit file</strong> in the repo root — highest priority
            <Pre>{`# .grit
profile = Work`}</Pre>
          </li>
          <li>
            <strong>Path pattern</strong> — glob matched against the repo's absolute path
            <Pre>{`grit profile edit Work --path-pattern "~/work/*"`}</Pre>
          </li>
          <li>
            <strong>Remote URL pattern</strong> — matched against <code>git remote get-url origin</code>
            <Pre>{`grit profile edit Work --remote-pattern "github.com/my-company/*"`}</Pre>
          </li>
          <li>→ <strong>Profile picker dialog</strong> — your choice is remembered for 8 hours</li>
        </ol>
      </>
    ),
  },
  {
    id: 'sessions',
    title: 'Sessions',
    content: (
      <>
        <p>
          A session ties a profile to a repo for a configurable TTL (default <strong>8 hours</strong>).
          After expiry, Grit re-prompts on the next commit.
        </p>
        <Pre>{`grit session show          # active session for current repo
grit session set Work      # manually set profile for this repo
grit session clear         # force re-prompt on next commit
grit session list          # all active sessions`}</Pre>
        <h4>Extending TTL</h4>
        <Pre>{`grit config set session_ttl_hours 24
grit session set Work --lock   # never auto-expire this session`}</Pre>
      </>
    ),
  },
  {
    id: 'daemon',
    title: 'Daemon',
    content: (
      <>
        <p>
          The daemon is a lightweight background process that handles all profile resolution and
          IPC. It starts automatically on login after <code>grit setup</code>.
        </p>
        <Pre>{`grit daemon start                    # background
grit daemon start --foreground --verbose   # debug mode
grit daemon status
grit daemon stop
grit daemon restart`}</Pre>
        <h4>Git hook</h4>
        <p>
          The daemon installs a <code>pre-commit</code> hook in every repo it detects. Verify
          with:
        </p>
        <Pre>{`cat .git/hooks/pre-commit
# Should contain: grit hook pre-commit`}</Pre>
      </>
    ),
  },
  {
    id: 'config',
    title: 'Configuration',
    content: (
      <>
        <Pre>{`grit config list                            # view all settings
grit config set session_ttl_hours 12        # session TTL (default: 8)
grit config set auto_detect false           # always prompt instead
grit config set notifications_enabled true  # desktop notifications
grit config set default_profile_id <id>    # fallback profile
grit config reset session_ttl_hours        # restore default`}</Pre>
      </>
    ),
  },
  {
    id: 'tray-vscode',
    title: 'Tray & VS Code',
    content: (
      <>
        <h4>System tray</h4>
        <p>
          After the daemon starts, a tray icon appears showing the active profile. The icon
          colour is stable per profile. Click to switch profiles or clear the session.
        </p>
        <h4>VS Code extension</h4>
        <p>Install <strong>Grit</strong> from the Marketplace. It adds:</p>
        <ul>
          <li>Status bar item — active profile for the current workspace</li>
          <li><kbd>Ctrl+Shift+P</kbd> → <em>Grit: Switch Profile</em></li>
          <li><em>Grit: Show Session</em> and <em>Grit: Invalidate Session</em></li>
        </ul>
        <p>No extra configuration needed — the extension connects to the running daemon automatically.</p>
      </>
    ),
  },
  {
    id: 'std-troubleshooting',
    title: 'Troubleshooting',
    content: (
      <>
        <h4>Profile not applied after commit</h4>
        <Pre>{`grit daemon status
grit session show
grit session set Work
git config --local user.email`}</Pre>

        <h4>Profile picker doesn't appear</h4>
        <p>Requires a display server (X11/Wayland/Windows/macOS desktop). On headless servers:</p>
        <Pre>{`grit session set Work`}</Pre>

        <h4>Hook not installed</h4>
        <Pre>{`cat .git/hooks/pre-commit   # should contain GRIT_HOOK_v1
grit daemon restart          # triggers re-scan`}</Pre>

        <h4>Profile limit reached (free tier)</h4>
        <p>Delete an unused profile, or <a href="https://grit.dev/pricing" target="_blank" rel="noreferrer">upgrade to Pro</a>.</p>

        <h4>Data locations</h4>
        <table style={{ borderCollapse: 'collapse', width: '100%' }}>
          <thead><tr><Th>Platform</Th><Th>Path</Th></tr></thead>
          <tbody>
            <tr><Td>Linux</Td><Td><code>~/.config/grit/</code></Td></tr>
            <tr><Td>macOS</Td><Td><code>~/Library/Application Support/grit/</code></Td></tr>
            <tr><Td>Windows</Td><Td><code>%APPDATA%\grit\</code></Td></tr>
            <tr><Td>Override</Td><Td>Set <code>GRIT_CONFIG_DIR</code></Td></tr>
          </tbody>
        </table>
      </>
    ),
  },
]

// ── Enterprise edition sections ───────────────────────────────────────────────

const enterpriseSections = [
  {
    id: 'getting-started',
    title: 'Getting Started',
    content: (
      <>
        <p>Install Grit and run the onboarding wizard to get set up in under a minute.</p>
        <Pre>{`pip install grit
grit setup`}</Pre>
        <p>
          <code>grit setup</code> creates your config directory, walks you through creating your
          first profile, and installs the daemon autostart entry for your platform.
        </p>
      </>
    ),
  },
  {
    id: 'organisation',
    title: 'Organisation & SSO',
    content: (
      <>
        <p>
          The <strong>Organisation</strong> page lets you configure enterprise SSO and manage
          members. Changes here are pushed to all Grit clients joined to your org.
        </p>
        <h4>SSO types</h4>
        <ul>
          <li><strong>OIDC</strong> — OpenID Connect device flow (Google Workspace, Okta, Azure AD, etc.)</li>
          <li><strong>SAML</strong> — SAML 2.0 (Okta, OneLogin, ADFS, etc.)</li>
        </ul>
        <h4>Enforce SSO</h4>
        <p>
          When enabled, Grit automatically resolves the profile matching the signed-in SSO user
          on every commit. Commits from users without an active SSO session can be blocked at
          the hook level.
        </p>
        <h4>Client setup (run once per machine)</h4>
        <Pre>{`grit enterprise config \\
  --idp-type oidc \\
  --idp-url https://accounts.your-company.com \\
  --client-id grit-client-id \\
  --org-id <org-id> \\
  --enforce-sso

grit enterprise sso-login`}</Pre>
      </>
    ),
  },
  {
    id: 'team-profiles',
    title: 'Team Profiles',
    content: (
      <>
        <p>
          Team profiles are organisation-managed identities pushed to all members as read-only
          profiles. Use them for shared service accounts, bots, or role-based identities.
        </p>
        <h4>Path & remote patterns</h4>
        <p>Patterns let Grit auto-apply the team profile in matching repos:</p>
        <ul>
          <li><strong>Path pattern</strong> — e.g. <code>~/work/infra/*</code></li>
          <li><strong>Remote pattern</strong> — e.g. <code>github.com/my-company/*</code></li>
        </ul>
      </>
    ),
  },
  {
    id: 'audit-log',
    title: 'Audit Log',
    content: (
      <>
        <p>
          Every profile switch, session creation, and git config write is recorded in an
          append-only log suitable for SIEM forwarding.
        </p>
        <h4>Event types</h4>
        <table style={{ borderCollapse: 'collapse', width: '100%' }}>
          <thead><tr><Th>Action</Th><Th>When</Th></tr></thead>
          <tbody>
            <tr><Td><code>session_create</code></Td><Td>A new per-repo session is started</Td></tr>
            <tr><Td><code>profile_switch</code></Td><Td>A profile is applied to git config</Td></tr>
            <tr><Td><code>git_config_write</code></Td><Td>A specific git config key is written</Td></tr>
          </tbody>
        </table>
        <h4>CLI access</h4>
        <Pre>{`grit audit show --action profile_switch --since 2025-01-01T00:00:00Z
grit audit export --format csv --output audit.csv`}</Pre>
      </>
    ),
  },
  {
    id: 'compliance',
    title: 'Compliance',
    content: (
      <>
        <p>Generate a JSON report verifying hook installation, GPG coverage, and SSO status.</p>
        <Pre>{`grit compliance report --output report.json
grit compliance hooks   # hook inventory only
grit compliance gpg     # GPG signing coverage only`}</Pre>
        <p>Report passes (<code>"compliant": true</code>) only when:</p>
        <ul>
          <li>All watched repos have the hook installed</li>
          <li>No profiles are missing a GPG key</li>
          <li>If SSO is enforced, an active SSO session exists</li>
        </ul>
      </>
    ),
  },
  {
    id: 'subscription',
    title: 'Subscription & Licensing',
    content: (
      <>
        <table style={{ borderCollapse: 'collapse', width: '100%' }}>
          <thead>
            <tr><Th>Tier</Th><Th>Profiles</Th><Th>Cloud sync</Th><Th>Team profiles</Th><Th>SSO / Audit</Th></tr>
          </thead>
          <tbody>
            <tr><Td>Free</Td><Td>Up to 5</Td><Td>—</Td><Td>—</Td><Td>—</Td></tr>
            <tr><Td>Pro ($5/mo)</Td><Td>Unlimited</Td><Td>✓</Td><Td>✓</Td><Td>—</Td></tr>
            <tr><Td>Enterprise</Td><Td>Unlimited</Td><Td>✓</Td><Td>✓</Td><Td>✓</Td></tr>
          </tbody>
        </table>
        <p style={{ marginTop: 12 }}>
          Licenses are RSA-signed JWTs verified locally — no internet required. A 30-day grace
          period applies if the license server is unreachable.
        </p>
        <Pre>{`grit auth login    # link your Grit account
grit auth status   # check current tier`}</Pre>
      </>
    ),
  },
  {
    id: 'windows-service',
    title: 'Windows Service',
    content: (
      <>
        <p>
          For enterprise multi-user Windows deployments, run the Grit daemon as a Windows NT
          Service. Data is stored in <code>%PROGRAMDATA%\Grit</code>, shared across all users.
        </p>
        <Pre>{`# Run as Administrator
grit service install
grit service start
grit service status
grit service stop
grit service uninstall`}</Pre>
        <p>Requires: <code>pip install pywin32</code></p>
      </>
    ),
  },
  {
    id: 'ent-troubleshooting',
    title: 'Troubleshooting',
    content: (
      <>
        <h4>Daemon not running</h4>
        <Pre>{`grit daemon status
grit daemon start`}</Pre>
        <h4>Hook not firing</h4>
        <Pre>{`cat .git/hooks/pre-commit   # should contain GRIT_HOOK_v1`}</Pre>
        <h4>Profile not applied</h4>
        <Pre>{`grit session show
grit session set "Work"
git config --local user.email`}</Pre>
        <h4>SSO login fails</h4>
        <ul>
          <li>Verify <code>--idp-url</code> is reachable from this machine</li>
          <li>OIDC: confirm device flow is enabled on your IdP</li>
          <li>SAML: verify SP metadata is registered</li>
        </ul>
        <h4>Full reset</h4>
        <Pre>{`grit daemon stop
# macOS/Linux
rm -rf ~/.config/grit ~/.local/share/grit
# Windows
rmdir /s /q "%APPDATA%\\grit"
grit setup`}</Pre>
      </>
    ),
  },
]

// ── Layout ────────────────────────────────────────────────────────────────────

type Edition = 'standard' | 'enterprise'

function HelpLayout({ sections }: { sections: typeof standardSections }) {
  const [active, setActive] = useState(sections[0].id)
  const current = sections.find(s => s.id === active) ?? sections[0]

  return (
    <div style={{ display: 'flex', height: '100%' }}>
      <nav style={{ width: 200, flexShrink: 0, borderRight: '1px solid #e1e4e8', paddingTop: 8 }}>
        {sections.map(s => (
          <button
            key={s.id}
            onClick={() => setActive(s.id)}
            style={{
              display: 'block', width: '100%', textAlign: 'left',
              padding: '8px 16px', border: 'none', cursor: 'pointer',
              background: active === s.id ? '#f0f4ff' : 'transparent',
              fontWeight: active === s.id ? 600 : 400,
              color: active === s.id ? '#1a56db' : '#333',
              borderLeft: active === s.id ? '3px solid #1a56db' : '3px solid transparent',
              fontSize: 14,
            }}
          >
            {s.title}
          </button>
        ))}
      </nav>
      <article style={{ flex: 1, padding: '24px 32px', overflowY: 'auto', maxWidth: 720 }}>
        <h2 style={{ marginTop: 0 }}>{current.title}</h2>
        <div style={{ lineHeight: 1.6, fontSize: 14 }}>{current.content}</div>
      </article>
    </div>
  )
}

// ── Page ─────────────────────────────────────────────────────────────────────

export default function HelpPage() {
  const [edition, setEdition] = useState<Edition>('enterprise')

  const tabStyle = (active: boolean): React.CSSProperties => ({
    padding: '8px 20px',
    border: 'none',
    borderBottom: active ? '2px solid #1a56db' : '2px solid transparent',
    background: 'none',
    cursor: 'pointer',
    fontWeight: active ? 600 : 400,
    color: active ? '#1a56db' : '#555',
    fontSize: 14,
  })

  return (
    <div style={{ display: 'flex', flexDirection: 'column', height: '100%' }}>
      {/* Edition tabs */}
      <div style={{ borderBottom: '1px solid #e1e4e8', paddingLeft: 16, flexShrink: 0 }}>
        <button style={tabStyle(edition === 'standard')} onClick={() => setEdition('standard')}>
          Standard Edition
        </button>
        <button style={tabStyle(edition === 'enterprise')} onClick={() => setEdition('enterprise')}>
          Enterprise Edition
        </button>
      </div>

      {/* Content */}
      <div style={{ flex: 1, overflow: 'hidden' }}>
        {edition === 'standard'
          ? <HelpLayout sections={standardSections} />
          : <HelpLayout sections={enterpriseSections} />
        }
      </div>
    </div>
  )
}
