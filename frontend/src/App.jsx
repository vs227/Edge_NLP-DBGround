import React, { useState, useEffect, useRef } from 'react'
import {
  LineChart,
  Line,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
  CartesianGrid
} from 'recharts'

const DEFAULT_API_URL = 'http://10.84.56.228:8000'

const SUGGESTIONS = [
  "Which machine has the highest temperature?",
  "What was the average temperature of M02 in the last 30 minutes?",
  "Which machine produced the most units today?",
  "Show machines above 80 degrees",
  "Which machines are currently under maintenance?",
  "Compare production M01 vs M02",
  "When was M05 last maintained?",
  "Temperature trend M02"
]

export default function App() {
  const [apiUrl] = useState(DEFAULT_API_URL)
  const [connected, setConnected] = useState(false)
  const [inputQuery, setInputQuery] = useState('')
  const [loading, setLoading] = useState(false)
  const [showERModal, setShowERModal] = useState(false)
  const [isClosingModal, setIsClosingModal] = useState(false)
  const [messages, setMessages] = useState([])
  const chatBottomRef = useRef(null)
  const inputRef = useRef(null)

  // ER Diagram refs
  const canvasRef = useRef(null)
  const sourcePinRef = useRef(null)
  const sensorPinRef = useRef(null)
  const prodPinRef = useRef(null)
  const maintPinRef = useRef(null)
  const [connectorPaths, setConnectorPaths] = useState([])

  useEffect(() => {
    const checkStatus = async () => {
      try {
        const res = await fetch(`${apiUrl}/health`, { signal: AbortSignal.timeout(3000) })
        setConnected(res.ok)
      } catch {
        setConnected(false)
      }
    }
    checkStatus()
    const timer = setInterval(checkStatus, 5000)
    return () => clearInterval(timer)
  }, [apiUrl])

  useEffect(() => {
    chatBottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages, loading])

  const handleCloseModal = () => {
    setIsClosingModal(true)
    setTimeout(() => {
      setShowERModal(false)
      setIsClosingModal(false)
    }, 220)
  }

  useEffect(() => {
    const handleKey = (e) => {
      if (e.key === 'Escape' && showERModal) handleCloseModal()
    }
    window.addEventListener('keydown', handleKey)
    return () => window.removeEventListener('keydown', handleKey)
  }, [showERModal])

  const updateConnectors = () => {
    if (!canvasRef.current || !sourcePinRef.current) return
    const canvasRect = canvasRef.current.getBoundingClientRect()
    const srcRect = sourcePinRef.current.getBoundingClientRect()

    const x1 = srcRect.left - canvasRect.left + srcRect.width / 2
    const y1 = srcRect.bottom - canvasRect.top

    const targets = [sensorPinRef.current, prodPinRef.current, maintPinRef.current]
    const paths = []

    targets.forEach((target) => {
      if (!target) return
      const tRect = target.getBoundingClientRect()
      const x2 = tRect.left - canvasRect.left + tRect.width / 2
      const y2 = tRect.top - canvasRect.top

      const dy = (y2 - y1) * 0.55
      const d = `M ${x1} ${y1} C ${x1} ${y1 + dy}, ${x2} ${y2 - dy}, ${x2} ${y2}`
      paths.push({ d, x1, y1, x2, y2 })
    })

    setConnectorPaths(paths)
  }

  useEffect(() => {
    if (showERModal) {
      const timer = setTimeout(updateConnectors, 50)
      window.addEventListener('resize', updateConnectors)
      return () => {
        clearTimeout(timer)
        window.removeEventListener('resize', updateConnectors)
      }
    }
  }, [showERModal])

  const handleSend = async (queryToSend = inputQuery) => {
    const q = queryToSend.trim()
    if (!q || loading) return

    setInputQuery('')
    const userMessage = {
      id: Date.now(),
      sender: 'user',
      text: q
    }
    setMessages(prev => [...prev, userMessage])
    setLoading(true)

    try {
      const res = await fetch(`${apiUrl}/query`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ query: q })
      })

      if (!res.ok) {
        throw new Error(`Edge device returned HTTP ${res.status}`)
      }

      const data = await res.json()

      let chartData = null
      if (data.chart_type === 'line' && data.details?.points?.length > 0) {
        chartData = {
          type: 'line',
          title: `Trend: ${data.details.machine_id} (${data.details.machine_name || ''})`,
          points: data.details.points.map(p => ({
            time: p.timestamp ? p.timestamp.split(' ')[1] : '',
            val: p.val
          }))
        }
      } else if (data.chart_type === 'bar' && data.details?.comparison?.length > 0) {
        chartData = {
          type: 'bar',
          title: 'Comparison',
          items: data.details.comparison.map(c => ({
            name: c.machine_id,
            val: c.units_produced !== undefined ? c.units_produced : c.avg_val
          }))
        }
      }

      const botMessage = {
        id: Date.now() + 1,
        sender: 'bot',
        text: data.answer || 'Query completed.',
        metadata: {
          nlp: data.nlp_latency_ms,
          sql: data.sql_latency_ms,
          total: data.latency_ms
        },
        chart: chartData
      }

      setMessages(prev => [...prev, botMessage])
    } catch (err) {
      setMessages(prev => [
        ...prev,
        {
          id: Date.now() + 1,
          sender: 'bot',
          text: `Connection error: ${err.message}. Make sure the Redmi Y2 server is running at ${apiUrl}.`,
          metadata: null
        }
      ])
    } finally {
      setLoading(false)
      setTimeout(() => {
        inputRef.current?.focus()
      }, 50)
    }
  }

  const handleKeyDown = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      handleSend()
    }
  }

  return (
    <div className="app-container">
      {/* Header */}
      <header className="header">
        <div className="header-left">
          <div className="brand-title" onClick={() => setMessages([])} role="button" title="Start new session">
            Edge AI
          </div>
        </div>

        <div className="header-right">
          <div className="status-pill">
            <span className="status-text">
              {connected ? 'Edge Device connected' : 'Edge Device disconnected'}
            </span>
          </div>

          <button
            className="relationships-btn"
            onClick={() => setShowERModal(true)}
            title="View Database Relationships"
          >
            Database Relationships
          </button>
        </div>
      </header>

      {/* Main Chat View */}
      <main className="chat-main">
        {messages.length === 0 ? (
          <div className="empty-state">
            <div className="empty-tagline">Ask questions about operational data, sensors, production, and maintenance</div>

            <div className="suggestions-grid">
              {SUGGESTIONS.map((s, idx) => (
                <button
                  key={idx}
                  className="suggestion-pill"
                  onClick={() => handleSend(s)}
                >
                  {s}
                </button>
              ))}
            </div>
          </div>
        ) : (
          <div className="messages-container">
            {messages.map(m => (
              <div
                key={m.id}
                className={`message-wrapper ${m.sender === 'user' ? 'message-user' : 'message-bot'}`}
              >
                {m.sender === 'bot' && (
                  <div className="message-author">EdgeNLP</div>
                )}

                <div className="message-content">
                  <div className="message-text">{m.text}</div>

                  {/* Inline Chart */}
                  {m.chart && m.chart.type === 'line' && (
                    <div className="chart-box">
                      <div className="chart-title">{m.chart.title}</div>
                      <ResponsiveContainer width="100%" height={180}>
                        <LineChart data={m.chart.points}>
                          <CartesianGrid strokeDasharray="3 3" stroke="#222222" />
                          <XAxis dataKey="time" tick={{ fontSize: 10, fill: '#777777' }} stroke="#333333" />
                          <YAxis domain={['auto', 'auto']} unit="°C" tick={{ fontSize: 10, fill: '#777777' }} stroke="#333333" />
                          <Tooltip contentStyle={{ backgroundColor: '#0a0a0a', border: '1px solid #2a2a2a', borderRadius: '4px', color: '#eeeeee' }} />
                          <Line type="monotone" dataKey="val" stroke="#e5e5e5" strokeWidth={1.5} dot={false} />
                        </LineChart>
                      </ResponsiveContainer>
                    </div>
                  )}

                  {m.chart && m.chart.type === 'bar' && (
                    <div className="chart-box">
                      <div className="chart-title">{m.chart.title}</div>
                      <ResponsiveContainer width="100%" height={170}>
                        <BarChart data={m.chart.items}>
                          <CartesianGrid strokeDasharray="3 3" stroke="#222222" />
                          <XAxis dataKey="name" tick={{ fontSize: 11, fill: '#777777' }} stroke="#333333" />
                          <YAxis tick={{ fontSize: 11, fill: '#777777' }} stroke="#333333" />
                          <Tooltip contentStyle={{ backgroundColor: '#0a0a0a', border: '1px solid #2a2a2a', borderRadius: '4px', color: '#eeeeee' }} />
                          <Bar dataKey="val" fill="#d4d4d4" />
                        </BarChart>
                      </ResponsiveContainer>
                    </div>
                  )}


                </div>
              </div>
            ))}

            {loading && (
              <div className="message-wrapper message-bot">
                <div className="message-author">EdgeNLP</div>
                <div className="message-content loading-content">
                  <span className="dot-pulse"></span>
                  <span className="dot-pulse"></span>
                  <span className="dot-pulse"></span>
                </div>
              </div>
            )}

            <div ref={chatBottomRef} />
          </div>
        )}
      </main>

      {/* Floating Bottom Input */}
      <footer className="footer-dock">
        <div className="input-container">
          <input
            ref={inputRef}
            type="text"
            className="query-input"
            placeholder="Ask about machines, production, sensors, or maintenance..."
            value={inputQuery}
            onChange={(e) => setInputQuery(e.target.value)}
            onKeyDown={handleKeyDown}
            disabled={loading}
            autoFocus
          />
          <button
            className="send-button"
            onClick={() => handleSend()}
            disabled={loading || !inputQuery.trim()}
            title="Send query"
          >
            &#x27A4;
          </button>
        </div>
      </footer>

      {/* Database Relationships Modal (Monochrome Schema Editor) */}
      {showERModal && (
        <div
          className={`modal-backdrop ${isClosingModal ? 'closing' : ''}`}
          onClick={handleCloseModal}
        >
          <div
            className={`modal-window ${isClosingModal ? 'closing' : ''}`}
            onClick={(e) => e.stopPropagation()}
          >
            <div className="modal-top">
              <div className="modal-title-left">
                <span className="schema-badge">SQLite Schema</span>
              </div>
              <button
                className="modal-x-btn"
                onClick={handleCloseModal}
                title="Close"
              >
                &times;
              </button>
            </div>

            {/* Non-scrollable Diagram Canvas */}
            <div className="diagram-canvas" ref={canvasRef}>
              <svg className="connector-svg">
                {connectorPaths.map((p, i) => (
                  <g key={i}>
                    <path
                      d={p.d}
                      fill="none"
                      stroke="#666666"
                      strokeWidth="1.5"
                    />
                    <circle cx={p.x1} cy={p.y1} r="3" fill="#888888" />
                    <circle cx={p.x2} cy={p.y2} r="3" fill="#888888" />
                  </g>
                ))}
              </svg>

              {/* Top Row: Parent Table (machines) */}
              <div className="canvas-row-top">
                <div className="schema-card card-parent">
                  <div className="card-top-bar">
                    <div className="card-title-group">
                      <span className="icon-table">
                        <svg width="12" height="12" viewBox="0 0 16 16" fill="currentColor">
                          <path d="M1 2.5A1.5 1.5 0 0 1 2.5 1h11A1.5 1.5 0 0 1 15 2.5v11a1.5 1.5 0 0 1-1.5 1.5h-11A1.5 1.5 0 0 1 1 13.5v-11zM2.5 2a.5.5 0 0 0-.5.5V5h5V2H2.5zM8 2v3h6V2.5a.5.5 0 0 0-.5-.5H8zm6 4H8v4h6V6zm0 5H8v3h5.5a.5.5 0 0 0 .5-.5V11zM7 14V11H2v2.5a.5.5 0 0 0 .5.5H7zm-5-4h5V6H2v4z"/>
                        </svg>
                      </span>
                      <span className="table-header-name">machines</span>
                    </div>
                    <span className="card-dots">&bull;&bull;&bull;</span>
                  </div>

                  <div className="card-rows">
                    <div className="col-row row-pk">
                      <span className="col-symbol diamond-filled">&#x25C6;</span>
                      <span className="col-key-tag">PK</span>
                      <span className="col-name">machine_id</span>
                      <span className="col-type">text</span>
                      <div className="pin-anchor" ref={sourcePinRef} />
                    </div>
                    <div className="col-row">
                      <span className="col-symbol diamond-empty">&#x25C7;</span>
                      <span className="col-name">machine_name</span>
                      <span className="col-type">text</span>
                    </div>
                    <div className="col-row">
                      <span className="col-symbol diamond-empty">&#x25C7;</span>
                      <span className="col-name">location</span>
                      <span className="col-type">text</span>
                    </div>
                    <div className="col-row">
                      <span className="col-symbol diamond-empty">&#x25C7;</span>
                      <span className="col-name">machine_type</span>
                      <span className="col-type">text</span>
                    </div>
                    <div className="col-row">
                      <span className="col-symbol diamond-empty">&#x25C7;</span>
                      <span className="col-name">status</span>
                      <span className="col-type">text</span>
                    </div>
                    <div className="col-row">
                      <span className="col-symbol diamond-empty">&#x25C7;</span>
                      <span className="col-name">installation_date</span>
                      <span className="col-type">text</span>
                    </div>
                  </div>
                </div>
              </div>

              {/* Bottom Row: 3 Child Tables */}
              <div className="canvas-row-bottom">
                {/* sensor_readings */}
                <div className="schema-card">
                  <div className="card-top-bar">
                    <div className="card-title-group">
                      <span className="icon-table">
                        <svg width="12" height="12" viewBox="0 0 16 16" fill="currentColor">
                          <path d="M1 2.5A1.5 1.5 0 0 1 2.5 1h11A1.5 1.5 0 0 1 15 2.5v11a1.5 1.5 0 0 1-1.5 1.5h-11A1.5 1.5 0 0 1 1 13.5v-11zM2.5 2a.5.5 0 0 0-.5.5V5h5V2H2.5zM8 2v3h6V2.5a.5.5 0 0 0-.5-.5H8zm6 4H8v4h6V6zm0 5H8v3h5.5a.5.5 0 0 0 .5-.5V11zM7 14V11H2v2.5a.5.5 0 0 0 .5.5H7zm-5-4h5V6H2v4z"/>
                        </svg>
                      </span>
                      <span className="table-header-name">sensor_readings</span>
                    </div>
                    <span className="card-dots">&bull;&bull;&bull;</span>
                  </div>

                  <div className="card-rows">
                    <div className="col-row row-pk">
                      <span className="col-symbol diamond-filled">&#x25C6;</span>
                      <span className="col-key-tag">PK</span>
                      <span className="col-name">reading_id</span>
                      <span className="col-type">integer</span>
                    </div>
                    <div className="col-row row-fk">
                      <div className="pin-target-anchor" ref={sensorPinRef} />
                      <span className="col-symbol diamond-filled">&#x25C6;</span>
                      <span className="col-key-tag">FK</span>
                      <span className="col-name">machine_id</span>
                      <span className="col-type">text</span>
                    </div>
                    <div className="col-row">
                      <span className="col-symbol diamond-empty">&#x25C7;</span>
                      <span className="col-name">temperature</span>
                      <span className="col-type">real</span>
                    </div>
                    <div className="col-row">
                      <span className="col-symbol diamond-empty">&#x25C7;</span>
                      <span className="col-name">humidity</span>
                      <span className="col-type">real</span>
                    </div>
                    <div className="col-row">
                      <span className="col-symbol diamond-empty">&#x25C7;</span>
                      <span className="col-name">energy</span>
                      <span className="col-type">real</span>
                    </div>
                    <div className="col-row">
                      <span className="col-symbol diamond-empty">&#x25C7;</span>
                      <span className="col-name">vibration</span>
                      <span className="col-type">real</span>
                    </div>
                    <div className="col-row">
                      <span className="col-symbol diamond-empty">&#x25C7;</span>
                      <span className="col-name">timestamp</span>
                      <span className="col-type">text</span>
                    </div>
                  </div>
                </div>

                {/* production */}
                <div className="schema-card">
                  <div className="card-top-bar">
                    <div className="card-title-group">
                      <span className="icon-table">
                        <svg width="12" height="12" viewBox="0 0 16 16" fill="currentColor">
                          <path d="M1 2.5A1.5 1.5 0 0 1 2.5 1h11A1.5 1.5 0 0 1 15 2.5v11a1.5 1.5 0 0 1-1.5 1.5h-11A1.5 1.5 0 0 1 1 13.5v-11zM2.5 2a.5.5 0 0 0-.5.5V5h5V2H2.5zM8 2v3h6V2.5a.5.5 0 0 0-.5-.5H8zm6 4H8v4h6V6zm0 5H8v3h5.5a.5.5 0 0 0 .5-.5V11zM7 14V11H2v2.5a.5.5 0 0 0 .5.5H7zm-5-4h5V6H2v4z"/>
                        </svg>
                      </span>
                      <span className="table-header-name">production</span>
                    </div>
                    <span className="card-dots">&bull;&bull;&bull;</span>
                  </div>

                  <div className="card-rows">
                    <div className="col-row row-pk">
                      <span className="col-symbol diamond-filled">&#x25C6;</span>
                      <span className="col-key-tag">PK</span>
                      <span className="col-name">production_id</span>
                      <span className="col-type">integer</span>
                    </div>
                    <div className="col-row row-fk">
                      <div className="pin-target-anchor" ref={prodPinRef} />
                      <span className="col-symbol diamond-filled">&#x25C6;</span>
                      <span className="col-key-tag">FK</span>
                      <span className="col-name">machine_id</span>
                      <span className="col-type">text</span>
                    </div>
                    <div className="col-row">
                      <span className="col-symbol diamond-empty">&#x25C7;</span>
                      <span className="col-name">units_produced</span>
                      <span className="col-type">integer</span>
                    </div>
                    <div className="col-row">
                      <span className="col-symbol diamond-empty">&#x25C7;</span>
                      <span className="col-name">defective_units</span>
                      <span className="col-type">integer</span>
                    </div>
                    <div className="col-row">
                      <span className="col-symbol diamond-empty">&#x25C7;</span>
                      <span className="col-name">production_date</span>
                      <span className="col-type">text</span>
                    </div>
                  </div>
                </div>

                {/* maintenance */}
                <div className="schema-card">
                  <div className="card-top-bar">
                    <div className="card-title-group">
                      <span className="icon-table">
                        <svg width="12" height="12" viewBox="0 0 16 16" fill="currentColor">
                          <path d="M1 2.5A1.5 1.5 0 0 1 2.5 1h11A1.5 1.5 0 0 1 15 2.5v11a1.5 1.5 0 0 1-1.5 1.5h-11A1.5 1.5 0 0 1 1 13.5v-11zM2.5 2a.5.5 0 0 0-.5.5V5h5V2H2.5zM8 2v3h6V2.5a.5.5 0 0 0-.5-.5H8zm6 4H8v4h6V6zm0 5H8v3h5.5a.5.5 0 0 0 .5-.5V11zM7 14V11H2v2.5a.5.5 0 0 0 .5.5H7zm-5-4h5V6H2v4z"/>
                        </svg>
                      </span>
                      <span className="table-header-name">maintenance</span>
                    </div>
                    <span className="card-dots">&bull;&bull;&bull;</span>
                  </div>

                  <div className="card-rows">
                    <div className="col-row row-pk">
                      <span className="col-symbol diamond-filled">&#x25C6;</span>
                      <span className="col-key-tag">PK</span>
                      <span className="col-name">maintenance_id</span>
                      <span className="col-type">integer</span>
                    </div>
                    <div className="col-row row-fk">
                      <div className="pin-target-anchor" ref={maintPinRef} />
                      <span className="col-symbol diamond-filled">&#x25C6;</span>
                      <span className="col-key-tag">FK</span>
                      <span className="col-name">machine_id</span>
                      <span className="col-type">text</span>
                    </div>
                    <div className="col-row">
                      <span className="col-symbol diamond-empty">&#x25C7;</span>
                      <span className="col-name">issue</span>
                      <span className="col-type">text</span>
                    </div>
                    <div className="col-row">
                      <span className="col-symbol diamond-empty">&#x25C7;</span>
                      <span className="col-name">maintenance_type</span>
                      <span className="col-type">text</span>
                    </div>
                    <div className="col-row">
                      <span className="col-symbol diamond-empty">&#x25C7;</span>
                      <span className="col-name">maintenance_date</span>
                      <span className="col-type">text</span>
                    </div>
                    <div className="col-row">
                      <span className="col-symbol diamond-empty">&#x25C7;</span>
                      <span className="col-name">status</span>
                      <span className="col-type">text</span>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
