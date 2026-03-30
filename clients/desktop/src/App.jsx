import { useState, useEffect, useRef, useCallback } from 'react'
import { Send, Search, MoreVertical, X, Mic, MicOff } from 'lucide-react'
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
  const [isListening, setIsListening] = useState(false)
  const [voiceEnabled, setVoiceEnabled] = useState(true)
  const bottomRef = useRef(null)
  const inputRef = useRef(null)
  const recognitionRef = useRef(null)
  const synthRef = useRef(window.speechSynthesis)

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

  useEffect(() => { inputRef.current?.focus() }, [])

  useEffect(() => {
    const handler = (e) => {
      if (e.key === 'Escape') window.sara?.hideWindow()
      if (e.ctrlKey && e.key === 'm') { e.preventDefault(); toggleListen() }
    }
    window.addEventListener('keydown', handler)
    return () => window.removeEventListener('keydown', handler)
  }, [])

  // Inicializar SpeechRecognition
  useEffect(() => {
    const SR = window.SpeechRecognition || window.webkitSpeechRecognition
    if (!SR) return
    const rec = new SR()
    rec.lang = 'es-ES'
    rec.continuous = false
    rec.interimResults = false
    rec.onresult = (e) => {
      const transcript = e.results[0][0].transcript
      setInput(transcript)
      setIsListening(false)
    }
    rec.onerror = () => setIsListening(false)
    rec.onend = () => setIsListening(false)
    recognitionRef.current = rec
  }, [])

  const toggleListen = useCallback(() => {
    if (!recognitionRef.current) return
    if (isListening) {
      recognitionRef.current.stop()
      setIsListening(false)
    } else {
      synthRef.current?.cancel()
      recognitionRef.current.start()
      setIsListening(true)
    }
  }, [isListening])

  const speak = useCallback((text) => {
    if (!voiceEnabled || !synthRef.current) return
    synthRef.current.cancel()
    const utt = new SpeechSynthesisUtterance(text)
    utt.lang = 'es-ES'
    utt.rate = 1.05
    utt.pitch = 1.0
    // Preferir voz femenina en español si está disponible
    const voices = synthRef.current.getVoices()
    const esVoice = voices.find(v => v.lang.startsWith('es') && v.name.toLowerCase().includes('female'))
      || voices.find(v => v.lang.startsWith('es'))
    if (esVoice) utt.voice = esVoice
    synthRef.current.speak(utt)
  }, [voiceEnabled])

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
      speak(data.response)
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
              <button
                className={`icon-btn${voiceEnabled ? ' active' : ''}`}
                title={voiceEnabled ? 'Voz activa (click para silenciar)' : 'Voz silenciada'}
                onClick={() => { setVoiceEnabled(v => !v); synthRef.current?.cancel() }}
              >
                {voiceEnabled ? <Mic size={13} strokeWidth={1.8} /> : <MicOff size={13} strokeWidth={1.8} />}
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
                  onMouseDown={toggleListen}
                  className={`send-btn mic-btn${isListening ? ' listening' : ''}`}
                  title="Hablar (Ctrl+M)"
                  style={{ marginRight: 4 }}
                >
                  <Mic size={12} strokeWidth={2} />
                </button>
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
          <div className="hint">↵ enviar &nbsp;·&nbsp; Ctrl+M voz &nbsp;·&nbsp; Esc ocultar</div>
        </div>

      </div>
    </div>
  )
}
