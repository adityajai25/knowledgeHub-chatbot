import { useCallback, useEffect, useRef, useState } from 'react';
import { Link, Navigate, Route, Routes, useNavigate } from 'react-router-dom';
import axios from 'axios';
import './styles.css';

const API = import.meta.env.VITE_API_URL !== undefined ? import.meta.env.VITE_API_URL : 'http://localhost:8000';

// ─── Helpers ────────────────────────────────────────────────────────────────

function authHeaders() {
  const token = localStorage.getItem('token');
  return token ? { Authorization: `Bearer ${token}` } : {};
}

function Toast({ message, type, onClose }) {
  useEffect(() => {
    const t = setTimeout(onClose, 3500);
    return () => clearTimeout(t);
  }, [onClose]);
  return (
    <div className={`toast toast-${type}`}>
      <span>{message}</span>
      <button onClick={onClose}>✕</button>
    </div>
  );
}

function useToast() {
  const [toasts, setToasts] = useState([]);
  const push = useCallback((message, type = 'info') => {
    const id = Date.now();
    setToasts(prev => [...prev, { id, message, type }]);
  }, []);
  const remove = useCallback((id) => setToasts(prev => prev.filter(t => t.id !== id)), []);
  return { toasts, push, remove };
}

// ─── NavBar ─────────────────────────────────────────────────────────────────

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

// ─── AuthPage ────────────────────────────────────────────────────────────────

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
      const response = await axios.post(`${API}${endpoint}`, { email, password });
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
          <button className={mode === 'login' ? 'active' : ''} onClick={() => setMode('login')}>Login</button>
          <button className={mode === 'register' ? 'active' : ''} onClick={() => setMode('register')}>Register</button>
        </div>
        <form onSubmit={handleSubmit}>
          <div className="form-group">
            <label htmlFor="email">Email</label>
            <input id="email" value={email} onChange={e => setEmail(e.target.value)} placeholder="you@example.com" />
          </div>
          <div className="form-group">
            <label htmlFor="password">Password</label>
            <input id="password" type="password" value={password} onChange={e => setPassword(e.target.value)} placeholder="Enter password" />
          </div>
          <button type="submit" className="form-btn">{mode === 'login' ? 'Login' : 'Register'}</button>
          {message && <p className="form-message">{message}</p>}
        </form>
      </div>
    </div>
  );
}

// ─── HomePage ────────────────────────────────────────────────────────────────

function HomePage() {
  return (
    <div className="app-shell">
      <NavBar isAuthenticated={false} onLogout={() => {}} />
      <section className="hero">
        <div className="hero-copy">
          <h1>Turn documents into instant knowledge.</h1>
          <p>KnowledgeHub AI helps teams upload industrial documents, extract insights, search semantically, and ask questions in natural language.</p>
          <div className="hero-actions">
            <Link to="/auth" className="primary-btn">Start free</Link>
            <Link to="/about" className="secondary-btn">See how it works</Link>
          </div>
        </div>
        <div className="hero-card">
          <div className="hero-metric"><span>Documents processed</span><strong>1.2K+</strong></div>
          <div className="hero-metric"><span>Average response time</span><strong>&lt; 3s</strong></div>
          <div className="hero-metric"><span>Search accuracy</span><strong>94%</strong></div>
        </div>
      </section>
      <section className="section">
        <h2 className="section-title">Built for modern knowledge work</h2>
        <div className="feature-grid">
          <div className="card"><h3>Upload anything</h3><p>PDFs, manuals, SOPs, reports, and technical documents can be brought into one workspace.</p></div>
          <div className="card"><h3>Semantic search</h3><p>Find the right information by meaning, not just keywords, with a vector-powered search layer.</p></div>
          <div className="card"><h3>Ask questions</h3><p>Chat with your uploaded documents and get grounded answers with retrieval-augmented generation.</p></div>
        </div>
      </section>
    </div>
  );
}

// ─── AboutPage ───────────────────────────────────────────────────────────────

function AboutPage() {
  return (
    <div className="app-shell">
      <NavBar isAuthenticated={false} onLogout={() => {}} />
      <section className="section" style={{ paddingTop: '2rem' }}>
        <h2 className="section-title">How the platform works</h2>
        <div className="feature-grid">
          <div className="card"><h3>1. Ingest</h3><p>Upload your documents and store them in a secure workspace.</p></div>
          <div className="card"><h3>2. Understand</h3><p>Extract text, split it into chunks, and generate embeddings for search.</p></div>
          <div className="card"><h3>3. Interact</h3><p>Ask questions and get clever, grounded responses through the chat experience.</p></div>
        </div>
      </section>
    </div>
  );
}

// ─── DocumentPanel ───────────────────────────────────────────────────────────

