import { useState } from 'react'
import { useAuthStore } from '../api/auth'
import axios from 'axios'

// In development (no backend), set VITE_DEV_TOKEN in .env.local to bypass OAuth.
// Example: VITE_DEV_TOKEN=dev-token-local
const DEV_TOKEN = import.meta.env.VITE_DEV_TOKEN as string | undefined

export default function LoginPage() {
  const setToken = useAuthStore(s => s.setToken)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  async function handleGitHub() {
    setLoading(true)
    setError(null)
    try {
      const { data: flow } = await axios.post('/oauth/device/start', { provider: 'github' })
      window.open(flow.verification_uri, '_blank')
      alert(`Enter code ${flow.user_code} at the page that just opened, then click OK.`)

      const { data: result } = await axios.post('/oauth/device/poll', {
        device_code: flow.device_code,
        provider: 'github',
      })
      setToken(result.access_token)
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Login failed — is the backend running?')
    } finally {
      setLoading(false)
    }
  }

  function handleDevLogin() {
    // Paste any bearer token directly — useful when running the backend locally
    const token = window.prompt('Paste your bearer token (from /oauth/github/token or a dev JWT):')
    if (token?.trim()) setToken(token.trim())
  }

  const isDev = import.meta.env.DEV

  return (
    <div style={{ maxWidth: 380, margin: '15vh auto', textAlign: 'center', fontFamily: 'sans-serif' }}>
      <h1 style={{ fontSize: 28, marginBottom: 4 }}>Grit Admin</h1>
      <p style={{ color: '#666', marginBottom: 28 }}>Sign in to manage your organisation.</p>

      {error && (
        <p style={{ color: '#c0392b', background: '#fdecea', padding: '8px 12px', borderRadius: 4, fontSize: 14 }}>
          {error}
        </p>
      )}

      <button
        onClick={handleGitHub}
        disabled={loading}
        style={{
          display: 'block', width: '100%', padding: '11px 0',
          fontSize: 15, fontWeight: 600, cursor: loading ? 'wait' : 'pointer',
          background: '#24292e', color: '#fff', border: 'none', borderRadius: 6,
          marginBottom: 12,
        }}
      >
        {loading ? 'Waiting for GitHub…' : '⬡  Sign in with GitHub'}
      </button>

      {/* Dev bypass — auto-login with VITE_DEV_TOKEN if set */}
      {DEV_TOKEN && (
        <button
          onClick={() => setToken(DEV_TOKEN)}
          style={{
            display: 'block', width: '100%', padding: '10px 0',
            fontSize: 14, cursor: 'pointer',
            background: '#fff3cd', color: '#856404', border: '1px solid #ffc107', borderRadius: 6,
            marginBottom: 12,
          }}
        >
          Dev: auto-login (VITE_DEV_TOKEN)
        </button>
      )}

      {/* Manual token paste — visible in dev mode */}
      {isDev && (
        <button
          onClick={handleDevLogin}
          style={{
            background: 'none', border: 'none', color: '#888',
            fontSize: 13, cursor: 'pointer', textDecoration: 'underline',
          }}
        >
          Paste a token manually
        </button>
      )}

      <p style={{ marginTop: 28, fontSize: 12, color: '#aaa' }}>
        The admin UI requires the Grit backend to be running.{' '}
        <a href="https://github.com/your-org/grit#backend" style={{ color: '#aaa' }}>
          Setup guide →
        </a>
      </p>
    </div>
  )
}
