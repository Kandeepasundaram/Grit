/**
 * Minimal auth store — persists JWT token in localStorage.
 * In a real app use a proper state library (Zustand, Jotai, etc.).
 */

type AuthState = {
  token: string | null
  setToken: (token: string) => void
  logout: () => void
}

function createStore() {
  let state: AuthState = {
    token: localStorage.getItem('grit_admin_token'),
    setToken(token: string) {
      localStorage.setItem('grit_admin_token', token)
      state.token = token
      listeners.forEach(l => l())
    },
    logout() {
      localStorage.removeItem('grit_admin_token')
      state.token = null
      listeners.forEach(l => l())
    },
  }

  const listeners = new Set<() => void>()

  function subscribe(listener: () => void) {
    listeners.add(listener)
    return () => listeners.delete(listener)
  }

  function getSnapshot() {
    return state
  }

  return { subscribe, getSnapshot }
}

const store = createStore()

// Minimal hook — works without Zustand
import { useSyncExternalStore } from 'react'

export function useAuthStore<T>(selector: (s: AuthState) => T): T {
  return selector(useSyncExternalStore(store.subscribe, store.getSnapshot))
}
