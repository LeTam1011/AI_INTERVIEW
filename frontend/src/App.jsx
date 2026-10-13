import { useEffect, useState } from 'react'
import axios from 'axios'
import './App.css'

const API = import.meta.env.VITE_API_URL || 'http://127.0.0.1:8000/api'
const TOKEN = 'ai_interview_access_token'

function App() {
  const [view, setView] = useState('landing')
  const [user, setUser] = useState(null)
  const [form, setForm] = useState({
    email: '',
    password: '',
    full_name: '',
  })
  const [error, setError] = useState('')
  const [busy, setBusy] = useState(false)
  const [isCheckingSession, setIsCheckingSession] = useState(true)

useEffect(() => {
  const token = localStorage.getItem(TOKEN)

  if (!token) {
    setIsCheckingSession(false)
    return
  }

  const checkSession = async () => {
    try {
      const response = await axios.get(
        `${API}/auth/me`,
        {
          headers: {
            Authorization: `Bearer ${token}`,
          },
        }
      )

      setUser(response.data)
      setView('dashboard')
    } catch (error) {
      localStorage.removeItem(TOKEN)
      setUser(null)
    } finally {
      setIsCheckingSession(false)
    }
  }

  checkSession()
}, [])

  const auth = (mode = 'login') => {
    setError('')
    setView(mode)
  }

  const submit = async (event) => {
    event.preventDefault()
    setBusy(true)
    setError('')

    try {
      const registering = view === 'register'
      const endpoint = registering ? '/auth/register' : '/auth/login'
      const payload = registering
        ? form
        : { email: form.email, password: form.password }

      const { data } = await axios.post(`${API}${endpoint}`, payload)

      localStorage.setItem(TOKEN, data.access_token)
      setUser(data.user)
      setView('dashboard')
      setForm({ email: '', password: '', full_name: '' })
    } catch (err) {
      const detail = err.response?.data?.detail
      setError(
        typeof detail === 'string'
          ? detail
          : Array.isArray(detail)
            ? detail.map(item => item.msg).join(', ')
            : 'Không thể xử lý yêu cầu. Vui lòng thử lại.'
      )
    } finally {
      setBusy(false)
    }
  }

  const logout = () => {
    localStorage.removeItem(TOKEN)
    setUser(null)
    setView('landing')
    setError('')
  }

  if (isCheckingSession) {
    return <main className="page"><p className="loading">Đang kiểm tra phiên đăng nhập...</p></main>
  }

  if (view === 'landing') {
    return (
      <Landing
        user={user}
        login={() => auth('login')}
        profile={() => setView('dashboard')}
      />
    )
  }

  if (view === 'dashboard' && user) {
    return <Dashboard user={user} home={logout} />
  }

  const registering = view === 'register'

  return (
    <main className="auth-page">
      <section className="auth-card">
        <button className="back" type="button" onClick={() => setView('landing')}>
          ← Trang chủ
        </button>

        <b className="eyebrow">AI Interview Trainer</b>
        <h1>{registering ? 'Tạo tài khoản' : 'Chào mừng trở lại'}</h1>
        <p>
          {registering
            ? 'Bắt đầu hành trình luyện phỏng vấn hiệu quả hơn.'
            : 'Đăng nhập để tiếp tục luyện phỏng vấn.'}
        </p>

        <form onSubmit={submit}>
          {registering && (
            <label>
              Họ và tên
              <input
                name="full_name"
                value={form.full_name}
                onChange={e => setForm({ ...form, full_name: e.target.value })}
                minLength={2}
                maxLength={120}
                required
              />
            </label>
          )}

          <label>
            Email
            <input
              type="email"
              value={form.email}
              onChange={e => setForm({ ...form, email: e.target.value })}
              required
            />
          </label>

          <label>
            Mật khẩu
            <input
              type="password"
              value={form.password}
              onChange={e => setForm({ ...form, password: e.target.value })}
              minLength={8}
              required
            />
          </label>

          {error && <p className="error" role="alert">{error}</p>}

          <button className="primary" type="submit" disabled={busy}>
            {busy
              ? 'Đang xử lý...'
              : registering
                ? 'Tạo tài khoản'
                : 'Đăng nhập'}
          </button>
        </form>

        <p className="switch">
          {registering ? 'Đã có tài khoản?' : 'Chưa có tài khoản?'}{' '}
          <button
            type="button"
            onClick={() => auth(registering ? 'login' : 'register')}
          >
            {registering ? 'Đăng nhập' : 'Đăng ký ngay'}
          </button>
        </p>
      </section>
    </main>
  )
}


