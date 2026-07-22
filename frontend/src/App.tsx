import React, { useState, useEffect, useRef } from 'react';
import { fetchEventSource } from '@microsoft/fetch-event-source';
import { motion, AnimatePresence } from 'framer-motion';
import {
  Send, Plus, MessageSquare, Shield, Activity, Key,
  Sparkles, AlertCircle, Loader2, LogOut, ChevronRight,
  Zap, Brain,
} from 'lucide-react';
import { TopologyBar } from './components/TopologyBar';
import { TraceInspector, type TraceStep } from './components/TraceInspector';
import { MarkdownRenderer } from './components/MarkdownRenderer';
import { ToolCallCard } from './components/ToolCallCard';
import { BackendStatusBanner } from './components/BackendStatusBanner';

const CONFIGURED_API_BASE_URL = (import.meta.env.VITE_API_BASE_URL || '').replace(/\/$/, '');

interface ThreadItem {
  thread_id: string;
  title: string;
}

interface ChatMessage {
  id: string;
  sender: 'user' | 'agent';
  text: string;
  toolCalls?: { name: string; args: any; result?: any }[];
}

/* ─────────────────────────────────────────────────────────────────────────── */
/* Login Page                                                                  */
/* ─────────────────────────────────────────────────────────────────────────── */
function LoginPage({
  email, setEmail, password, setPassword,
  authError, isLoggingIn, onLogin,
}: {
  email: string; setEmail: (v: string) => void;
  password: string; setPassword: (v: string) => void;
  authError: string | null; isLoggingIn: boolean;
  onLogin: () => void;
}) {
  return (
    <div style={{
      minHeight: '100vh',
      background: '#000000',
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'center',
      position: 'relative',
      overflow: 'hidden',
      padding: '1rem',
    }}>
      {/* Background watermark */}
      <div style={{
        position: 'absolute',
        top: '50%',
        left: '50%',
        transform: 'translate(-50%, -50%)',
        pointerEvents: 'none',
        userSelect: 'none',
        zIndex: 0,
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        width: '100%',
      }}>
        <span style={{
          fontFamily: "'Impact', 'Arial Black', sans-serif",
          fontSize: 'clamp(4rem, 18vw, 16rem)',
          fontWeight: 900,
          color: 'rgba(255,255,255,0.032)',
          WebkitTextStroke: '1px rgba(255, 215, 0, 0.65)',
          textShadow: '0 0 40px rgba(255, 215, 0, 0.15)',
          letterSpacing: '-0.04em',
          lineHeight: 0.85,
          textTransform: 'uppercase',
          whiteSpace: 'nowrap',
        }}>
          ORQFLOW
        </span>
      </div>

      {/* Subtle radial glow behind card */}
      <div style={{
        position: 'absolute',
        top: '50%', left: '50%',
        transform: 'translate(-50%, -50%)',
        width: 600, height: 600,
        background: 'radial-gradient(ellipse at center, rgba(139,92,246,0.08) 0%, transparent 70%)',
        pointerEvents: 'none',
        zIndex: 1,
      }} />

      {/* Login card */}
      <motion.div
        initial={{ opacity: 0, y: 24 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ type: 'spring', stiffness: 200, damping: 22 }}
        style={{
          position: 'relative',
          zIndex: 10,
          width: '100%',
          maxWidth: 420,
          background: 'rgba(17,17,21,0.88)',
          backdropFilter: 'blur(24px)',
          border: '1px solid rgba(255,255,255,0.07)',
          borderRadius: 18,
          padding: '2.25rem',
          boxShadow: '0 32px 64px -16px rgba(0,0,0,0.8), 0 0 0 1px rgba(255,255,255,0.05)',
          overflow: 'hidden',
        }}
      >
        {/* Top accent line */}
        <div style={{
          position: 'absolute',
          top: 0, left: '10%',
          width: '80%', height: 1,
          background: 'linear-gradient(90deg, transparent, #8b5cf6, #00f0ff, transparent)',
        }} />

        {/* Brand header */}
        <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', marginBottom: '1.75rem', gap: '0.6rem' }}>
          <div style={{
            width: 48, height: 48,
            background: 'rgba(139,92,246,0.12)',
            border: '1px solid rgba(139,92,246,0.3)',
            borderRadius: 12,
            display: 'flex', alignItems: 'center', justifyContent: 'center',
            boxShadow: '0 0 20px -4px rgba(139,92,246,0.5)',
          }}>
            <Brain size={22} style={{ color: '#8b5cf6' }} />
          </div>
          <div style={{ textAlign: 'center' }}>
            <h1 style={{
              fontFamily: "'Inter', sans-serif",
              fontWeight: 800,
              fontSize: '1.4rem',
              color: '#f8fafc',
              margin: 0,
              letterSpacing: '-0.02em',
            }}>
              OrqFlow Studio
            </h1>
            <p style={{
              fontFamily: "'JetBrains Mono', monospace",
              fontSize: '0.68rem',
              color: '#475569',
              margin: '0.25rem 0 0',
              letterSpacing: '0.04em',
            }}>
              Multi-Agent Orchestration · LangGraph · FastMCP
            </p>
          </div>
        </div>

        {/* Error */}
        <AnimatePresence>
          {authError && (
            <motion.div
              initial={{ opacity: 0, height: 0 }}
              animate={{ opacity: 1, height: 'auto' }}
              exit={{ opacity: 0, height: 0 }}
              style={{
                marginBottom: '1rem',
                padding: '0.6rem 0.85rem',
                borderRadius: 9,
                background: 'rgba(255,42,42,0.08)',
                border: '1px solid rgba(255,42,42,0.25)',
                color: '#fca5a5',
                fontSize: '0.78rem',
                fontFamily: "'JetBrains Mono', monospace",
                display: 'flex',
                alignItems: 'flex-start',
                gap: '0.5rem',
              }}
            >
              <AlertCircle size={13} style={{ marginTop: 1, flexShrink: 0 }} />
              {authError}
            </motion.div>
          )}
        </AnimatePresence>

        {/* Form */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: '0.85rem' }}>
          <div>
            <label style={{
              display: 'block',
              fontFamily: "'JetBrains Mono', monospace",
              fontSize: '0.65rem',
              letterSpacing: '0.08em',
              textTransform: 'uppercase',
              color: '#475569',
              marginBottom: '0.38rem',
            }}>
              Email
            </label>
            <input
              type="text"
              value={email}
              onChange={e => setEmail(e.target.value)}
              onKeyDown={e => e.key === 'Enter' && onLogin()}
              className="glass-input"
              style={{ width: '100%', padding: '0.65rem 0.9rem', fontSize: '0.875rem' }}
            />
          </div>
          <div>
            <label style={{
              display: 'block',
              fontFamily: "'JetBrains Mono', monospace",
              fontSize: '0.65rem',
              letterSpacing: '0.08em',
              textTransform: 'uppercase',
              color: '#475569',
              marginBottom: '0.38rem',
            }}>
              Password
            </label>
            <input
              type="password"
              value={password}
              onChange={e => setPassword(e.target.value)}
              onKeyDown={e => e.key === 'Enter' && onLogin()}
              className="glass-input"
              style={{ width: '100%', padding: '0.65rem 0.9rem', fontSize: '0.875rem' }}
            />
          </div>

          <motion.button
            whileHover={{ scale: 1.02, y: -1, boxShadow: '0 12px 30px -8px rgba(139,92,246,0.5)' }}
            whileTap={{ scale: 0.97 }}
            transition={{ type: 'spring', stiffness: 400, damping: 18 }}
            onClick={onLogin}
            disabled={isLoggingIn}
            style={{
              width: '100%',
              background: isLoggingIn
                ? 'rgba(139,92,246,0.35)'
                : 'linear-gradient(135deg, #7c3aed 0%, #8b5cf6 100%)',
              border: '1px solid rgba(139,92,246,0.45)',
              borderRadius: 10,
              color: '#f8fafc',
              fontFamily: "'Inter', sans-serif",
              fontWeight: 700,
              fontSize: '0.875rem',
              padding: '0.72rem',
              cursor: isLoggingIn ? 'not-allowed' : 'pointer',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              gap: '0.5rem',
              letterSpacing: '0.02em',
              marginTop: '0.25rem',
              boxShadow: '0 8px 20px -8px rgba(139,92,246,0.4)',
              transition: 'background 0.2s ease',
            }}
          >
            {isLoggingIn
              ? <Loader2 size={16} style={{ animation: 'spin 1s linear infinite' }} />
              : <Key size={15} />
            }
            {isLoggingIn ? 'Authenticating...' : 'Launch Studio'}
          </motion.button>
        </div>

        {/* Hint */}
        <p style={{
          marginTop: '1.1rem',
          fontFamily: "'JetBrains Mono', monospace",
          fontSize: '0.62rem',
          color: '#475569',
          textAlign: 'center',
          lineHeight: 1.6,
        }}>
          First launch auto-registers · credentials persist in localStorage
        </p>

        {/* Free Tier Spin-Up Notice */}
        <div style={{
          marginTop: '1rem',
          padding: '0.75rem 0.85rem',
          borderRadius: 10,
          background: 'rgba(234,179,8,0.06)',
          border: '1px solid rgba(234,179,8,0.25)',
          display: 'flex',
          alignItems: 'flex-start',
          gap: '0.55rem',
        }}>
          <span style={{ color: '#fbbf24', fontSize: '0.85rem', lineHeight: 1, marginTop: '1px' }}>*</span>
          <p style={{
            margin: 0,
            fontFamily: "'JetBrains Mono', monospace",
            fontSize: '0.65rem',
            color: '#cbd5e1',
            lineHeight: 1.5,
          }}>
            <strong style={{ color: '#fbbf24', fontWeight: 600 }}>Hosted on Free-Tier Cloud (Render):</strong> If the server has been inactive, your first sign-in may take <span style={{ color: '#38bdf8', fontWeight: 600 }}>50–60 seconds</span> while the backend wakes up. Please wait!
          </p>
        </div>
      </motion.div>
    </div>
  );
}