function DocumentPanel({ toast }) {
  const fileInputRef = useRef(null);
  const [docs, setDocs] = useState([]);
  const [uploading, setUploading] = useState(false);
  const [expandedDoc, setExpandedDoc] = useState(null);
  const [searchQuery, setSearchQuery] = useState('');
  const [searchResults, setSearchResults] = useState([]);
  const [searchLoading, setSearchLoading] = useState(false);

  const fetchDocs = useCallback(async () => {
    try {
      const res = await axios.get(`${API}/api/docs/`, { headers: authHeaders() });
      setDocs(res.data || []);
    } catch {
      toast('Failed to load documents', 'error');
    }
  }, [toast]);

  useEffect(() => { fetchDocs(); }, [fetchDocs]);

  const handleFiles = async (e) => {
    const files = Array.from(e.target.files || []);
    if (!files.length) return;
    setUploading(true);
    const fd = new FormData();
    files.forEach(f => fd.append('files', f));
    try {
      await axios.post(`${API}/api/docs/upload`, fd, {
        headers: { 'Content-Type': 'multipart/form-data', ...authHeaders() },
      });
      toast(`${files.length} file(s) uploaded & summarized!`, 'success');
      await fetchDocs();
    } catch {
      toast('Upload failed', 'error');
    } finally {
      setUploading(false);
      e.target.value = null;
    }
  };

  const handleDelete = async (docId, filename) => {
    if (!window.confirm(`Delete "${filename}"?`)) return;
    try {
      await axios.delete(`${API}/api/docs/${docId}`, { headers: authHeaders() });
      toast(`"${filename}" deleted`, 'success');
      setDocs(prev => prev.filter(d => d.id !== docId));
    } catch {
      toast('Delete failed', 'error');
    }
  };

  const handleSearch = async () => {
    if (!searchQuery.trim()) return;
    setSearchLoading(true);
    try {
      const res = await axios.post(
        `${API}/api/docs/search`,
        { query: searchQuery.trim(), top_k: 5 },
        { headers: authHeaders() }
      );
      setSearchResults(res.data.results || []);
      if (!res.data.results?.length) toast('No results found', 'info');
    } catch {
      toast('Search failed', 'error');
    } finally {
      setSearchLoading(false);
    }
  };

  return (
    <div className="doc-panel">
      {/* Upload */}
      <div className="dashboard-card">
        <h3>📁 Upload Documents</h3>
        <div
          className="upload-dropzone"
          onClick={() => fileInputRef.current?.click()}
          onDragOver={e => e.preventDefault()}
          onDrop={async e => {
            e.preventDefault();
            const files = Array.from(e.dataTransfer.files);
            if (!files.length) return;
            setUploading(true);
            const fd = new FormData();
            files.forEach(f => fd.append('files', f));
            try {
              await axios.post(`${API}/api/docs/upload`, fd, { headers: { 'Content-Type': 'multipart/form-data', ...authHeaders() } });
              toast(`${files.length} file(s) uploaded!`, 'success');
              await fetchDocs();
            } catch { toast('Upload failed', 'error'); }
            finally { setUploading(false); }
          }}
        >
          {uploading ? (
            <div className="upload-spinner"><div className="spinner" /><span>Processing & summarizing…</span></div>
          ) : (
            <>
              <div className="upload-icon">📂</div>
              <p>Drag & drop files here or <span className="link-text">browse</span></p>
              <p className="muted" style={{ fontSize: '0.8rem' }}>PDF, TXT supported</p>
            </>
          )}
        </div>
        <input type="file" multiple ref={fileInputRef} style={{ display: 'none' }} onChange={handleFiles} accept=".pdf,.txt" />
      </div>

      {/* Document list */}
      <div className="dashboard-card">
        <h3>📄 My Documents <span className="badge">{docs.length}</span></h3>
        {docs.length === 0 ? (
          <p className="muted">No documents uploaded yet.</p>
        ) : (
          <ul className="doc-list">
            {docs.map(d => (
              <li key={d.id} className="doc-item">
                <div className="doc-item-header">
                  <div className="doc-filename">
                    <span className="doc-icon">{d.filename.endsWith('.pdf') ? '📕' : '📝'}</span>
                    <span>{d.filename}</span>
                  </div>
                  <div className="doc-actions">
                    <button
                      className="icon-btn"
                      title="Show summary"
                      onClick={() => setExpandedDoc(expandedDoc === d.id ? null : d.id)}
                    >
                      {expandedDoc === d.id ? '▲' : '▼'}
                    </button>
                    <button className="icon-btn danger" title="Delete" onClick={() => handleDelete(d.id, d.filename)}>🗑</button>
                  </div>
                </div>
                <div className="doc-meta">{new Date(d.uploaded_at).toLocaleString()}</div>
                {expandedDoc === d.id && (
                  <div className="doc-summary">
                    <strong>AI Summary:</strong>
                    <p>{d.summary || 'No summary available.'}</p>
                  </div>
                )}
              </li>
            ))}
          </ul>
        )}
      </div>

      {/* Semantic Search */}
      <div className="dashboard-card">
        <h3>🔍 Semantic Search</h3>
        <div className="search-input-group">
          <textarea
            value={searchQuery}
            onChange={e => setSearchQuery(e.target.value)}
            rows={2}
            placeholder="Search your documents by meaning…"
            onKeyDown={e => { if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); handleSearch(); } }}
          />
          <button className="secondary-btn" onClick={handleSearch} disabled={searchLoading}>
            {searchLoading ? 'Searching…' : 'Search'}
          </button>
        </div>
        {searchResults.length > 0 && (
          <div className="search-results">
            {searchResults.map((r, i) => (
              <div key={i} className="search-result-card">
                <div className="result-source">{r.meta?.filename || 'Document'}</div>
                <div className="result-snippet">{r.meta?.text || 'No snippet.'}</div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}

// ─── ChatPanel ───────────────────────────────────────────────────────────────

function ChatPanel({ toast }) {
  const [sessions, setSessions] = useState([]);
  const [activeSessionId, setActiveSessionId] = useState(null);
  const [chatHistory, setChatHistory] = useState([]);
  const [chatInput, setChatInput] = useState('');
  const [streaming, setStreaming] = useState(false);
  const [streamingText, setStreamingText] = useState('');
  const chatEndRef = useRef(null);

  const fetchSessions = useCallback(async () => {
    try {
      const res = await axios.get(`${API}/api/docs/sessions`, { headers: authHeaders() });
      setSessions(res.data || []);
    } catch { /* ignore */ }
  }, []);

  useEffect(() => { fetchSessions(); }, [fetchSessions]);

  useEffect(() => {
    chatEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [chatHistory, streamingText]);

  const loadSession = async (sessionId) => {
    try {
      const res = await axios.get(`${API}/api/docs/sessions/${sessionId}`, { headers: authHeaders() });
      setActiveSessionId(sessionId);
      setChatHistory(res.data.messages.map(m => ({
        role: m.role,
        text: m.content,
        sources: m.sources || [],
      })));
    } catch {
      toast('Failed to load session', 'error');
    }
  };

  const newChat = () => {
    setActiveSessionId(null);
    setChatHistory([]);
    setChatInput('');
    setStreamingText('');
  };

  const deleteSession = async (e, sessionId) => {
    e.stopPropagation();
    try {
      await axios.delete(`${API}/api/docs/sessions/${sessionId}`, { headers: authHeaders() });
      if (activeSessionId === sessionId) newChat();
      setSessions(prev => prev.filter(s => s.id !== sessionId));
      toast('Chat session deleted', 'success');
    } catch {
      toast('Failed to delete session', 'error');
    }
  };

  const sendMessage = async () => {
    if (!chatInput.trim() || streaming) return;
    const userText = chatInput.trim();
    setChatInput('');
    setChatHistory(prev => [...prev, { role: 'user', text: userText, sources: [] }]);
    setStreaming(true);
    setStreamingText('');

    try {
      const token = localStorage.getItem('token');
      const response = await fetch(`${API}/api/docs/chat/stream`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify({ query: userText, session_id: activeSessionId, top_k: 3 }),
      });

      if (!response.ok) throw new Error('Stream request failed');

      const reader = response.body.getReader();
      const decoder = new TextDecoder();
      let fullText = '';
      let newSessionId = activeSessionId;
      let sources = [];

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;
        const chunk = decoder.decode(value, { stream: true });
        const lines = chunk.split('\n');
        for (const line of lines) {
          if (!line.startsWith('data: ')) continue;
          const data = line.slice(6);
          if (data === '[DONE]') break;
          if (data.startsWith('__META__')) {
            try {
              const meta = JSON.parse(data.slice(8));
              newSessionId = meta.session_id;
              sources = meta.sources || [];
              if (!activeSessionId) setActiveSessionId(newSessionId);
            } catch { /* ignore */ }
            continue;
          }
          fullText += data;
          setStreamingText(fullText);
        }
      }

      setChatHistory(prev => [
        ...prev,
        { role: 'assistant', text: fullText || 'No response.', sources },
      ]);
      setStreamingText('');
      await fetchSessions();
    } catch (err) {
      setChatHistory(prev => [
        ...prev,
        { role: 'assistant', text: 'Error: ' + err.message, sources: [] },
      ]);
    } finally {
      setStreaming(false);
    }
  };

  return (
    <div className="chat-layout">
      {/* Sessions sidebar */}
      <div className="sessions-sidebar">
        <button className="new-chat-btn" onClick={newChat}>+ New Chat</button>
        <div className="sessions-list">
          {sessions.length === 0 ? (
            <p className="muted" style={{ padding: '0.75rem', fontSize: '0.85rem' }}>No past sessions</p>
          ) : (
            sessions.map(s => (
              <div
                key={s.id}
                className={`session-item ${activeSessionId === s.id ? 'active' : ''}`}
                onClick={() => loadSession(s.id)}
              >
                <div className="session-title">{s.title || 'Untitled chat'}</div>
                <div className="session-meta">{s.message_count} msgs · {new Date(s.updated_at).toLocaleDateString()}</div>
                <button className="session-delete" onClick={e => deleteSession(e, s.id)} title="Delete">✕</button>
              </div>
            ))
          )}
        </div>
      </div>

      {/* Chat window */}
      <div className="chat-main">
        <div className="chat-header">
          <h3>💬 Ask your knowledge base</h3>
          {activeSessionId && <span className="session-badge">Session #{activeSessionId}</span>}
        </div>

        <div className="chat-window">
          {chatHistory.length === 0 && !streaming ? (
            <div className="chat-empty">
              <div className="chat-empty-icon">🤖</div>
              <p>Ask anything about your uploaded documents.</p>
              <p className="muted">I'll search through them and answer with sources.</p>
            </div>
          ) : (
            <div className="chat-history">
              {chatHistory.map((item, idx) => (
                <div key={idx} className={`chat-message ${item.role}`}>
                  <div className="message-avatar">{item.role === 'user' ? '👤' : '🤖'}</div>
                  <div className="message-body">
                    <div className="message-label">{item.role === 'user' ? 'You' : 'Assistant'}</div>
                    <div className="message-text">{item.text}</div>
                    {item.sources?.length > 0 && (
                      <details className="chat-sources">
                        <summary>📎 {item.sources.length} source(s)</summary>
                        {item.sources.map((src, si) => (
                          <div key={si} className="source-snippet">
                            <span className="source-label">{src.meta?.filename || 'Doc'}</span>
                            {src.meta?.text?.slice(0, 150) || ''}…
                          </div>
                        ))}
                      </details>
                    )}
                  </div>
                </div>
              ))}
              {streaming && (
                <div className="chat-message assistant">
                  <div className="message-avatar">🤖</div>
                  <div className="message-body">
                    <div className="message-label">Assistant</div>
                    <div className="message-text streaming-text">
                      {streamingText || <span className="typing-dots"><span /><span /><span /></span>}
                      <span className="cursor-blink" />
                    </div>
                  </div>
                </div>
              )}
              <div ref={chatEndRef} />
            </div>
          )}
        </div>

        <div className="chat-input-group">
          <textarea
            value={chatInput}
            onChange={e => setChatInput(e.target.value)}
            rows={3}
            placeholder="Ask a question about your documents…"
            disabled={streaming}
            onKeyDown={e => {
              if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); sendMessage(); }
            }}
          />
          <button className="primary-btn" onClick={sendMessage} disabled={streaming || !chatInput.trim()}>
            {streaming ? <><span className="spinner-sm" /> Thinking…</> : 'Send ↑'}
          </button>
        </div>
      </div>
    </div>
  );
}

// ─── DashboardPage ───────────────────────────────────────────────────────────

function DashboardPage({ onLogout }) {
  const { toasts, push, remove } = useToast();
  const [tab, setTab] = useState('docs');

  return (
    <div className="app-shell">
      <NavBar isAuthenticated onLogout={onLogout} />

      {/* Toast container */}
      <div className="toast-container">
        {toasts.map(t => <Toast key={t.id} message={t.message} type={t.type} onClose={() => remove(t.id)} />)}
      </div>

      <div className="dashboard-page">
        <div className="dashboard-tabs">
          <button className={`tab-btn ${tab === 'docs' ? 'active' : ''}`} onClick={() => setTab('docs')}>
            📁 Documents
          </button>
          <button className={`tab-btn ${tab === 'chat' ? 'active' : ''}`} onClick={() => setTab('chat')}>
            💬 Chat
          </button>
        </div>

        {tab === 'docs' ? (
          <DocumentPanel toast={push} />
        ) : (
          <ChatPanel toast={push} />
        )}
      </div>
    </div>
  );
}

// ─── App ─────────────────────────────────────────────────────────────────────

export default function App() {
  const [isAuthenticated, setIsAuthenticated] = useState(Boolean(localStorage.getItem('token')));
  const navigate = useNavigate();

  const handleAuthenticate = () => setIsAuthenticated(true);
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
      <Route
        path="/dashboard"
        element={isAuthenticated ? <DashboardPage onLogout={handleLogout} /> : <Navigate to="/auth" replace />}
      />
    </Routes>
  );
}