function Dashboard({ user, home }) {
  const [cvFile, setCvFile] = useState(null)
  const [job, setJob] = useState({
    title: '',
    company_name: '',
    description: '',
    required_skills: '',
    preferred_skills: '',
    responsibilities: '',
    career_level: 'intern',
  })
  const [language, setLanguage] = useState('Vietnamese')
  const [resume, setResume] = useState(null)
  const [interview, setInterview] = useState(null)
  const [questions, setQuestions] = useState([])
  const [index, setIndex] = useState(0)
  const [answer, setAnswer] = useState('')
  const [evaluation, setEvaluation] = useState(null)
  const [followUp, setFollowUp] = useState(null)
  const [history, setHistory] = useState([])
  const [stage, setStage] = useState('setup')
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')

  const token = localStorage.getItem('ai_interview_access_token')
  const headers = { Authorization: `Bearer ${token}` }
  const current = questions[index]

  const updateJob = (key, value) =>
    setJob(old => ({ ...old, [key]: value }))

  const listValues = value =>
    value.split(/[\n,;]+/).map(x => x.trim()).filter(Boolean)

  const getError = err => {
    const detail = err.response?.data?.detail
    return typeof detail === 'string'
      ? detail
      : Array.isArray(detail)
        ? detail.map(x => x.msg).join(', ')
        : 'Có lỗi xảy ra. Hãy kiểm tra backend và dữ liệu gửi lên.'
  }

  const startInterview = async e => {
    e.preventDefault()
    setBusy(true)
    setError('')

    try {
      if (!cvFile) throw new Error('Vui lòng chọn CV PDF hoặc DOCX.')

      // 1. Upload CV
      const formData = new FormData()
      formData.append('file', cvFile)

      const resumeRes = await axios.post(
        `${API}/resumes/upload`,
        formData,
        { headers }
      )
      const savedResume = resumeRes.data
      setResume(savedResume)

      // 2. Create job description
      const jobRes = await axios.post(`${API}/jobs`, {
        title: job.title.trim(),
        company_name: job.company_name.trim() || 'Chưa cung cấp',
        description: job.description.trim(),
        required_skills: listValues(job.required_skills),
        preferred_skills: listValues(job.preferred_skills),
        responsibilities: listValues(job.responsibilities),
        career_level: job.career_level,
      }, { headers })

      
      const scoreRes = await axios.post(
        `${API}/resumes/${savedResume.id}/score`,
        {
          job_description_id: jobRes.data.id,
          career_level: job.career_level,
        },
        { headers }
      )

      
      const scoredResume = {
        ...savedResume,
        cv_score: scoreRes.data.overall_score,
        score_feedback: {
          strengths: scoreRes.data.strengths ?? [],
          improvements: scoreRes.data.improvements ?? [],
          breakdown: scoreRes.data.breakdown ?? {},
        },
      }

      setResume(scoredResume)


      console.log(
        'CV SCORE RESPONSE:',
        JSON.stringify(scoreRes.data, null, 2)
      )
      
      console.log(
        'CURRENT RESUME:',
        JSON.stringify(savedResume, null, 2)
      )


      // 3. Create interview
      const interviewRes = await axios.post(`${API}/interviews`, {
        resume_id: savedResume.id,
        job_description_id: jobRes.data.id,
        title: `Phỏng vấn ${job.title.trim()}`,
        career_level: job.career_level,
        language,
      }, { headers })

      const savedInterview = interviewRes.data
      setInterview(savedInterview)

      // 4. Generate questions
      const questionRes = await axios.post(
        `${API}/interviews/${savedInterview.id}/generate-questions`,
        null,
        { params: { count: 10 }, headers }
      )

      if (!Array.isArray(questionRes.data) || !questionRes.data.length) {
        throw new Error('Không tạo được câu hỏi phỏng vấn.')
      }

      setQuestions(questionRes.data)
      setIndex(0)
      setHistory([])
      setEvaluation(null)
      setFollowUp(null)
      setAnswer('')
      setStage('interview')
    } catch (err) {
      setError(getError(err))
    } finally {
      setBusy(false)
    }
  }

  const submitAnswer = async e => {
    e.preventDefault()
    if (!current || !answer.trim()) {
      setError('Vui lòng nhập câu trả lời.')
      return
    }

    setBusy(true)
    setError('')

    try {
      // Save answer first
      const answerRes = await axios.post(
        `${API}/questions/${current.id}/answers`,
        { answer_text: answer.trim() },
        { headers }
      )

      // Evaluate the latest saved answer
      const evalRes = await axios.post(
        `${API}/questions/${current.id}/evaluate`,
        null,
        { headers }
      )

      setEvaluation(evalRes.data)
      setHistory(old => [
        ...old,
        {
          question: current,
          answer: answerRes.data,
          evaluation: evalRes.data,
          followUp: null,
        },
      ])
      setFollowUp(null)
      setStage('feedback')
    } catch (err) {
      setError(getError(err))
    } finally {
      setBusy(false)
    }
  }

  const generateFollowUp = async () => {
    if (!current) return
    setBusy(true)
    setError('')

    try {
      const res = await axios.post(
        `${API}/questions/${current.id}/follow-up`,
        null,
        { headers }
      )
      setFollowUp(res.data)

      setHistory(old => old.map(item =>
        item.question.id === current.id
          ? { ...item, followUp: res.data }
          : item
      ))
    } catch (err) {
      setError(
        err.response?.status === 409
          ? 'Câu hỏi này đã có câu hỏi tiếp nối.'
          : getError(err)
      )
    } finally {
      setBusy(false)
    }
  }

  const answerFollowUp = () => {
    if (!followUp) return

    setQuestions(old => [
      ...old.slice(0, index + 1),
      followUp,
      ...old.slice(index + 1),
    ])
    setIndex(index + 1)
    setAnswer('')
    setEvaluation(null)
    setFollowUp(null)
    setStage('interview')
    setError('')
  }

  const nextQuestion = () => {
    if (index + 1 >= questions.length) {
      setStage('summary')
      return
    }

    setIndex(index + 1)
    setAnswer('')
    setEvaluation(null)
    setFollowUp(null)
    setStage('interview')
    setError('')
  }

  const averageScore = history.length
    ? (
        history.reduce(
          (sum, item) => sum + Number(item.evaluation?.total_score || 0),
          0
        ) / history.length
      ).toFixed(1)
    : null

    return (
      <div className="app">
        <aside className="sidebar">
          <div className="sidebar-logo">
            <div className="logo-icon">✦</div>
            <div className="logo-text">AI <span>Interviewer</span></div>
          </div>
  
          <nav className="sidebar-menu">
            <p className="menu-title">WORKSPACE</p>
            <button
              className="menu-item active"
              onClick={() => setStage('setup')}
            >
              <span className="menu-icon">♟</span>
              <span>Luyện phỏng vấn</span>
            </button>
            <button className="menu-item" onClick={home}>
              <span className="menu-icon">⌂</span>
              <span>Trang chủ</span>
            </button>
          </nav>
  
          <div className="sidebar-bottom">
            <div className="user-mini">
              <div className="user-avatar">
                {(user.full_name || 'U').charAt(0).toUpperCase()}
              </div>
              <div className="user-info">
                <div className="user-name">{user.full_name}</div>
                <div className="user-email">{user.email}</div>
              </div>
            </div>
          </div>
        </aside>
  
        <main className="main">
          <header className="topbar">
            <div>
              <div className="page-title">Mock Interview AI</div>
              <div className="page-subtitle">
                Luyện tập và cải thiện kỹ năng phỏng vấn
              </div>
            </div>
            <div className="topbar-right">
              <span>{user.full_name}</span>
            </div>
          </header>
  
          <div className="content">
            {error && (
              <p className="error" role="alert">{error}</p>
            )}
  
            {stage === 'setup' && (
              <>
                <section className="welcome-section">
                  <h1 className="welcome-title">Bắt đầu buổi phỏng vấn mới</h1>
                  <p className="welcome-description">
                    Tải CV và nhập mô tả công việc để tạo câu hỏi phù hợp với bạn.
                  </p>
                </section>
  
                <section className="panel">
                  <h2 className="panel-title">Thông tin phỏng vấn</h2>
                  <p className="panel-description">
                    Các trường có dấu * là bắt buộc.
                  </p>
  
                  <form onSubmit={startInterview}>
                    <div className="form-group">
                      <label className="form-label">CV của bạn *</label>
                      <div className="upload-box">
                        <div className="upload-icon">↑</div>
                        <div className="upload-title">
                          {cvFile ? cvFile.name : 'Chọn CV để tải lên'}
                        </div>
                        <div className="upload-description">
                          Hỗ trợ định dạng PDF hoặc DOCX
                        </div>
                        <input
                          className="form-input"
                          type="file"
                          accept=".pdf,.docx"
                          onChange={e => setCvFile(e.target.files?.[0] || null)}
                          required
                        />
                      </div>
                    </div>
  
                    <div className="form-group">
                      <label className="form-label">Vị trí ứng tuyển *</label>
                      <input
                        className="form-input"
                        value={job.title}
                        onChange={e => updateJob('title', e.target.value)}
                        placeholder="Ví dụ: Backend Developer Intern"
                        minLength={2}
                        required
                      />
                    </div>
  
                    <div className="form-group">
                      <label className="form-label">Công ty</label>
                      <input
                        className="form-input"
                        value={job.company_name}
                        onChange={e => updateJob('company_name', e.target.value)}
                        placeholder="Tên công ty ứng tuyển"
                      />
                    </div>
  
                    <div className="form-group">
                      <label className="form-label">Mô tả công việc (JD) *</label>
                      <textarea
                        className="form-textarea"
                        rows={5}
                        value={job.description}
                        onChange={e => updateJob('description', e.target.value)}
                        placeholder="Mô tả công việc, yêu cầu và kỹ năng cần có..."
                        minLength={10}
                        required
                      />
                    </div>
  
                    <div className="form-group">
                      <label className="form-label">Kỹ năng bắt buộc</label>
                      <textarea
                        className="form-textarea"
                        value={job.required_skills}
                        onChange={e => updateJob('required_skills', e.target.value)}
                        placeholder="Ví dụ: Python, SQL, REST API"
                      />
                    </div>
  
                    <div className="form-group">
                      <label className="form-label">Kỹ năng ưu tiên</label>
                      <textarea
                        className="form-textarea"
                        value={job.preferred_skills}
                        onChange={e => updateJob('preferred_skills', e.target.value)}
                        placeholder="Các kỹ năng bổ sung nếu có"
                      />
                    </div>
  
                    <div className="form-group">
                      <label className="form-label">Trách nhiệm công việc</label>
                      <textarea
                        className="form-textarea"
                        value={job.responsibilities}
                        onChange={e => updateJob('responsibilities', e.target.value)}
                        placeholder="Các nhiệm vụ chính của vị trí"
                      />
                    </div>
  
                    <div className="form-group">
                      <label className="form-label">Cấp độ ứng tuyển</label>
                      <select
                        className="form-select"
                        value={job.career_level}
                        onChange={e => updateJob('career_level', e.target.value)}
                      >
                        <option value="intern">Intern</option>
                        <option value="junior">Junior</option>
                        <option value="middle">Middle</option>
                        <option value="senior">Senior</option>
                      </select>
                    </div>
  
                    <div className="form-group">
                      <label className="form-label">Ngôn ngữ phỏng vấn</label>
                      <select
                        className="form-select"
                        value={language}
                        onChange={e => setLanguage(e.target.value)}
                      >
                        <option value="Vietnamese">Tiếng Việt</option>
                        <option value="English">English</option>
                      </select>
                    </div>
  
                    <button
                      className="primary-btn"
                      type="submit"
                      disabled={busy}
                    >
                      {busy ? 'Đang tạo buổi phỏng vấn...' : 'Bắt đầu phỏng vấn →'}
                    </button>
                  </form>
                </section>
              </>
            )}
  
            {stage === 'interview' && current && (
              <>
                <section className="welcome-section">
                  <h1 className="welcome-title">
                    Câu hỏi {index + 1}/{questions.length}
                  </h1>
                  <p className="welcome-description">
                    Chủ đề: {current.topic || 'Tổng quát'} · {current.question_type}
                  </p>
                </section>
  
                <section className="panel">
                  <h2 className="panel-title">{current.question_text}</h2>
                  <form onSubmit={submitAnswer}>
                    <div className="form-group">
                      <label className="form-label">Câu trả lời của bạn *</label>
                      <textarea
                        className="form-textarea"
                        rows={8}
                        value={answer}
                        onChange={e => setAnswer(e.target.value)}
                        placeholder="Trình bày câu trả lời và ví dụ cụ thể..."
                        required
                      />
                    </div>
                    <button className="primary-btn" disabled={busy}>
                      {busy ? 'Đang xử lý...' : 'Gửi câu trả lời và chấm điểm'}
                    </button>
                  </form>
                </section>
              </>
            )}
  
            {stage === 'feedback' && evaluation && (
              <>
                <section className="welcome-section">
                  <h1 className="welcome-title">
                    Kết quả: {evaluation.total_score}/100
                  </h1>
                  <p className="welcome-description">{evaluation.feedback}</p>
                </section>
  
                <section className="panel">
                  <h2 className="panel-title">Điểm mạnh</h2>
                  {evaluation.strengths?.length ? (
                    <ul>
                      {evaluation.strengths.map((item, i) => (
                        <li key={i}>{item}</li>
                      ))}
                    </ul>
                  ) : <p>Chưa có điểm mạnh được ghi nhận.</p>}
  
                  <h2 className="panel-title">Nội dung cần cải thiện</h2>
                  {evaluation.improvements?.length ? (
                    <ul>
                      {evaluation.improvements.map((item, i) => (
                        <li key={i}>{item}</li>
                      ))}
                    </ul>
                  ) : <p>Không có góp ý bổ sung.</p>}
  
                  <div className="form-group">
                    <button
                      className="primary-btn"
                      onClick={generateFollowUp}
                      disabled={busy || Boolean(followUp)}
                    >
                      {busy ? 'Đang tạo...' : 'Tạo câu hỏi tiếp nối'}
                    </button>
                  </div>
  
                  {followUp && (
                    <div className="form-group">
                      <h2 className="panel-title">Câu hỏi tiếp nối</h2>
                      <p>{followUp.question_text}</p>
                      <button className="primary-btn" onClick={answerFollowUp}>
                        Trả lời câu hỏi tiếp nối →
                      </button>
                    </div>
                  )}
  
                  <button className="primary-btn" onClick={nextQuestion}>
                    {index + 1 >= questions.length
                      ? 'Xem tổng kết'
                      : 'Bỏ qua, sang câu tiếp theo →'}
                  </button>
                </section>
              </>
            )}
  
            {stage === 'summary' && (
              <>
                <section className="welcome-section">
                  <h1 className="welcome-title">Hoàn thành buổi phỏng vấn</h1>
                  <p className="welcome-description">
                    Bạn đã hoàn thành phần luyện tập hiện tại.
                  </p>
                </section>
  
                <div className="stats-grid">
                  <div className="stat-card">
                    <div className="stat-label">Điểm CV</div>
                    <div className="stat-value">
                        {resume?.cv_score != null
                          ? `${Number(resume.cv_score).toFixed(2)}/100`
                          : 'N/A'}
                    </div>
                  </div>
                  <div className="stat-card">
                    <div className="stat-label">Số câu đã đánh giá</div>
                    <div className="stat-value">{history.length}</div>
                  </div>
                  <div className="stat-card">
                    <div className="stat-label">Điểm trung bình</div>
                    <div className="stat-value">{averageScore ?? 'N/A'}</div>
                  </div>
                </div>
  
                <section className="panel">
                  <h2 className="panel-title">Chi tiết kết quả</h2>
                  {history.map((item, i) => (
                    <article key={`${item.question.id}-${i}`}>
                      <h3>{i + 1}. {item.question.question_text}</h3>
                      <p>Điểm: {item.evaluation.total_score}/100</p>
                      <p>{item.evaluation.feedback}</p>
                    </article>
                  ))}
  
                  <button
                    className="primary-btn"
                    onClick={() => {
                      setStage('setup')
                      setQuestions([])
                      setHistory([])
                      setAnswer('')
                      setEvaluation(null)
                      setFollowUp(null)
                      setError('')
                    }}
                  >
                    Tạo buổi phỏng vấn mới
                  </button>
                </section>
              </>
            )}
          </div>
        </main>
      </div>
    )
}