/* ─────────────────────────────────────────────────────────────────────────── */
/* Empty state                                                                 */
/* ─────────────────────────────────────────────────────────────────────────── */
const QUICK_PROMPTS = [
  'List all employees in the engineering department',
  'Search the web for latest LangGraph news',
  'Write and lint a Python hello-world script',
  'Show the company database schema',
];

function EmptyState({ onPrompt }: { onPrompt: (text: string) => void }) {
  return (
    <div style={{
      display: 'flex', flexDirection: 'column',
      alignItems: 'center', justifyContent: 'center',
      flex: 1, padding: '2rem', gap: '1.5rem',
    }}>
      <motion.div
        animate={{ y: [0, -8, 0] }}
        transition={{ duration: 4, repeat: Infinity, ease: 'easeInOut' }}
        style={{
          display: 'flex', alignItems: 'center', justifyContent: 'center',
          width: 64, height: 64,
          background: 'rgba(139,92,246,0.10)',
          border: '1px solid rgba(139,92,246,0.25)',
          borderRadius: 16,
          boxShadow: '0 0 30px -6px rgba(139,92,246,0.4)',
        }}
      >
        <Sparkles size={28} style={{ color: '#8b5cf6' }} />
      </motion.div>

      <div style={{ textAlign: 'center' }}>
        <div style={{ fontWeight: 700, fontSize: '0.95rem', color: '#e2e8f0', marginBottom: '0.4rem' }}>
          Multi-Agent Studio Ready
        </div>
        <p style={{
          fontFamily: "'JetBrains Mono', monospace",
          fontSize: '0.72rem', color: '#334155',
          maxWidth: 320, lineHeight: 1.7,
        }}>
          Route tasks to Researcher, Analyst, or Coder agents via the LangGraph supervisor.
        </p>
      </div>

      {/* Quick prompts */}
      <div style={{
        display: 'flex', flexWrap: 'wrap', gap: '0.55rem',
        justifyContent: 'center', maxWidth: 540,
      }}>
        {QUICK_PROMPTS.map((q, idx) => (
          <motion.button
            key={idx}
            whileHover={{ scale: 1.03, borderColor: 'rgba(139,92,246,0.45)' }}
            whileTap={{ scale: 0.97 }}
            onClick={() => onPrompt(q)}
            style={{
              background: 'rgba(255,255,255,0.03)',
              border: '1px solid rgba(255,255,255,0.08)',
              borderRadius: 8,
              color: '#94a3b8',
              fontSize: '0.75rem',
              padding: '0.42rem 0.75rem',
              cursor: 'pointer',
              fontFamily: "'Inter', sans-serif",
              display: 'flex', alignItems: 'center', gap: '0.35rem',
              transition: 'border-color 0.15s ease, color 0.15s ease',
            }}
          >
            <ChevronRight size={11} style={{ color: '#8b5cf6', flexShrink: 0 }} />
            {q}
          </motion.button>
        ))}
      </div>
      
      {/* Backend Status Poller on Login Page */}
      <BackendStatusBanner />
    </div>
  );
}

