import { useState, useEffect, useRef } from 'react'
import { Send, Search, MoreVertical, X } from 'lucide-react'
import './index.css'

const BACKEND = window.sara?.backendUrl ?? 'http://localhost:8000'
const SESSION_ID = `lamda94-desktop`
const DEVICE = 'desktop'

function getTime() {
  return new Date().toLocaleTimeString('es', { hour: '2-digit', minute: '2-digit' })
}

function getDateLabel() {
  return new Date().toLocaleDateString('es', {
    weekday: 'long', month: 'long', day: 'numeric'
  }).toUpperCase()
}

function ThinkingDots() {
  return (
    <div className="bubble sara typing msg-enter">
      <div className="dot" style={{ '--d': '0ms' }} />
      <div className="dot" style={{ '--d': '150ms' }} />
      <div className="dot" style={{ '--d': '300ms' }} />
    </div>
  )
}

function MessageGroup({ msg }) {
  const isUser = msg.role === 'user'

  if (msg.typing) {
    return (
      <div className="msg-group sara msg-enter">
        <div className="msg-label">
          <span>SARA</span>
          <span className="device-tag">{msg.device}</span>
        </div>
        <ThinkingDots />
      </div>
    )
  }

  return (
    <div className={`msg-group ${isUser ? 'user' : 'sara'} msg-enter`}>
      {!isUser && (
        <div className="msg-label">
          <span>SARA</span>
          <span className="device-tag">{msg.device}</span>
        </div>
      )}
      <div className={`bubble ${isUser ? 'user' : 'sara'}`}>
        {msg.content}
      </div>
      <div className="msg-time">{msg.time}</div>
    </div>
  )
}

export default function App() {
  const [messages, setMessages] = useState([
    {
      id: 0,
      role: 'assistant',
      content: 'Hola. Soy SARA, tu asistente con memoria persistente. ¿En qué puedo ayudarte?',
      device: 'system',
      time: getTime(),
    },
  ])
  const [input, setInput] = useState('')
  const [loading, setLoading] = useState(false)
  const [sessionActive, setSessionActive] = useState(false)
  const bottomRef = useRef(null)
  const inputRef = useRef(null)

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

  useEffect(() => { inputRef.current?.focus() }, [])

  useEffect(() => {
    const handler = (e) => { if (e.key === 'Escape') window.sara?.hideWindow() }
    window.addEventListener('keydown', handler)
    return () => window.removeEventListener('keydown', handler)
  }, [])

  const sendMessage = async () => {
    const text = input.trim()
    if (!text || loading) return

    if (!sessionActive) setSessionActive(true)

    const userMsg = {
      id: Date.now(), role: 'user',
      content: text, device: DEVICE, time: getTime(),
    }
    setMessages(prev => [...prev, userMsg])
    setInput('')
    setLoading(true)

    const thinkingId = Date.now() + 1
    setMessages(prev => [...prev, {
      id: thinkingId, role: 'assistant',
      content: '', device: 'system', time: '', typing: true,
    }])

    try {
      const res = await fetch(`${BACKEND}/chat`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ message: text, session_id: SESSION_ID, device: DEVICE }),
      })
      const data = await res.json()
      setMessages(prev => prev.map(m =>
        m.id === thinkingId
          ? { ...m, content: data.response, typing: false, device: DEVICE, time: getTime() }
          : m
      ))
    } catch {
      setMessages(prev => prev.map(m =>
        m.id === thinkingId
          ? { ...m, content: 'Error al conectar con el backend.', typing: false, device: 'system', time: getTime() }
          : m
      ))
    } finally {
      setLoading(false)
      setTimeout(() => inputRef.current?.focus(), 50)
    }
  }

  const handleKey = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      sendMessage()
    }
  }

  return (
    <div className="shell">
      <div className="card">

        {/* Header */}
        <div className="header">
          <div className="header-top">
            <div className="header-title">
              SARA
              <div className={`status-dot ${sessionActive ? 'active' : ''}`} />
            </div>
            <div className="header-actions">
              <button className="icon-btn" title="Buscar">
                <Search size={13} strokeWidth={1.8} />
              </button>
              <button className="icon-btn" title="Más opciones">
                <MoreVertical size={13} strokeWidth={1.8} />
              </button>
              <button className="icon-btn close" onClick={() => window.sara?.hideWindow()} title="Cerrar">
                <X size={13} strokeWidth={1.8} />
              </button>
            </div>
          </div>
          <div className="header-sub">
            {sessionActive ? 'sesión activa · desktop' : 'en espera · desktop'}
          </div>
        </div>

        {/* Mensajes */}
        <div className="messages">
          <div className="date-sep">{getDateLabel()}</div>
          {messages.map(msg => (
            <MessageGroup key={msg.id} msg={msg} />
          ))}
          <div ref={bottomRef} />
        </div>

        {/* Input */}
        <div className="input-area">
          <div className="compose-row">
            <div className="compose-box">
              <textarea
                ref={inputRef}
                value={input}
                onChange={e => setInput(e.target.value)}
                onKeyDown={handleKey}
                placeholder="Escribe tus pensamientos..."
                rows={1}
                disabled={loading}
                className="compose-input"
                style={{ scrollbarWidth: 'none' }}
              />
              <div className="compose-actions">
                <button
                  onClick={sendMessage}
                  disabled={!input.trim() || loading}
                  className="send-btn"
                >
                  <Send size={13} strokeWidth={2} />
                </button>
              </div>
            </div>
          </div>
          <div className="hint">↵ enviar &nbsp;·&nbsp; Esc ocultar &nbsp;·&nbsp; Ctrl+Space abrir</div>
        </div>

      </div>
    </div>
  )
}
