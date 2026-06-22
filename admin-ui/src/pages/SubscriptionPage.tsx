import { useQuery } from '@tanstack/react-query'
import { getSubscription } from '../api/enterprise'

export default function SubscriptionPage() {
  const { data, isLoading } = useQuery({
    queryKey: ['subscription'],
    queryFn: getSubscription,
  })

  if (isLoading) return <p>Loading…</p>
  if (!data) return <p>Could not load subscription details.</p>

  const { tier, profile_limit, expires_at, email } = data

  return (
    <div>
      <h2>Subscription</h2>
      <table style={{ borderCollapse: 'collapse' }}>
        <tbody>
          <tr><td style={td}>Account email</td><td style={td}>{email ?? '—'}</td></tr>
          <tr><td style={td}>Tier</td><td style={td}><strong>{tier}</strong></td></tr>
          <tr>
            <td style={td}>Profile limit</td>
            <td style={td}>{profile_limit === -1 ? 'Unlimited' : profile_limit}</td>
          </tr>
          <tr>
            <td style={td}>Expires</td>
            <td style={td}>{expires_at ? new Date(expires_at).toLocaleDateString() : 'Never'}</td>
          </tr>
        </tbody>
      </table>

      {tier === 'free' && (
        <div style={{ marginTop: 24, padding: 16, background: '#fff8e1', borderRadius: 4 }}>
          <strong>Upgrade to Pro</strong> for unlimited profiles, cloud sync, and team sharing.
          {' '}
          <a href="https://grit.dev/pricing" target="_blank" rel="noreferrer">Learn more →</a>
        </div>
      )}

      {tier === 'pro' && (
        <div style={{ marginTop: 24, padding: 16, background: '#e8f5e9', borderRadius: 4 }}>
          You're on <strong>Grit Pro</strong>. Need enterprise SSO and audit logs?
          {' '}
          <a href="https://grit.dev/enterprise" target="_blank" rel="noreferrer">Contact sales →</a>
        </div>
      )}
    </div>
  )
}

const td: React.CSSProperties = {
  padding: '8px 16px',
  borderBottom: '1px solid #eee',
  verticalAlign: 'top',
}
