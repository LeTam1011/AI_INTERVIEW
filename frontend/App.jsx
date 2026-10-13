import { useEffect, useState } from 'react'
import axios from 'axios'
import './App.css'

const API_URL = import.meta.env.VITE_API_URL || 'http://127.0.0.1:8000/api'
const TOKEN_KEY = 'ai_interview_access_token'

function App() {
  const [mode, setMode] = useState('login')
  const [user, setUser] = useState(null)
  const [form, setForm] = useState({ email: '', password: '', full_name: '' })
  const [message, setMessage] = useState('')
  const [error, setError] = useState('')
  const [isSubmitting, setIsSubmitting] = useState(false)
  const [isCheckingSession, setIsCheckingSession] = useState(true)

  useEffect(() => {
    const token = localStorage.getItem(TOKEN_KEY)
    if (!token) {
      setIsCheckingSession(false)
      return
    }

    axios
      .get(`${API_URL}/auth/me`, { headers: { Authorization: `Bearer ${token}` } })
      .then(({ data }) => setUser(data))
      .catch(() => localStorage.removeItem(TOKEN_KEY))
      .finally(() => setIsCheckingSession(false))
  }, [])

  function updateField(event) {
    setForm((current) => ({ ...current, [event.target.name]: event.target.value }))
  }

  async function submit(event) {
    event.preventDefault()
    setError('')
    setMessage('')
    setIsSubmitting(true)

    try {
      const endpoint = mode === 'login' ? '/auth/login' : '/auth/register'
      const payload =
        mode === 'login'
          ? { email: form.email, password: form.password }
          : form
      const { data } = await axios.post(`${API_URL}${endpoint}`, payload)
      localStorage.setItem(TOKEN_KEY, data.access_token)
      setUser(data.user)
      setMessage(mode === 'login' ? 'Đăng nhập thành công.' : 'Tài khoản đã được tạo thành công.')
      setForm({ email: '', password: '', full_name: '' })
    } catch (requestError) {
      const detail = requestError.response?.data?.detail
      setError(typeof detail === 'string' ? detail : 'Không thể xử lý yêu cầu. Vui lòng thử lại.')
    } finally {
      setIsSubmitting(false)
    }
  }

  function logout() {
    localStorage.removeItem(TOKEN_KEY)
    setUser(null)
    setMessage('Bạn đã đăng xuất.')
  }

  if (isCheckingSession) {
    return <main className="page"><p className="loading">Đang kiểm tra phiên đăng nhập...</p></main>
  }

  if (user) {
    return (
      <main className="page">
        <section className="card dashboard" aria-labelledby="welcome-title">
          <span className="eyebrow">AI Interview Trainer</span>
          <h1 id="welcome-title">Chào, {user.full_name}</h1>
          <p className="lead">Bạn đã sẵn sàng luyện phỏng vấn cùng AI.</p>
          {message && <p className="success" role="status">{message}</p>}
          <dl className="profile">
            <div><dt>Email</dt><dd>{user.email}</dd></div>
            <div><dt>Vai trò</dt><dd>{user.role === 'admin' ? 'Quản trị viên' : 'Ứng viên'}</dd></div>
          </dl>
          <button className="secondary" type="button" onClick={logout}>Đăng xuất</button>
        </section>
      </main>
    )
  }

  const registering = mode === 'register'
  return (
    <main className="page">
      <section className="card" aria-labelledby="auth-title">
        <span className="eyebrow">AI Interview Trainer</span>
        <h1 id="auth-title">{registering ? 'Tạo tài khoản' : 'Chào mừng trở lại'}</h1>
        <p className="lead">
          {registering ? 'Bắt đầu hành trình luyện phỏng vấn hiệu quả hơn.' : 'Đăng nhập để tiếp tục luyện phỏng vấn.'}
        </p>

        <form onSubmit={submit}>
          {registering && (
            <label>
              Họ và tên
              <input name="full_name" value={form.full_name} onChange={updateField} minLength="2" maxLength="120" required autoComplete="name" />
            </label>
          )}
          <label>
            Email
            <input name="email" type="email" value={form.email} onChange={updateField} required autoComplete="email" />
          </label>
          <label>
            Mật khẩu
            <input name="password" type="password" value={form.password} onChange={updateField} minLength="8" required autoComplete={registering ? 'new-password' : 'current-password'} />
          </label>

          {error && <p className="error" role="alert">{error}</p>}
          {message && <p className="success" role="status">{message}</p>}
          <button className="primary" type="submit" disabled={isSubmitting}>
            {isSubmitting ? 'Đang xử lý...' : registering ? 'Tạo tài khoản' : 'Đăng nhập'}
          </button>
        </form>

        <p className="switch">
          {registering ? 'Đã có tài khoản?' : 'Chưa có tài khoản?'}{' '}
          <button type="button" onClick={() => { setMode(registering ? 'login' : 'register'); setError(''); setMessage('') }}>
            {registering ? 'Đăng nhập' : 'Đăng ký ngay'}
          </button>
        </p>
      </section>
    </main>
  )
}

export default App