function Landing({ user, login, profile }) { const cubes = [['AI','ai'],['JS','js'],['PY','py'],['SQL','sql'],['⚛','react'],['</>','code'],['✓','check']]; return <main className="landing"><header><button className="brand"><i>✦</i> AI Interviewer</button><nav><a href="#features">Tính năng</a><a href="#how">Cách dùng</a><a href="#reviews">Đánh giá</a></nav><div>{user ? <button className="login" onClick={profile}>Hồ sơ</button> : <button className="login" onClick={login}>Đăng nhập</button>}<button className="cta" onClick={login}>Bắt đầu miễn phí →</button></div></header><section className="hero" id="features"><div className="copy"><b className="badge">✦ Được hỗ trợ bởi AI</b><h1>Luyện phỏng vấn <em>thông minh hơn</em> với AI</h1><p>Upload CV, nhập vị trí ứng tuyển — AI tạo bộ câu hỏi cá nhân hóa, chấm điểm và phản hồi chi tiết từng câu trả lời của bạn.</p><div className="actions"><button className="cta big" onClick={login}>Bắt đầu miễn phí →</button><a href="#how">▷ Xem demo</a></div><div className="trust">★★★★★ <strong>4.9/5</strong> · 500+ người dùng <span>✓ Miễn phí</span></div></div><div className="scene">{cubes.map(([text,name]) => <div className={`cube ${name}`} key={name}>{text}</div>)}</div></section><section className="features" id="how"><article><b>01</b><h2>Phân tích CV</h2><p>Nhận diện kỹ năng và điểm mạnh của bạn.</p></article><article><b>02</b><h2>Luyện phỏng vấn</h2><p>Câu hỏi phù hợp với vị trí ứng tuyển.</p></article><article id="reviews"><b>03</b><h2>Nhận phản hồi</h2><p>Cải thiện sau mỗi lần thực hành.</p></article></section></main> }

export default App
