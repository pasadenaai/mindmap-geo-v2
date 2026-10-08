import { useState } from 'react'
import { useAuthStore } from '../../store'

export default function Login() {
  const { login, register } = useAuthStore()
  const [mode, setMode] = useState('login')
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)

  const submit = async (e) => {
    e.preventDefault()
    setError(''); setLoading(true)
    try {
      if (mode === 'login') await login(username, password)
      else await register(username, password)
    } catch {
      setError(mode === 'login' ? 'Invalid username or password.' : 'Registration failed. Username may be taken.')
    } finally { setLoading(false) }
  }

  return (
    <div style={styles.wrap}>
      <div style={styles.card}>
        <div style={styles.brand}>
          <svg width="36" height="36" viewBox="0 0 24 24" fill="none">
            <circle cx="12" cy="12" r="10" stroke="#4fc3f7" strokeWidth="1.5" fill="none"/>
            <ellipse cx="12" cy="12" rx="4" ry="10" stroke="#4fc3f7" strokeWidth="1" fill="none"/>
            <line x1="2" y1="12" x2="22" y2="12" stroke="#4fc3f7" strokeWidth="1"/>
          </svg>
          <h1 style={styles.brandName}>mindmap-geo</h1>
        </div>
        <h2 style={styles.title}>{mode === 'login' ? 'Sign In' : 'Create Account'}</h2>
        <form onSubmit={submit} style={styles.form}>
          <input style={styles.input} type="text" placeholder="Username" value={username} onChange={e => setUsername(e.target.value)} required autoFocus/>
          <input style={styles.input} type="password" placeholder="Password" value={password} onChange={e => setPassword(e.target.value)} required/>
          {error && <p style={styles.error}>{error}</p>}
          <button style={{...styles.btn, opacity: loading ? 0.7 : 1}} type="submit" disabled={loading}>
            {loading ? 'Please wait…' : mode === 'login' ? 'Sign In' : 'Create Account'}
          </button>
        </form>
        <p style={styles.toggle}>
          {mode === 'login' ? "Don't have an account? " : 'Already have an account? '}
          <button style={styles.link} onClick={() => { setMode(mode === 'login' ? 'register' : 'login'); setError('') }}>
            {mode === 'login' ? 'Register' : 'Sign In'}
          </button>
        </p>
      </div>
    </div>
  )
}

const styles = {
  wrap: { display: 'flex', alignItems: 'center', justifyContent: 'center', height: '100vh', background: '#020a14' },
  card: { background: '#0d1b2a', border: '1px solid #1e3a5f', borderRadius: '16px', padding: '40px', width: '100%', maxWidth: '360px', display: 'flex', flexDirection: 'column', gap: '24px' },
  brand: { display: 'flex', alignItems: 'center', gap: '12px', justifyContent: 'center' },
  brandName: { fontSize: '20px', fontWeight: 800, color: '#4fc3f7', margin: 0 },
  title: { textAlign: 'center', fontSize: '17px', fontWeight: 600, color: '#8ab4d4', margin: 0 },
  form: { display: 'flex', flexDirection: 'column', gap: '12px' },
  input: { background: '#081420', border: '1px solid #1e3a5f', borderRadius: '8px', color: '#e0f0ff', padding: '10px 14px', fontSize: '14px', outline: 'none', width: '100%', boxSizing: 'border-box' },
  error: { color: '#f87171', fontSize: '13px', textAlign: 'center', margin: 0 },
  btn: { background: '#1a6dbf', border: 'none', borderRadius: '8px', color: 'white', padding: '10px', fontSize: '14px', fontWeight: 600, width: '100%', cursor: 'pointer', transition: 'background 0.15s' },
  toggle: { textAlign: 'center', fontSize: '13px', color: '#5a8aaa', margin: 0 },
  link: { background: 'none', border: 'none', color: '#4fc3f7', fontSize: '13px', padding: 0, textDecoration: 'underline', cursor: 'pointer' },
}
