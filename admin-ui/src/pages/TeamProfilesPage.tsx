import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import {
  listTeamProfiles, createTeamProfile, updateTeamProfile, deleteTeamProfile,
  type TeamProfile,
} from '../api/enterprise'

const ORG_ID = localStorage.getItem('grit_org_id') ?? ''

const empty: Partial<TeamProfile> = {
  name: '', email: '', gpg_key_id: null, ssh_key_path: null,
  path_patterns: [], remote_patterns: [],
}

export default function TeamProfilesPage() {
  const qc = useQueryClient()
  const { data: profiles = [], isLoading } = useQuery({
    queryKey: ['team-profiles', ORG_ID],
    queryFn: () => listTeamProfiles(ORG_ID),
  })

  const [editing, setEditing] = useState<Partial<TeamProfile> | null>(null)
  const [isNew, setIsNew] = useState(false)

  const saveMut = useMutation({
    mutationFn: (p: Partial<TeamProfile>) =>
      p.id ? updateTeamProfile(ORG_ID, p.id, p) : createTeamProfile(ORG_ID, p),
    onSuccess: () => { setEditing(null); qc.invalidateQueries({ queryKey: ['team-profiles'] }) },
  })

  const deleteMut = useMutation({
    mutationFn: (id: string) => deleteTeamProfile(ORG_ID, id),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['team-profiles'] }),
  })

  if (isLoading) return <p>Loading…</p>

  return (
    <div>
      <h2>Team Profiles</h2>
      <button onClick={() => { setEditing({ ...empty }); setIsNew(true) }}>+ New profile</button>

      {editing && (
        <ProfileForm
          profile={editing}
          isNew={isNew}
          onChange={setEditing}
          onSave={() => saveMut.mutate(editing)}
          onCancel={() => setEditing(null)}
          saving={saveMut.isPending}
        />
      )}

      <table style={{ width: '100%', borderCollapse: 'collapse', marginTop: 16 }}>
        <thead>
          <tr>
            <th style={{ textAlign: 'left' }}>Name</th>
            <th style={{ textAlign: 'left' }}>Email</th>
            <th style={{ textAlign: 'left' }}>GPG</th>
            <th style={{ textAlign: 'left' }}>Updated</th>
            <th />
          </tr>
        </thead>
        <tbody>
          {profiles.map(p => (
            <tr key={p.id} style={{ borderTop: '1px solid #eee' }}>
              <td>{p.name}</td>
              <td>{p.email}</td>
              <td>{p.gpg_key_id ?? '—'}</td>
              <td>{new Date(p.updated_at).toLocaleDateString()}</td>
              <td>
                <button onClick={() => { setEditing(p); setIsNew(false) }}>Edit</button>
                {' '}
                <button onClick={() => { if (confirm('Delete this profile?')) deleteMut.mutate(p.id) }}>Delete</button>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}

function ProfileForm({
  profile, isNew, onChange, onSave, onCancel, saving,
}: {
  profile: Partial<TeamProfile>
  isNew: boolean
  onChange: (p: Partial<TeamProfile>) => void
  onSave: () => void
  onCancel: () => void
  saving: boolean
}) {
  const set = (key: keyof TeamProfile) => (e: React.ChangeEvent<HTMLInputElement>) =>
    onChange({ ...profile, [key]: e.target.value || null })

  return (
    <div style={{ border: '1px solid #ccc', padding: 16, marginTop: 16, maxWidth: 480 }}>
      <h3>{isNew ? 'New Team Profile' : `Edit — ${profile.name}`}</h3>
      <label>Name<br />
        <input value={profile.name ?? ''} onChange={e => onChange({ ...profile, name: e.target.value })} />
      </label><br />
      <label>Email<br />
        <input value={profile.email ?? ''} onChange={e => onChange({ ...profile, email: e.target.value })} />
      </label><br />
      <label>GPG Key ID<br />
        <input value={profile.gpg_key_id ?? ''} onChange={set('gpg_key_id')} />
      </label><br />
      <label>SSH Key Path<br />
        <input value={profile.ssh_key_path ?? ''} onChange={set('ssh_key_path')} />
      </label><br />
      <label>Path patterns (comma-separated)<br />
        <input
          value={(profile.path_patterns ?? []).join(', ')}
          onChange={e => onChange({ ...profile, path_patterns: e.target.value.split(',').map(s => s.trim()).filter(Boolean) })}
          style={{ width: '100%' }}
        />
      </label><br />
      <div style={{ marginTop: 12 }}>
        <button onClick={onSave} disabled={saving || !profile.name || !profile.email}>
          {saving ? 'Saving…' : 'Save'}
        </button>
        {' '}
        <button onClick={onCancel}>Cancel</button>
      </div>
    </div>
  )
}
