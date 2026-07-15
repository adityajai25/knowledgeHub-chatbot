import { useEffect, useMemo, useRef, useState } from 'react';
import { Link, Navigate, Route, Routes, useNavigate } from 'react-router-dom';
import axios from 'axios';
import './styles.css';

function NavBar({ isAuthenticated, onLogout }) {
  return (
    <nav className="navbar">
      <Link to="/" className="brand">KnowledgeHub AI</Link>
      <div className="nav-links">
        <Link to="/" className="nav-link">Home</Link>
        <Link to="/about" className="nav-link">About</Link>
        {isAuthenticated ? (
          <>
            <Link to="/dashboard" className="nav-link">Dashboard</Link>
            <button className="nav-button" onClick={onLogout}>Logout</button>
          </>
        ) : (
          <Link to="/auth" className="nav-button">Get Started</Link>
        )}
      </div>
    </nav>
  );
}

function AuthPage({ onAuthenticate }) {
  const [mode, setMode] = useState('login');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [message, setMessage] = useState('');
  const navigate = useNavigate();

  const handleSubmit = async (e) => {
    e.preventDefault();
    try {
      const endpoint = mode === 'login' ? '/api/auth/login' : '/api/auth/register';
      const response = await axios.post(`http://localhost:8000${endpoint}`, { email, password });
      setMessage(mode === 'login' ? 'Login successful' : 'Registration successful');
      if (response.data.access_token) {
        localStorage.setItem('token', response.data.access_token);
        onAuthenticate();
        navigate('/dashboard');
      }
    } catch (error) {
      setMessage(error.response?.data?.detail || 'Request failed');
    }
  };

  return (
    <div className="auth-page">
      <div className="auth-card">
        <h2>{mode === 'login' ? 'Welcome back' : 'Create your account'}</h2>
        <p className="muted">Secure access to your document intelligence workspace.</p>
        <div className="auth-toggle">
          <button className={mode === 'login' ? 'active' : ''} onClick={() => setMode('login')}>
            Login
          </button>
          <button className={mode === 'register' ? 'active' : ''} onClick={() => setMode('register')}>
            Register
          </button>
        </div>
        <form onSubmit={handleSubmit}>
          <div className="form-group">
            <label htmlFor="email">Email</label>
            <input id="email" value={email} onChange={(e) => setEmail(e.target.value)} placeholder="you@example.com" />
          </div>
          <div className="form-group">
            <label htmlFor="password">Password</label>
            <input id="password" type="password" value={password} onChange={(e) => setPassword(e.target.value)} placeholder="Enter password" />
          </div>
          <button type="submit" className="form-btn">{mode === 'login' ? 'Login' : 'Register'}</button>
          {message && <p className="form-message">{message}</p>}
        </form>
      </div>
    </div>
  );
}

function HomePage() {
  return (
    <div className="app-shell">
      <NavBar isAuthenticated={false} onLogout={() => {}} />
      <section className="hero">
        <div className="hero-copy">
          <h1>Turn documents into instant knowledge.</h1>
          <p>
            KnowledgeHub AI helps teams upload industrial documents, extract insights, search semantically, and ask questions in natural language.
          </p>
          <div className="hero-actions">
            <Link to="/auth" className="primary-btn">Start free</Link>
            <Link to="/about" className="secondary-btn">See how it works</Link>
          </div>
        </div>
        <div className="hero-card">
          <div className="hero-metric">
            <span>Documents processed</span>
            <strong>1.2K+</strong>
          </div>
          <div className="hero-metric">
            <span>Average response time</span>
            <strong>&lt; 3s</strong>
          </div>
          <div className="hero-metric">
            <span>Search accuracy</span>
            <strong>94%</strong>
          </div>
        </div>
      </section>

      <section className="section">
        <h2 className="section-title">Built for modern knowledge work</h2>
        <div className="feature-grid">
          <div className="card">
            <h3>Upload anything</h3>
            <p>PDFs, manuals, SOPs, reports, and technical documents can be brought into one workspace.</p>
          </div>
          <div className="card">
            <h3>Semantic search</h3>
            <p>Find the right information by meaning, not just keywords, with a vector-powered search layer.</p>
          </div>
          <div className="card">
            <h3>Ask questions</h3>
            <p>Chat with your uploaded documents and get grounded answers with retrieval-augmented generation.</p>
          </div>
        </div>
      </section>
    </div>
  );
}

