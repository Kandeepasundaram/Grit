import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { getOrg, updateOrg, listMembers, addMember, removeMember, type OrgConfig } from '../api/enterprise'

// Org ID is stored in localStorage after first org creation / login.
// In a real app this would come from the session context.
const ORG_ID = localStorage.getItem('grit_org_id') ?? ''

export default function OrgPage() {
  const qc = useQueryClient()
  const { data: org, isLoading } = useQuery({ queryKey: ['org', ORG_ID], queryFn: () => getOrg(ORG_ID) })
  const { data: members = [] } = useQuery({ queryKey: ['members', ORG_ID], queryFn: () => listMembers(ORG_ID) })

  const patchOrg = useMutation({
    mutationFn: (patch: Partial<OrgConfig>) => updateOrg(ORG_ID, patch),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['org'] }),
  })
  const removeM = useMutation({
    mutationFn: (userId: string) => removeMember(ORG_ID, userId),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['members'] }),
  })

  const [inviteEmail, setInviteEmail] = useState('')
  const addM = useMutation({
    mutationFn: () => addMember(ORG_ID, inviteEmail, 'member'),
    onSuccess: () => { setInviteEmail(''); qc.invalidateQueries({ queryKey: ['members'] }) },
  })

  if (isLoading) return <p>Loading…</p>
  if (!org) return <p>No organisation found. Set <code>grit_org_id</code> in localStorage.</p>

  return (
    <div>
      <h2>Organisation — {org.name}</h2>

      <section>
        <h3>SSO Configuration</h3>
        <label>
          IdP type&nbsp;
          <select
            value={org.idp_type}
            onChange={e => patchOrg.mutate({ idp_type: e.target.value })}
          >
            <option value="none">None</option>
            <option value="oidc">OIDC</option>
            <option value="saml">SAML</option>
          </select>
        </label>
        <br />
        <label>
          IdP URL&nbsp;
          <input
            defaultValue={org.idp_url ?? ''}
            onBlur={e => patchOrg.mutate({ idp_url: e.target.value || null })}
            style={{ width: 360 }}
          />
        </label>
        <br />
        <label>
          Client ID&nbsp;
          <input
            defaultValue={org.client_id ?? ''}
            onBlur={e => patchOrg.mutate({ client_id: e.target.value || null })}
            style={{ width: 280 }}
          />
        </label>
        <br />
        <label>
          <input
            type="checkbox"
            checked={org.enforce_sso}
            onChange={e => patchOrg.mutate({ enforce_sso: e.target.checked })}
          />
          &nbsp;Enforce SSO (block commits without active session)
        </label>
        <br />
        <label>
          Session TTL (hours)&nbsp;
          <input
            type="number"
            defaultValue={org.sso_ttl_hours}
            min={1}
            max={168}
            onBlur={e => patchOrg.mutate({ sso_ttl_hours: parseInt(e.target.value, 10) })}
            style={{ width: 60 }}
          />
        </label>
      </section>

      <section style={{ marginTop: 32 }}>
        <h3>Members ({members.length})</h3>
        <table style={{ width: '100%', borderCollapse: 'collapse' }}>
          <thead>
            <tr>
              <th style={{ textAlign: 'left' }}>Email</th>
              <th style={{ textAlign: 'left' }}>Role</th>
              <th style={{ textAlign: 'left' }}>Joined</th>
              <th />
            </tr>
          </thead>
          <tbody>
            {members.map(m => (
              <tr key={m.user_id} style={{ borderTop: '1px solid #eee' }}>
                <td>{m.email}</td>
                <td>{m.role}</td>
                <td>{new Date(m.joined_at).toLocaleDateString()}</td>
                <td>
                  {m.role !== 'owner' && (
                    <button onClick={() => removeM.mutate(m.user_id)}>Remove</button>
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>

        <div style={{ marginTop: 12 }}>
          <input
            placeholder="user@example.com"
            value={inviteEmail}
            onChange={e => setInviteEmail(e.target.value)}
            style={{ width: 240 }}
          />
          <button onClick={() => addM.mutate()} disabled={!inviteEmail} style={{ marginLeft: 8 }}>
            Add member
          </button>
        </div>
      </section>
    </div>
  )
}
