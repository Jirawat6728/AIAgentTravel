import React, { useState, useRef, useEffect } from 'react';
import './AITravelChat.css';
import PlanChoiceCard from './PlanChoiceCard';

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000';

export default function AITravelChat({ user, onLogout }) {
  const [messages, setMessages] = useState([
    {
      id: 1,
      type: 'bot',
      text: "สวัสดีค่ะ ดิฉันคือ AI Travel Agent 💙 เล่าไอเดียทริปของคุณได้เลย หรือจะให้ช่วยคิดทริปให้ตั้งแต่ศูนย์ก็ได้นะคะ"
    }
  ]);
  const [inputText, setInputText] = useState('');
  const [isTyping, setIsTyping] = useState(false);
  const [isRecording, setIsRecording] = useState(false);
  const [isConnected, setIsConnected] = useState(true);
  const messagesEndRef = useRef(null);

  // ===== Scroll ลงล่างทุกครั้งที่มีข้อความใหม่ =====
  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  useEffect(() => {
    checkApiConnection();
  }, []);

  const checkApiConnection = async () => {
    try {
      const response = await fetch(`${API_BASE_URL}/health`);
      const data = await response.json();
      setIsConnected(data.status === 'ok');
    } catch (error) {
      console.error('API connection error:', error);
      setIsConnected(false);
    }
  };

  // ===== Helper: ถ้า text เป็น JSON ให้ดึง field response ออกมาแสดง =====
  const formatMessageText = (text) => {
    if (!text) return '';
    let raw = String(text).trim();

    // ลบ ```json ... ``` ถ้ามี
    if (raw.startsWith('```')) {
      raw = raw.replace(/^```(?:json)?\s*/i, '');
      if (raw.endsWith('```')) raw = raw.slice(0, -3).trim();
    }

    // ลอง parse JSON ถ้าหน้าตาเหมือน JSON
    if (
      (raw.startsWith('{') && raw.endsWith('}')) ||
      (raw.startsWith('[') && raw.endsWith(']'))
    ) {
      try {
        const obj = JSON.parse(raw);

        if (typeof obj === 'string') return obj;
        if (obj && typeof obj === 'object' && typeof obj.response === 'string') {
          return obj.response;
        }
      } catch (e) {
        // parse ไม่ได้ก็แสดงข้อความเดิม
        return text;
      }
    }

    return text;
  };

  // ===== ส่งข้อความไป backend (ใช้ได้ทั้งจาก input, suggestion, เลือกช้อยส์) =====
  const sendMessage = async (textToSend) => {
    const trimmed = textToSend.trim();
    if (!trimmed) return;

    if (!isConnected) {
      alert('Backend is not connected. Please start the backend server first.');
      return;
    }

    const userMessage = {
      id: Date.now(),
      type: 'user',
      text: trimmed
    };

    setMessages(prev => [...prev, userMessage]);
    setIsTyping(true);

    try {
      const response = await fetch(`${API_BASE_URL}/api/chat`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          message: trimmed,
          user_id: user?.id || 'demo_user'
        })
      });

      if (!response.ok) {
        throw new Error(`API Error: ${response.status}`);
      }

      const data = await response.json();
      console.log('API data >>>', data);

      const botMessage = {
        id: Date.now() + 1,
        type: 'bot',
        text: data.response,
        searchResults: data.search_results || {},
        planChoices: data.plan_choices || [],
        agentState: data.agent_state || null,
        suggestions: data.suggestions || [],
        currentPlan: data.current_plan || null
      };

      setMessages(prev => [...prev, botMessage]);
    } catch (error) {
      console.error('Error calling API:', error);

      const errorMessage = {
        id: Date.now() + 1,
        type: 'bot',
        text: `❌ Error: ${error.message}\n\nPlease check:\n1. Backend is running\n2. API Keys are correct`
      };

      setMessages(prev => [...prev, errorMessage]);
      setIsConnected(false);
    } finally {
      setIsTyping(false);
    }
  };

  const handleSend = () => {
    if (!inputText.trim()) return;
    const currentInput = inputText;
    setInputText('');
    sendMessage(currentInput);
  };

  const handleKeyPress = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  // ===== Voice Input =====
  const handleVoiceInput = () => {
    if (!isRecording) {
      setIsRecording(true);

      if ('webkitSpeechRecognition' in window || 'SpeechRecognition' in window) {
        const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
        const recognition = new SpeechRecognition();

        recognition.lang = 'th-TH'; // ปรับเป็นภาษาไทย
        recognition.continuous = false;
        recognition.interimResults = false;

        recognition.onresult = (event) => {
          const transcript = event.results[0][0].transcript;
          setInputText(transcript);
          setIsRecording(false);
        };

        recognition.onerror = (event) => {
          console.error('Speech recognition error:', event.error);
          setIsRecording(false);
          alert('Cannot use microphone. Please check microphone permissions.');
        };

        recognition.onend = () => {
          setIsRecording(false);
        };

        recognition.start();
      } else {
        alert('Your browser does not support speech recognition');
        setIsRecording(false);
      }
    } else {
      setIsRecording(false);
    }
  };

  // ===== เลือกช้อยส์แพลนจากการ์ด =====
  const handleSelectPlanChoice = (choiceId) => {
    const text = `เลือกช้อยส์ ${choiceId}`;
    sendMessage(text);
  };

  // ===== Quick suggestions จากบอท =====
  const handleSuggestionClick = (suggestionText) => {
    sendMessage(suggestionText);
  };

  // ===== Agent State / Typing Text =====

  // หา agentState ล่าสุดจากข้อความบอท
  const lastBotWithState = [...messages]
    .slice()
    .reverse()
    .find(m => m.type === 'bot' && m.agentState);

  const currentAgentState = lastBotWithState?.agentState || null;

  const mapIntentToThai = (intent) => {
    switch (intent) {
      case 'collect_preferences':
        return 'กำลังถามเพื่อรู้จักสไตล์การเที่ยวของคุณ';
      case 'suggest_destination':
        return 'กำลังหาเมือง/จังหวัดที่เหมาะกับคุณ';
      case 'plan_trip_and_autoselect':
        return 'กำลังสร้างแพ็กเกจทริปให้เลือก (หลายช้อยส์)';
      case 'edit_plan':
        return 'กำลังปรับแพลนตามที่คุณขอ';
      case 'confirm_plan':
        return 'กำลังสรุปทริปให้ตรวจสอบก่อนจอง';
      case 'idle':
      default:
        return 'รอให้คุณเริ่มคุยเรื่องทริป';
    }
  };

  const getTypingText = () => {
    if (!currentAgentState) return 'กำลังคิดคำตอบให้คุณ...';

    switch (currentAgentState.intent) {
      case 'collect_preferences':
        return 'กำลังเก็บข้อมูลสไตล์การเที่ยวจากคำตอบของคุณ...';
      case 'suggest_destination':
        return 'กำลังเปรียบเทียบจุดหมายที่เข้ากับสไตล์ของคุณ...';
      case 'plan_trip_and_autoselect':
        return 'กำลังวางแพ็กเกจทริปและคำนวณราคาทั้งหมด...';
      case 'edit_plan':
        return 'กำลังปรับแพลนให้ตรงใจมากขึ้น...';
      case 'confirm_plan':
        return 'กำลังสรุปทริปฉบับสุดท้ายให้คุณตรวจดู...';
      default:
        return 'กำลังคิดคำตอบให้คุณ...';
    }
  };

  // ===== UI =====
  return (
    <div className="chat-container">
      {/* Header */}
      <header className="chat-page-header">
        <div className="chat-header-content">
          <div className="chat-logo-section">
            <div className="chat-logo-icon">
              <svg className="chat-plane-icon" fill="currentColor" viewBox="0 0 24 24">
                <path d="M21 16v-2l-8-5V3.5c0-.83-.67-1.5-1.5-1.5S10 2.67 10 3.5V9l-8 5v2l8-2.5V19l-2 1.5V22l3.5-1 3.5 1v-1.5L13 19v-5.5l8 2.5z" />
              </svg>
            </div>
            <span className="chat-logo-text">AI Travel Agent</span>
          </div>
          <nav className="chat-nav-links">
            <a href="#" className="chat-nav-link">Flights</a>
            <a href="#" className="chat-nav-link">Hotels</a>
            <a href="#" className="chat-nav-link">Car Rentals</a>
            <a href="#" className="chat-nav-link">My Bookings</a>
          </nav>
          <div className="user-section">
            {user && (
              <div className="user-info">
                <div className="user-avatar">
                  <span className="user-initial">{user.name?.[0]?.toUpperCase()}</span>
                </div>
                <span className="user-name">{user.name}</span>
              </div>
            )}
            <button onClick={onLogout} className="btn-logout">
              Logout
            </button>
          </div>
        </div>
      </header>

      {/* Chat Container */}
      <main className="chat-main">
        <div className="chat-box">

          {/* Chatbox Header */}
          <div className="chatbox-header">
            <div className="chatbox-header-left">
              <div className="chatbox-avatar">
                <svg className="chatbox-icon" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 10h.01M12 10h.01M16 10h.01M9 16H5a2 2 0 01-2-2V6a2 2 0 012-2h14a2 2 0 012 2v8a2 2 0 01-2 2h-5l-5 5v-5z" />
                </svg>
              </div>
              <div>
                <h3 className="chatbox-title">AI Travel Assistant</h3>
                <div className="connection-status">
                  <div className={`status-dot ${isConnected ? 'status-connected' : 'status-disconnected'}`}></div>
                  <span className="status-text">
                    {isConnected ? 'Connected' : 'Disconnected'}
                  </span>
                </div>
              </div>
            </div>
          </div>

          {/* Messages Area */}
          <div className="messages-area">
            <div className="messages-list">

              {messages.map((message) => (
                <div
                  key={message.id}
                  className={`message-wrapper ${message.type === 'user' ? 'message-right' : 'message-left'}`}
                >
                  <div className={`message-bubble ${message.type === 'user' ? 'message-user' : 'message-bot'}`}>

                    {/* ข้อความหลัก */}
                    <p className="message-text">
                      {formatMessageText(message.text)}
                    </p>

                    {/* แสดงแพลนที่เลือกปัจจุบัน (หลังจากเลือกช้อยส์แล้ว) */}
                    {message.type === 'bot' && message.currentPlan && (
                      <div className="current-plan-summary">
                        <div className="current-plan-title">📌 แพลนที่เลือกปัจจุบัน</div>
                        <div className="current-plan-body">
                          {message.currentPlan.trip_meta && (
                            <div className="current-plan-row">
                              <span>
                                {message.currentPlan.trip_meta.origin} → {message.currentPlan.trip_meta.destination}
                              </span>
                              {message.currentPlan.trip_meta.check_in && message.currentPlan.trip_meta.check_out && (
                                <span>
                                  • {message.currentPlan.trip_meta.check_in} – {message.currentPlan.trip_meta.check_out}
                                </span>
                              )}
                            </div>
                          )}
                          {message.currentPlan.summary && (
                            <div className="current-plan-price">
                              {message.currentPlan.summary.currency || 'THB'}{' '}
                              {message.currentPlan.summary.total_price?.toLocaleString('th-TH')}
                            </div>
                          )}
                        </div>
                      </div>
                    )}

                    {/* การ์ดแผนเที่ยวจาก planChoices (รองรับ 1–10 ช้อยส์) */}
                    {message.planChoices && message.planChoices.length > 0 && (
                      <div className="plan-choices-block">
                        <div className="plan-choices-header">
                          แผนเที่ยวที่จัดให้คุณเลือกทั้งหมด {message.planChoices.length} ช้อยส์
                        </div>
                        <div className="plan-choices-grid">
                          {message.planChoices.map((choice) => (
                            <PlanChoiceCard
                              key={choice.id}
                              choice={choice}
                              onSelect={handleSelectPlanChoice}
                            />
                          ))}
                        </div>
                      </div>
                    )}

                    {/* Suggestion chips จากบอท */}
                    {message.type === 'bot' &&
                      message.suggestions &&
                      message.suggestions.length > 0 && (
                        <div className="suggestion-chips">
                          {message.suggestions.map((s, idx) => (
                            <button
                              key={idx}
                              className="suggestion-chip"
                              onClick={() => handleSuggestionClick(s)}
                            >
                              {s}
                            </button>
                          ))}
                        </div>
                      )}

                  </div>
                </div>
              ))}

              {/* Typing Indicator */}
              {isTyping && (
                <div className="typing-indicator">
                  <div className="typing-bubble">
                    <div className="typing-text">
                      {getTypingText()}
                    </div>
                    <div className="typing-dots">
                      <div className="typing-dot"></div>
                      <div className="typing-dot"></div>
                      <div className="typing-dot"></div>
                    </div>
                  </div>
                </div>
              )}

              <div ref={messagesEndRef} />
            </div>
          </div>

          {/* Input Area */}
          <div className="input-area">
            <div className="input-wrapper">
              <textarea
                value={inputText}
                onChange={(e) => setInputText(e.target.value)}
                onKeyPress={handleKeyPress}
                placeholder="เช่น “พรุ่งนี้วันหยุดอยากไปเที่ยว” หรือ “ไปภูเก็ต 3 วัน 2 คน 1 เด็ก”"
                rows="1"
                className="input-field"
              />
              <button
                onClick={handleVoiceInput}
                className={`btn-mic ${isRecording ? 'btn-mic-recording' : ''}`}
                title={isRecording ? 'Recording...' : 'Voice input'}
              >
                <svg className="mic-icon" fill="currentColor" viewBox="0 0 24 24">
                  <path d="M12 14c1.66 0 3-1.34 3-3V5c0-1.66-1.34-3-3-3S9 3.34 9 5v6c0 1.66 1.34 3 3 3z" />
                  <path d="M17 11c0 2.76-2.24 5-5 5s-5-2.24-5-5H5c0 3.53 2.61 6.43 6 6.92V21h2v-3.08c3.39-.49 6-3.39 6-6.92h-2z" />
                </svg>
              </button>
              <button
                onClick={handleSend}
                disabled={!inputText.trim()}
                className="btn-send"
              >
                Send
              </button>
            </div>
            {isRecording && (
              <div className="recording-status">
                🎤 Listening...
              </div>
            )}
            <div className="powered-by">
              Powered by Google Gemini AI + Amadeus API
            </div>
          </div>

        </div>
      </main>
    </div>
  );
}