function AboutPage() {
  return (
    <div className="app-shell">
      <NavBar isAuthenticated={false} onLogout={() => {}} />
      <section className="section" style={{ paddingTop: '2rem' }}>
        <h2 className="section-title">How the platform works</h2>
        <div className="feature-grid">
          <div className="card">
            <h3>1. Ingest</h3>
            <p>Upload your documents and store them in a secure workspace.</p>
          </div>
          <div className="card">
            <h3>2. Understand</h3>
            <p>Extract text, split it into chunks, and generate embeddings for search.</p>
          </div>
          <div className="card">
            <h3>3. Interact</h3>
            <p>Ask questions and get clever, grounded responses through the chat experience.</p>
          </div>
        </div>
      </section>
    </div>
  );
}

function DashboardPage({ onLogout }) {
  const stats = useMemo(() => [
    { label: 'Documents uploaded', value: '12' },
    { label: 'Embeddings indexed', value: '3.4K' },
    { label: 'Questions answered', value: '86' },
  ], []);

  const fileInputRef = useRef(null);
  const [docs, setDocs] = useState([]);

  const [chatInput, setChatInput] = useState('');
  const [chatHistory, setChatHistory] = useState([]);
  const [chatLoading, setChatLoading] = useState(false);
  const [searchQuery, setSearchQuery] = useState('');
  const [searchResults, setSearchResults] = useState([]);
  const [searchLoading, setSearchLoading] = useState(false);

  const fetchDocs = async () => {
    try {
      const token = localStorage.getItem('token');
      if (!token) return;
      const res = await axios.get('http://localhost:8000/api/docs/', { headers: { Authorization: `Bearer ${token}` } });
      setDocs(res.data || []);
    } catch (err) {
      console.error('fetchDocs error', err?.response || err);
    }
  };

  useEffect(() => {
    fetchDocs();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const handleFiles = async (e) => {
    const files = Array.from(e.target.files || []);
    if (files.length === 0) return;
    const token = localStorage.getItem('token');
    if (!token) {
      alert('Please login first');
      return;
    }

    const fd = new FormData();
    files.forEach((f) => fd.append('files', f));
    try {
      const res = await axios.post('http://localhost:8000/api/docs/upload', fd, {
        headers: { 'Content-Type': 'multipart/form-data', Authorization: `Bearer ${token}` },
      });
      console.log('upload res', res.data);
      await fetchDocs();
    } catch (err) {
      console.error('upload error', err?.response || err);
      alert('Upload failed');
    } finally {
      e.target.value = null;
    }
  };

  const handleSendChat = async () => {
    const token = localStorage.getItem('token');
    if (!token) {
      alert('Please login first');
      return;
    }
    if (!chatInput.trim()) return;

    const newHistory = [...chatHistory, { role: 'user', text: chatInput.trim() }];
    setChatHistory(newHistory);
    setChatLoading(true);

    try {
      const res = await axios.post('http://localhost:8000/api/docs/chat', { query: chatInput.trim(), top_k: 3 }, { headers: { Authorization: `Bearer ${token}` } });
      setChatHistory((prev) => [...prev, {
        role: 'assistant',
        text: res.data.answer || 'No answer returned.',
        sources: res.data.sources || [],
      }]);
      setChatInput('');
    } catch (err) {
      console.error('chat error', err?.response || err);
      setChatHistory((prev) => [...prev, { role: 'assistant', text: 'Chat failed: ' + (err.response?.data?.detail || err.message), sources: [] }]);
    } finally {
      setChatLoading(false);
    }
  };

  const handleSearch = async () => {
    const token = localStorage.getItem('token');
    if (!token) {
      alert('Please login first');
      return;
    }
    if (!searchQuery.trim()) return;

    setSearchLoading(true);
    try {
      const res = await axios.post('http://localhost:8000/api/docs/search', { query: searchQuery.trim(), top_k: 5 }, { headers: { Authorization: `Bearer ${token}` } });
      setSearchResults(res.data.results || []);
    } catch (err) {
      console.error('search error', err?.response || err);
      setSearchResults([]);
      alert('Search failed: ' + (err.response?.data?.detail || err.message));
    } finally {
      setSearchLoading(false);
    }
  };

  const handleClearChat = () => {
    setChatHistory([]);
    setChatInput('');
  };

  return (
    <div className="app-shell">
      <NavBar isAuthenticated onLogout={onLogout} />
      <div className="dashboard-page">
        <div className="dashboard-grid">
          <aside className="sidebar">
            <h3>Workspace</h3>
            <ul>
              <li>Upload documents</li>
              <li>Semantic search</li>
              <li>AI chat</li>
              <li>Team insights</li>
            </ul>
          </aside>

          <main className="dashboard-main">
            <div className="stats-grid">
              {stats.map((stat) => (
                <div className="dashboard-card" key={stat.label}>
                  <h4>{stat.value}</h4>
                  <p>{stat.label}</p>
                </div>
              ))}
            </div>

            <div className="panel-grid">
              <div className="dashboard-card">
                <h3>Upload documents</h3>
                <div className="upload-box">
                  <p className="muted">Drag and drop files here or browse from your device.</p>
                  <input
                    type="file"
                    multiple
                    ref={fileInputRef}
                    style={{ display: 'none' }}
                    onChange={(e) => handleFiles(e)}
                  />
                  <button className="primary-btn" onClick={() => fileInputRef.current?.click()}>Choose files</button>
                </div>
                <div style={{ marginTop: 12 }}>
                  <h4>Uploaded documents</h4>
                  {docs.length === 0 ? (
                    <p className="muted">No documents uploaded yet.</p>
                  ) : (
                    <ul>
                      {docs.map((d) => (
                        <li key={d.id}>{d.filename} <small className="muted">{new Date(d.uploaded_at).toLocaleString()}</small></li>
                      ))}
                    </ul>
                  )}
                </div>

                <div className="search-box" style={{ marginTop: 18 }}>
                  <h4>Semantic search</h4>
                  <div className="search-input-group">
                    <textarea value={searchQuery} onChange={(e) => setSearchQuery(e.target.value)} rows={3} placeholder="Search your documents by meaning..." />
                    <button className="secondary-btn" onClick={handleSearch} disabled={searchLoading}>
                      {searchLoading ? 'Searching…' : 'Search'}
                    </button>
                  </div>
                  <div className="search-results">
                    {searchResults.length === 0 ? (
                      <p className="muted">Search results will appear here.</p>
                    ) : (
                      searchResults.map((result, idx) => (
                        <div key={idx} className="search-result-card">
                          <div className="result-snippet">{result.meta?.text || 'No snippet available.'}</div>
                        </div>
                      ))
                    )}
                  </div>
                </div>
              </div>

              <div className="dashboard-card chat-panel">
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', gap: 12 }}>
                  <h3>Ask your knowledge base</h3>
                  <button className="secondary-btn" style={{ padding: '0.65rem 0.85rem', fontSize: '0.9rem' }} onClick={handleClearChat}>Clear</button>
                </div>
                <div className="chat-window">
                  {chatHistory.length === 0 ? (
                    <p className="muted">Start a conversation with your uploaded documents.</p>
                  ) : (
                    <div className="chat-history">
                      {chatHistory.map((item, idx) => (
                        <div key={idx} className={`chat-message ${item.role}`}>
                          <div className="message-label">{item.role === 'user' ? 'You' : 'Assistant'}</div>
                          <div className="message-text">{item.text}</div>
                          {item.sources && item.sources.length > 0 && (
                            <div className="chat-sources">
                              <strong>Sources:</strong>
                              {item.sources.map((source, sourceIdx) => (
                                <div key={sourceIdx} className="source-snippet">
                                  {source.meta?.text?.slice(0, 120) || 'No snippet available.'}
                                </div>
                              ))}
                            </div>
                          )}
                        </div>
                      ))}
                    </div>
                  )}
                </div>
                <div className="chat-input-group">
                  <textarea
                    value={chatInput}
                    onChange={(e) => setChatInput(e.target.value)}
                    rows={4}
                    placeholder="Ask a question about your documents..."
                  />
                  <button className="primary-btn" onClick={handleSendChat} disabled={chatLoading}>
                    {chatLoading ? 'Thinking…' : 'Send'}
                  </button>
                </div>
              </div>
            </div>
          </main>
        </div>
      </div>
    </div>
  );
}

export default function App() {
  const [isAuthenticated, setIsAuthenticated] = useState(Boolean(localStorage.getItem('token')));
  const navigate = useNavigate();

  useEffect(() => {
    const token = localStorage.getItem('token');
    setIsAuthenticated(Boolean(token));
  }, []);

  const handleAuthenticate = () => {
    setIsAuthenticated(true);
  };

  const handleLogout = () => {
    localStorage.removeItem('token');
    setIsAuthenticated(false);
    navigate('/');
  };

  return (
    <Routes>
      <Route path="/" element={<HomePage />} />
      <Route path="/about" element={<AboutPage />} />
      <Route path="/auth" element={<AuthPage onAuthenticate={handleAuthenticate} />} />
      <Route path="/dashboard" element={isAuthenticated ? <DashboardPage onLogout={handleLogout} /> : <Navigate to="/auth" replace />} />
    </Routes>
  );
}
