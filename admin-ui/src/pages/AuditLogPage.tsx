import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { queryAuditLog, type AuditEvent } from '../api/enterprise'

const ORG_ID = localStorage.getItem('grit_org_id') ?? ''

const ACTION_OPTIONS = [
  '', 'profile_switch', 'session_create', 'git_config_write',
]

export default function AuditLogPage() {
  const [since, setSince] = useState('')
  const [action, setAction] = useState('')
  const [limit, setLimit] = useState(100)

  const { data: events = [], isLoading, refetch } = useQuery({
    queryKey: ['audit', ORG_ID, since, action, limit],
    queryFn: () => queryAuditLog(ORG_ID, {
      since: since || undefined,
      action: action || undefined,
      limit,
    }),
  })

  function exportCSV() {
    const header = 'timestamp,action,user_id,repo_path,profile_name\n'
    const rows = events.map(e =>
      [e.timestamp, e.action, e.user_id ?? '', e.repo_path ?? '', e.profile_name ?? ''].join(',')
    ).join('\n')
    const blob = new Blob([header + rows], { type: 'text/csv' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `grit-audit-${new Date().toISOString().slice(0, 10)}.csv`
    a.click()
    URL.revokeObjectURL(url)
  }

  return (
    <div>
      <h2>Audit Log</h2>

      <div style={{ display: 'flex', gap: 12, flexWrap: 'wrap', marginBottom: 16 }}>
        <label>
          Since&nbsp;
          <input type="datetime-local" value={since} onChange={e => setSince(e.target.value)} />
        </label>
        <label>
          Action&nbsp;
          <select value={action} onChange={e => setAction(e.target.value)}>
            {ACTION_OPTIONS.map(a => <option key={a} value={a}>{a || 'All'}</option>)}
          </select>
        </label>
        <label>
          Limit&nbsp;
          <input type="number" value={limit} min={10} max={1000} style={{ width: 70 }}
            onChange={e => setLimit(parseInt(e.target.value, 10))} />
        </label>
        <button onClick={() => refetch()}>Refresh</button>
        <button onClick={exportCSV} disabled={events.length === 0}>Export CSV</button>
      </div>

      {isLoading ? (
        <p>Loading…</p>
      ) : (
        <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 13 }}>
          <thead style={{ background: '#f5f5f5' }}>
            <tr>
              <th style={{ textAlign: 'left', padding: '4px 8px' }}>Timestamp</th>
              <th style={{ textAlign: 'left', padding: '4px 8px' }}>Action</th>
              <th style={{ textAlign: 'left', padding: '4px 8px' }}>User</th>
              <th style={{ textAlign: 'left', padding: '4px 8px' }}>Profile</th>
              <th style={{ textAlign: 'left', padding: '4px 8px' }}>Repo</th>
            </tr>
          </thead>
          <tbody>
            {events.map(e => (
              <EventRow key={e.id} event={e} />
            ))}
          </tbody>
        </table>
      )}

      {!isLoading && events.length === 0 && (
        <p style={{ color: '#888' }}>No events found for the selected filters.</p>
      )}
    </div>
  )
}

function EventRow({ event: e }: { event: AuditEvent }) {
  const [expanded, setExpanded] = useState(false)
  return (
    <>
      <tr
        style={{ borderTop: '1px solid #eee', cursor: e.extra ? 'pointer' : 'default' }}
        onClick={() => e.extra && setExpanded(x => !x)}
      >
        <td style={{ padding: '4px 8px', fontFamily: 'monospace' }}>
          {new Date(e.timestamp).toLocaleString()}
        </td>
        <td style={{ padding: '4px 8px' }}>{e.action}</td>
        <td style={{ padding: '4px 8px', color: '#555' }}>{e.user_id ?? '—'}</td>
        <td style={{ padding: '4px 8px' }}>{e.profile_name ?? e.profile_id ?? '—'}</td>
        <td style={{ padding: '4px 8px', color: '#555', maxWidth: 240, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
          {e.repo_path ?? '—'}
        </td>
      </tr>
      {expanded && e.extra && (
        <tr>
          <td colSpan={5} style={{ padding: '4px 8px 8px 24px', background: '#fafafa' }}>
            <pre style={{ margin: 0, fontSize: 12 }}>{JSON.stringify(e.extra, null, 2)}</pre>
          </td>
        </tr>
      )}
    </>
  )
}
