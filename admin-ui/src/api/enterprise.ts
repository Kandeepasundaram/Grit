import api from './client'

export type OrgConfig = {
  id: string
  name: string
  slug: string
  idp_type: string
  idp_url: string | null
  client_id: string | null
  enforce_sso: boolean
  sso_ttl_hours: number
}

export type OrgMember = {
  user_id: string
  email: string
  name: string | null
  role: string
  joined_at: string
}

export type TeamProfile = {
  id: string
  name: string
  email: string
  gpg_key_id: string | null
  ssh_key_path: string | null
  path_patterns: string[]
  remote_patterns: string[]
  updated_at: string
}

export type AuditEvent = {
  id: string
  action: string
  timestamp: string
  user_id: string | null
  repo_path: string | null
  profile_id: string | null
  profile_name: string | null
  extra: Record<string, unknown> | null
}

// ── Org ──────────────────────────────────────────────────────────────────────

export const getOrg = (orgId: string) =>
  api.get<OrgConfig>(`/enterprise/orgs/${orgId}`).then(r => r.data)

export const updateOrg = (orgId: string, patch: Partial<OrgConfig>) =>
  api.patch(`/enterprise/orgs/${orgId}`, patch).then(r => r.data)

// ── Members ───────────────────────────────────────────────────────────────────

export const listMembers = (orgId: string) =>
  api.get<OrgMember[]>(`/enterprise/orgs/${orgId}/members`).then(r => r.data)

export const addMember = (orgId: string, email: string, role: string) =>
  api.post(`/enterprise/orgs/${orgId}/members`, { email, role }).then(r => r.data)

export const removeMember = (orgId: string, userId: string) =>
  api.delete(`/enterprise/orgs/${orgId}/members/${userId}`)

// ── Team Profiles ─────────────────────────────────────────────────────────────

export const listTeamProfiles = (orgId: string) =>
  api.get<TeamProfile[]>(`/enterprise/orgs/${orgId}/profiles`).then(r => r.data)

export const createTeamProfile = (orgId: string, profile: Partial<TeamProfile>) =>
  api.post<TeamProfile>(`/enterprise/orgs/${orgId}/profiles`, profile).then(r => r.data)

export const updateTeamProfile = (orgId: string, profileId: string, profile: Partial<TeamProfile>) =>
  api.put<TeamProfile>(`/enterprise/orgs/${orgId}/profiles/${profileId}`, profile).then(r => r.data)

export const deleteTeamProfile = (orgId: string, profileId: string) =>
  api.delete(`/enterprise/orgs/${orgId}/profiles/${profileId}`)

// ── Audit ─────────────────────────────────────────────────────────────────────

export const queryAuditLog = (orgId: string, params?: { since?: string; action?: string; limit?: number }) =>
  api.get<AuditEvent[]>(`/enterprise/orgs/${orgId}/audit`, { params }).then(r => r.data)

// ── Subscription (reuse /v1/account) ─────────────────────────────────────────

export const getSubscription = () =>
  api.get('/account').then(r => r.data)
