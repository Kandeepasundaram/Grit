export default function LoadingSpinner({ label = 'Loading…' }: { label?: string }) {
  return <p style={{ color: '#888', fontStyle: 'italic' }}>{label}</p>
}