/* ─────────────────────────────────────────────────────────────────────────── */
/* Main App                                                                    */
/* ─────────────────────────────────────────────────────────────────────────── */
export default function App() {
  const [token, setToken] = useState<string | null>(localStorage.getItem('orqflow_token'));
  const [email, setEmail] = useState('test@orqflow.ai');
  const [password, setPassword] = useState('password123');
  const [authError, setAuthError] = useState<string | null>(null);
  const [isLoggingIn, setIsLoggingIn] = useState(false);

  const [threads, setThreads] = useState<ThreadItem[]>([]);
  const [activeThreadId, setActiveThreadId] = useState<string | null>(null);
  const [isCreatingThread, setIsCreatingThread] = useState(false);

  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [inputMessage, setInputMessage] = useState('');
  const [isStreaming, setIsStreaming] = useState(false);
  const [activeNode, setActiveNode] = useState<string | null>(null);
  const [nextRoute, setNextRoute] = useState<string | null>(null);
  const [currentRunId, setCurrentRunId] = useState<string | null>(null);

  const [isTraceOpen, setIsTraceOpen] = useState(false);
  const [traceData, setTraceData] = useState<TraceStep[]>([]);
  const [isLoadingTrace, setIsLoadingTrace] = useState(false);

  const messagesEndRef = useRef<HTMLDivElement>(null);
  const abortControllerRef = useRef<AbortController | null>(null);
  const watchdogTimeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, isStreaming]);

  useEffect(() => {
    if (token) loadThreads();
  }, [token]);

  function getApiBase() {
    if (CONFIGURED_API_BASE_URL) return CONFIGURED_API_BASE_URL;
    if (window.location.port === '5173') return `http://${window.location.hostname}:8000`;
    return '';
  }

  async function apiFetch(path: string, options?: RequestInit) {
    const base = getApiBase();
    return fetch(base ? `${base}${path}` : path, options);
  }

  async function handleQuickLogin() {
    setIsLoggingIn(true);
    setAuthError(null);
    try {
      const res = await apiFetch('/api/auth/login', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email, password }),
      });
      if (res.ok) {
        const data = await res.json();
        setToken(data.access_token);
        localStorage.setItem('orqflow_token', data.access_token);
        return;
      }
      // Try register
      const regRes = await apiFetch('/api/auth/register', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email, username: email.split('@')[0], password }),
      });
      if (regRes.ok) {
        const regData = await regRes.json();
        setToken(regData.access_token);
        localStorage.setItem('orqflow_token', regData.access_token);
        return;
      }
      // Final login retry
      const finalRes = await apiFetch('/api/auth/login', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email, password }),
      });
      if (finalRes.ok) {
        const data = await finalRes.json();
        setToken(data.access_token);
        localStorage.setItem('orqflow_token', data.access_token);
      } else {
        setAuthError('Authentication failed. Check credentials.');
      }
    } catch {
      setAuthError('Network error — ensure backend is running on port 8000.');
    } finally {
      setIsLoggingIn(false);
    }
  }

  function handleLogout() {
    setToken(null);
    localStorage.removeItem('orqflow_token');
    setActiveThreadId(null);
    setMessages([]);
  }

  async function loadThreads() {
    try {
      const res = await apiFetch('/api/threads', {
        headers: { Authorization: `Bearer ${token}` },
      });
      if (res.ok) {
        const data = await res.json();
        setThreads(data);
        if (data.length > 0 && !activeThreadId) setActiveThreadId(data[0].thread_id);
      } else if (res.status === 401) handleLogout();
    } catch { /* silent */ }
  }

  async function createNewThread() {
    if (!token) return;
    setIsCreatingThread(true);
    try {
      const res = await apiFetch('/api/threads', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${token}` },
        body: JSON.stringify({
          title: `Session ${new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}`,
        }),
      });
      if (res.ok) {
        const newThread = await res.json();
        setThreads(prev => [newThread, ...prev]);
        setActiveThreadId(newThread.thread_id);
        setMessages([]);
      }
    } finally {
      setIsCreatingThread(false);
    }
  }

  async function openTraceInspector() {
    if (!currentRunId || !token) return;
    setIsTraceOpen(true);
    setIsLoadingTrace(true);
    try {
      const res = await apiFetch(`/api/runs/${currentRunId}/trace`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      if (res.ok) {
        const data = await res.json();
        setTraceData(Array.isArray(data) ? data : (data.steps || []));
      }
    } finally {
      setIsLoadingTrace(false);
    }
  }

  async function handleSendMessage(e: React.FormEvent) {
    e.preventDefault();
    if (!inputMessage.trim() || !activeThreadId || isStreaming || !token) return;

    const userMsgText = inputMessage;
    setInputMessage('');
    setIsStreaming(true);
    setActiveNode('supervisor');
    setNextRoute(null);

    const userMsg: ChatMessage = { id: Date.now().toString(), sender: 'user', text: userMsgText };
    const agentMsgId = (Date.now() + 1).toString();
    const initialAgentMsg: ChatMessage = { id: agentMsgId, sender: 'agent', text: '', toolCalls: [] };
    setMessages(prev => [...prev, userMsg, initialAgentMsg]);

    const clearWatchdog = () => { if (watchdogTimeoutRef.current) clearTimeout(watchdogTimeoutRef.current); };
    const resetWatchdog = () => {
      clearWatchdog();
      // Bug 5 fix: increased from 60s to 120s to allow the full 4-model fallback
      // chain to complete (up to ~90s) without false timeout messages.
      watchdogTimeoutRef.current = setTimeout(() => {
        abortControllerRef.current?.abort();
        setIsStreaming(false);
        setActiveNode(null);
        setMessages(prev => {
          const last = prev[prev.length - 1];
          if (last?.sender === 'agent') {
            return [...prev.slice(0, -1), { ...last, text: last.text + '\n\n> ⚠️ **Stream timeout** — no response for 2 minutes. All models may be rate-limited. Please try again in a few minutes.' }];
          }
          return prev;
        });
      }, 120000);
    };

    abortControllerRef.current = new AbortController();
    resetWatchdog();

    try {
      const base = getApiBase();
      const runUrl = base ? `${base}/api/threads/${activeThreadId}/run` : `/api/threads/${activeThreadId}/run`;
      await fetchEventSource(runUrl, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${token}` },
        body: JSON.stringify({ message: userMsgText }),
        signal: abortControllerRef.current.signal,
        onopen: async res => { if (!res.ok) throw new Error(`HTTP ${res.status}`); },
        onmessage: event => {
          resetWatchdog();
          if (!event.data) return;
          try {
            const data = JSON.parse(event.data);
            if (event.event === 'node_start') {
              setActiveNode(data.node);
            } else if (event.event === 'routing') {
              setNextRoute(data.next_agent);
            } else if (event.event === 'token') {
              setMessages(prev => prev.map(m => m.id === agentMsgId ? { ...m, text: m.text + (data.token || '') } : m));
            } else if (event.event === 'responder_message') {
              setMessages(prev => prev.map(m => m.id === agentMsgId ? { ...m, text: data.text || m.text } : m));
            } else if (event.event === 'tool_call') {
              setMessages(prev => prev.map(m => {
                if (m.id !== agentMsgId) return m;
                return { ...m, toolCalls: [...(m.toolCalls || []), { name: data.tool_name, args: data.args }] };
              }));
            } else if (event.event === 'tool_result') {
              setMessages(prev => prev.map(m => {
                if (m.id !== agentMsgId || !m.toolCalls) return m;
                const updated = m.toolCalls.map(tc =>
                  tc.name === data.tool_name && !tc.result ? { ...tc, result: data.result } : tc
                );
                return { ...m, toolCalls: updated };
              }));
            } else if (event.event === 'run_complete' || event.event === 'done') {
              clearWatchdog();
              setCurrentRunId(data.run_id);
              setIsStreaming(false);
              setActiveNode(null);
              setNextRoute(null);
            } else if (event.event === 'error') {
              // Bug 6 fix: display error message in agent bubble instead of leaving it empty
              clearWatchdog();
              setIsStreaming(false);
              setActiveNode(null);
              setNextRoute(null);
              const errorText = data.message || 'An unexpected error occurred. Please try again.';
              setMessages(prev => prev.map(m =>
                m.id === agentMsgId
                  ? { ...m, text: m.text ? m.text + '\n\n' + errorText : errorText }
                  : m
              ));
            } else if (event.event === 'model_switch') {
              // Bug 7 fix: show inline notice when models switch due to rate limits
              const notice = `\n> ⚡ **Model Switch:** \`${data.from_model}\` rate-limited → switching to \`${data.to_model}\`...\n`;
              setMessages(prev => prev.map(m =>
                m.id === agentMsgId
                  ? { ...m, text: m.text + notice }
                  : m
              ));
            }
          } catch (err) {
            console.error('SSE parse error', err);
          }
        },
        onerror: err => {
          clearWatchdog();
          setIsStreaming(false);
          setActiveNode(null);
          throw err;
        },
        onclose: () => clearWatchdog(),
      });
    } catch {
      clearWatchdog();
      setIsStreaming(false);
      setActiveNode(null);
    }
  }

  function handleQuickPrompt(text: string) {
    setInputMessage(text);
    setTimeout(() => inputRef.current?.focus(), 50);
  }

  // ── Login gate ──────────────────────────────────────────────────────────────
  if (!token) {
    return (
      <LoginPage
        email={email} setEmail={setEmail}
        password={password} setPassword={setPassword}
        authError={authError}
        isLoggingIn={isLoggingIn}
        onLogin={handleQuickLogin}
      />
    );
  }

  // ── Main App ────────────────────────────────────────────────────────────────
  return (
    <div style={{
      minHeight: '100vh',
      background: '#000000',
      display: 'flex',
      fontFamily: "'Inter', system-ui, sans-serif",
    }}>
      {/* ── Sidebar ────────────────────────────────────────────────────────── */}
      <div style={{
        width: 256,
        flexShrink: 0,
        display: 'flex',
        flexDirection: 'column',
        background: '#0a0a0a',
        borderRight: '1px solid rgba(255,255,255,0.06)',
        height: '100vh',
        position: 'sticky',
        top: 0,
        overflowY: 'auto',
      }}>
        {/* Brand */}
        <div style={{
          padding: '1rem 1rem 0.75rem',
          borderBottom: '1px solid rgba(255,255,255,0.05)',
        }}>
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '0.85rem' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
              <div style={{
                width: 28, height: 28,
                background: 'rgba(139,92,246,0.15)',
                border: '1px solid rgba(139,92,246,0.3)',
                borderRadius: 7,
                display: 'flex', alignItems: 'center', justifyContent: 'center',
                boxShadow: '0 0 12px -3px rgba(139,92,246,0.45)',
              }}>
                <Shield size={14} style={{ color: '#8b5cf6' }} />
              </div>
              <span style={{ fontWeight: 800, fontSize: '0.95rem', color: '#f8fafc', letterSpacing: '-0.01em' }}>
                OrqFlow
              </span>
            </div>
            <button
              onClick={handleLogout}
              title="Logout"
              style={{
                background: 'transparent',
                border: '1px solid rgba(255,255,255,0.06)',
                borderRadius: 6,
                cursor: 'pointer',
                color: '#334155',
                display: 'flex', alignItems: 'center', justifyContent: 'center',
                padding: '0.28rem',
                transition: 'color 0.15s ease, border-color 0.15s ease',
              }}
              onMouseEnter={e => {
                (e.currentTarget as HTMLButtonElement).style.color = '#fca5a5';
                (e.currentTarget as HTMLButtonElement).style.borderColor = 'rgba(255,42,42,0.30)';
              }}
              onMouseLeave={e => {
                (e.currentTarget as HTMLButtonElement).style.color = '#334155';
                (e.currentTarget as HTMLButtonElement).style.borderColor = 'rgba(255,255,255,0.06)';
              }}
            >
              <LogOut size={13} />
            </button>
          </div>

          {/* New Session button */}
          <motion.button
            whileHover={{ scale: 1.02 }}
            whileTap={{ scale: 0.97 }}
            onClick={createNewThread}
            disabled={isCreatingThread}
            style={{
              width: '100%',
              background: 'rgba(139,92,246,0.08)',
              border: '1px solid rgba(139,92,246,0.25)',
              borderRadius: 9,
              color: '#a78bfa',
              fontFamily: "'Inter', sans-serif",
              fontWeight: 600,
              fontSize: '0.8rem',
              padding: '0.52rem',
              cursor: isCreatingThread ? 'not-allowed' : 'pointer',
              display: 'flex', alignItems: 'center', justifyContent: 'center', gap: '0.4rem',
              transition: 'background 0.15s ease, border-color 0.15s ease',
              opacity: isCreatingThread ? 0.6 : 1,
            }}
            onMouseEnter={e => {
              if (!isCreatingThread) {
                (e.currentTarget as HTMLButtonElement).style.background = 'rgba(139,92,246,0.14)';
              }
            }}
            onMouseLeave={e => {
              (e.currentTarget as HTMLButtonElement).style.background = 'rgba(139,92,246,0.08)';
            }}
          >
            {isCreatingThread ? <Loader2 size={13} style={{ animation: 'spin 1s linear infinite' }} /> : <Plus size={13} />}
            New Session
          </motion.button>
        </div>

        {/* Thread list */}
        <div style={{ flex: 1, padding: '0.6rem 0.75rem', overflowY: 'auto' }}>
          <div style={{
            fontFamily: "'JetBrains Mono', monospace",
            fontSize: '0.6rem',
            letterSpacing: '0.1em',
            textTransform: 'uppercase',
            color: '#1e293b',
            padding: '0.3rem 0.25rem 0.5rem',
            fontWeight: 600,
          }}>
            Sessions
          </div>

          {threads.length === 0 ? (
            <div style={{
              padding: '1rem 0.25rem',
              fontFamily: "'JetBrains Mono', monospace",
              fontSize: '0.67rem',
              color: '#1e293b',
              textAlign: 'center',
            }}>
              No sessions yet
            </div>
          ) : (
            threads.map(t => {
              const isActive = activeThreadId === t.thread_id;
              return (
                <motion.button
                  key={t.thread_id}
                  whileHover={!isActive ? { x: 2 } : {}}
                  onClick={() => { setActiveThreadId(t.thread_id); setMessages([]); }}
                  style={{
                    width: '100%',
                    background: isActive ? 'rgba(139,92,246,0.10)' : 'transparent',
                    border: `1px solid ${isActive ? 'rgba(139,92,246,0.30)' : 'transparent'}`,
                    borderRadius: 8,
                    color: isActive ? '#e2e8f0' : '#334155',
                    textAlign: 'left',
                    padding: '0.45rem 0.6rem',
                    cursor: 'pointer',
                    display: 'flex', alignItems: 'center', gap: '0.45rem',
                    marginBottom: '0.2rem',
                    fontSize: '0.78rem',
                    fontFamily: "'Inter', sans-serif",
                    boxShadow: isActive ? '0 0 16px -5px rgba(139,92,246,0.4)' : 'none',
                    transition: 'background 0.15s ease, border-color 0.15s ease, color 0.15s ease, box-shadow 0.15s ease',
                  }}
                >
                  {isActive
                    ? <div style={{ width: 6, height: 6, borderRadius: '50%', background: '#8b5cf6', flexShrink: 0, boxShadow: '0 0 6px 1px rgba(139,92,246,0.7)' }} />
                    : <MessageSquare size={11} style={{ flexShrink: 0 }} />
                  }
                  <span style={{
                    overflow: 'hidden',
                    textOverflow: 'ellipsis',
                    whiteSpace: 'nowrap',
                    fontSize: '0.78rem',
                  }}>
                    {t.title || 'Untitled Session'}
                  </span>
                </motion.button>
              );
            })
          )}
        </div>

        {/* Sidebar footer badge */}
        <div style={{
          padding: '0.65rem 0.85rem',
          borderTop: '1px solid rgba(255,255,255,0.04)',
          display: 'flex', alignItems: 'center', gap: '0.4rem',
        }}>
          <span style={{ position: 'relative', display: 'flex', width: 7, height: 7 }}>
            <span style={{
              position: 'absolute', inset: 0, borderRadius: '50%',
              background: '#10b981',
              animation: 'ping 1.5s cubic-bezier(0,0,0.2,1) infinite',
              opacity: 0.6,
            }} />
            <span style={{
              position: 'relative', width: 7, height: 7,
              borderRadius: '50%', background: '#10b981',
            }} />
          </span>
          <span style={{
            fontFamily: "'JetBrains Mono', monospace",
            fontSize: '0.6rem',
            color: '#10b981',
            letterSpacing: '0.06em',
            textTransform: 'uppercase',
          }}>
            System Online
          </span>
        </div>
      </div>

      {/* ── Main Arena ─────────────────────────────────────────────────────── */}
      <div style={{
        flex: 1,
        display: 'flex',
        flexDirection: 'column',
        height: '100vh',
        overflow: 'hidden',
        minWidth: 0,
      }}>
        {/* Header bar */}
        <div style={{
          height: 52,
          borderBottom: '1px solid rgba(255,255,255,0.05)',
          background: 'rgba(10,10,10,0.85)',
          backdropFilter: 'blur(12px)',
          padding: '0 1.25rem',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          flexShrink: 0,
        }}>
          <div style={{
            display: 'flex', alignItems: 'center', gap: '0.5rem',
            fontFamily: "'JetBrains Mono', monospace",
          }}>
            <span style={{ fontSize: '0.65rem', color: '#334155' }}>session:</span>
            <span style={{
              fontSize: '0.65rem', color: '#8b5cf6',
              background: 'rgba(139,92,246,0.08)',
              border: '1px solid rgba(139,92,246,0.18)',
              padding: '0.15rem 0.5rem', borderRadius: 5,
            }}>
              {activeThreadId ? activeThreadId.slice(0, 8) + '…' : 'none'}
            </span>
          </div>

          <div style={{ display: 'flex', alignItems: 'center', gap: '0.6rem' }}>
            {currentRunId && (
              <motion.button
                whileHover={{ scale: 1.04 }}
                whileTap={{ scale: 0.96 }}
                onClick={openTraceInspector}
                style={{
                  background: 'rgba(139,92,246,0.08)',
                  border: '1px solid rgba(139,92,246,0.25)',
                  borderRadius: 8,
                  color: '#a78bfa',
                  fontFamily: "'JetBrains Mono', monospace",
                  fontSize: '0.65rem',
                  letterSpacing: '0.04em',
                  padding: '0.3rem 0.7rem',
                  cursor: 'pointer',
                  display: 'flex', alignItems: 'center', gap: '0.35rem',
                  transition: 'background 0.15s ease',
                }}
              >
                <Activity size={11} />
                Inspect Trace
              </motion.button>
            )}

            {isStreaming && (
              <div style={{ display: 'flex', alignItems: 'center', gap: '0.35rem' }}>
                <Zap size={11} style={{ color: '#f59e0b', animation: 'glow-pulse 1.2s ease infinite' }} />
                <span style={{
                  fontFamily: "'JetBrains Mono', monospace",
                  fontSize: '0.62rem',
                  color: '#f59e0b',
                  letterSpacing: '0.06em',
                }}>
                  STREAMING
                </span>
              </div>
            )}
          </div>
        </div>

        {/* Fixed Topology Bar */}
        <div style={{ padding: '1rem 1.25rem 0.5rem 1.25rem', flexShrink: 0, zIndex: 10 }}>
          <TopologyBar activeNode={activeNode} nextRoute={nextRoute} />
        </div>

        {/* Message area */}
        <div style={{
          flex: 1,
          overflowY: 'auto',
          padding: '0.5rem 1.25rem 1.25rem 1.25rem',
          display: 'flex',
          flexDirection: 'column',
        }}>

          {messages.length === 0 ? (
            <EmptyState onPrompt={handleQuickPrompt} />
          ) : (
            <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
              <AnimatePresence initial={false}>
                {messages.map(msg => (
                  <motion.div
                    key={msg.id}
                    initial={{ opacity: 0, y: 10 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ type: 'spring', stiffness: 280, damping: 24 }}
                    style={{
                      display: 'flex',
                      flexDirection: 'column',
                      alignItems: msg.sender === 'user' ? 'flex-end' : 'flex-start',
                    }}
                  >
                    {/* Role label */}
                    <div style={{
                      fontFamily: "'JetBrains Mono', monospace",
                      fontSize: '0.6rem',
                      letterSpacing: '0.08em',
                      textTransform: 'uppercase',
                      color: msg.sender === 'user' ? '#475569' : '#334155',
                      marginBottom: '0.3rem',
                      paddingLeft: msg.sender === 'agent' ? '0.25rem' : 0,
                      paddingRight: msg.sender === 'user' ? '0.25rem' : 0,
                    }}>
                      {msg.sender === 'user' ? 'You' : 'OrqFlow Agent'}
                    </div>

                    <div style={{
                      maxWidth: 'min(680px, 92%)',
                      padding: msg.sender === 'user' ? '0.65rem 1rem' : '0.85rem 1rem',
                      borderRadius: msg.sender === 'user' ? '14px 14px 4px 14px' : '14px 14px 14px 4px',
                      background: msg.sender === 'user'
                        ? 'linear-gradient(135deg, #6d28d9 0%, #7c3aed 60%, #8b5cf6 100%)'
                        : 'rgba(17,17,21,0.85)',
                      border: msg.sender === 'user'
                        ? '1px solid rgba(139,92,246,0.4)'
                        : '1px solid rgba(0,240,255,0.10)',
                      borderTopColor: msg.sender === 'agent' ? 'rgba(0,240,255,0.22)' : undefined,
                      boxShadow: msg.sender === 'user'
                        ? '0 6px 20px -6px rgba(139,92,246,0.45)'
                        : '0 4px 16px -6px rgba(0,0,0,0.5)',
                      backdropFilter: msg.sender === 'agent' ? 'blur(16px)' : undefined,
                    }}>
                      {/* Tool calls */}
                      {msg.toolCalls && msg.toolCalls.length > 0 && (
                        <div style={{ marginBottom: '0.65rem', borderBottom: '1px solid rgba(255,255,255,0.05)', paddingBottom: '0.65rem' }}>
                          {msg.toolCalls.map((tc, idx) => (
                            <ToolCallCard
                              key={idx}
                              toolCall={tc}
                              isRunning={isStreaming && !tc.result}
                            />
                          ))}
                        </div>
                      )}

                      {/* Text / Markdown */}
                      {msg.sender === 'user' ? (
                        <span style={{
                          fontSize: '0.875rem',
                          lineHeight: 1.6,
                          color: '#f0e9ff',
                        }}>
                          {msg.text}
                        </span>
                      ) : (
                        <div>
                          {msg.text ? (
                            <MarkdownRenderer content={msg.text} />
                          ) : (
                            isStreaming && (
                              <span style={{
                                fontFamily: "'JetBrains Mono', monospace",
                                fontSize: '0.78rem',
                                color: '#334155',
                                fontStyle: 'italic',
                              }}>
                                orchestrating agents
                                <span className="streaming-cursor" />
                              </span>
                            )
                          )}
                          {/* Streaming cursor on non-empty text */}
                          {isStreaming && msg.text && (
                            <span className="streaming-cursor" />
                          )}
                        </div>
                      )}
                    </div>
                  </motion.div>
                ))}
              </AnimatePresence>
              <div ref={messagesEndRef} />
            </div>
          )}
        </div>

        {/* Input bar */}
        <div style={{
          padding: '0.85rem 1.25rem',
          borderTop: '1px solid rgba(255,255,255,0.05)',
          background: 'rgba(10,10,10,0.90)',
          backdropFilter: 'blur(12px)',
          flexShrink: 0,
        }}>
          <form
            onSubmit={handleSendMessage}
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: '0.65rem',
              maxWidth: 800,
              margin: '0 auto',
            }}
          >
            <input
              ref={inputRef}
              type="text"
              value={inputMessage}
              onChange={e => setInputMessage(e.target.value)}
              placeholder={
                !activeThreadId
                  ? 'Select or create a session first…'
                  : isStreaming
                    ? 'Agents executing — please wait…'
                    : 'Message OrqFlow Supervisor…'
              }
              disabled={isStreaming || !activeThreadId}
              className="glass-input"
              style={{
                flex: 1,
                padding: '0.72rem 1rem',
                fontSize: '0.875rem',
              }}
            />

            <motion.button
              type="submit"
              whileHover={!isStreaming && !!activeThreadId && !!inputMessage.trim()
                ? { scale: 1.05, boxShadow: '0 8px 24px -6px rgba(0,240,255,0.45)' }
                : {}}
              whileTap={{ scale: 0.95 }}
              disabled={isStreaming || !activeThreadId || !inputMessage.trim()}
              style={{
                background: isStreaming || !activeThreadId || !inputMessage.trim()
                  ? 'rgba(255,255,255,0.05)'
                  : 'linear-gradient(135deg, #06b6d4 0%, #00f0ff 100%)',
                border: '1px solid rgba(0,240,255,0.25)',
                borderRadius: 10,
                color: isStreaming || !activeThreadId || !inputMessage.trim() ? '#334155' : '#000000',
                cursor: isStreaming || !activeThreadId || !inputMessage.trim() ? 'not-allowed' : 'pointer',
                padding: '0.72rem 1.1rem',
                display: 'flex', alignItems: 'center', gap: '0.4rem',
                fontFamily: "'Inter', sans-serif",
                fontWeight: 700,
                fontSize: '0.82rem',
                flexShrink: 0,
                transition: 'background 0.2s ease, border-color 0.2s ease, color 0.2s ease',
                boxShadow: isStreaming || !activeThreadId || !inputMessage.trim()
                  ? 'none'
                  : '0 4px 14px -4px rgba(0,240,255,0.35)',
              }}
            >
              {isStreaming
                ? <Loader2 size={15} style={{ animation: 'spin 1s linear infinite' }} />
                : <Send size={14} />
              }
              Send
            </motion.button>
          </form>

          <div style={{
            marginTop: '0.4rem',
            textAlign: 'center',
            fontFamily: "'JetBrains Mono', monospace",
            fontSize: '0.58rem',
            color: '#1e293b',
          }}>
            ↵ Enter to send · multi-agent LangGraph supervisor routes your request
          </div>
        </div>
      </div>

      {/* Trace Inspector */}
      <TraceInspector
        isOpen={isTraceOpen}
        onClose={() => setIsTraceOpen(false)}
        runId={currentRunId}
        trace={traceData}
        loading={isLoadingTrace}
      />
      
      {/* Backend Status Poller */}
      <BackendStatusBanner />
    </div>
  );
}
