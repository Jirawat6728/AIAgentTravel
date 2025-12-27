// AITravelChat.jsx
import React, { useState, useRef, useEffect, useMemo } from 'react';
import './AITravelChat.css';
import PlanChoiceCard from './PlanChoiceCard';
import {
  TripSummaryCard,
  EditSectionCard,
  UserInfoCard,
  ConfirmBookingCard,
} from './TripSummaryUI';

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000';

// ===== LocalStorage keys =====
const LS_TRIPS_KEY = 'ai_travel_trips_v1';
const LS_ACTIVE_TRIP_KEY = 'ai_travel_active_trip_id_v1';

// ===== Helpers =====
function nowISO() {
  return new Date().toISOString();
}

function shortDate(iso) {
  try {
    const d = new Date(iso);
    return d.toLocaleString('th-TH', { dateStyle: 'medium', timeStyle: 'short' });
  } catch {
    return iso || '';
  }
}

function makeId(prefix = 'trip') {
  return `${prefix}_${Date.now()}_${Math.random().toString(16).slice(2)}`;
}

function defaultWelcomeMessage() {
  return {
    id: 1,
    type: 'bot',
    text: "สวัสดีค่ะ ดิฉันคือ AI Travel Agent 💙 เล่าไอเดียทริปของคุณได้เลย หรือจะให้ช่วยคิดทริปให้ตั้งแต่ศูนย์ก็ได้นะคะ"
  };
}

function createNewTrip(title = 'ทริปใหม่') {
  const tripId = makeId('trip');
  return {
    tripId,
    title,
    createdAt: nowISO(),
    updatedAt: nowISO(),
    messages: [defaultWelcomeMessage()]
  };
}

export default function AITravelChat({ user, onLogout, initialPrompt = '' }) {
  const userId = user?.id || 'demo_user';

  // Cooldown for regenerate/refresh to prevent spam
  const REFRESH_COOLDOWN_MS = 4000;
  const lastRefreshAtRef = useRef({}); // { [messageId]: number }

  const messagesEndRef = useRef(null);
  const inputRef = useRef(null);

  // ===== Trips state (sidebar history) =====
  const [trips, setTrips] = useState(() => {
    try {
      const raw = localStorage.getItem(LS_TRIPS_KEY);
      if (raw) {
        const parsed = JSON.parse(raw);
        if (Array.isArray(parsed) && parsed.length > 0) return parsed;
      }
    } catch (_) {}
    return [createNewTrip('ทริปใหม่')];
  });

  const [activeTripId, setActiveTripId] = useState(() => {
    try {
      const saved = localStorage.getItem(LS_ACTIVE_TRIP_KEY);
      if (saved) return saved;
    } catch (_) {}
    return null;
  });

  const [inputText, setInputText] = useState('');
  const [isTyping, setIsTyping] = useState(false);
  const [isRecording, setIsRecording] = useState(false);
  const [isConnected, setIsConnected] = useState(true);
  const [editingMessageId, setEditingMessageId] = useState(null);
  const abortControllerRef = useRef(null);

  // ===== Selected plan (persists across messages) =====
  const [selectedPlan, setSelectedPlan] = useState(null);
  const [selectedTravelSlots, setSelectedTravelSlots] = useState(null);
  const [latestPlanChoices, setLatestPlanChoices] = useState([]);

  // ===== Derived: active trip =====
  const activeTrip = useMemo(() => {
    return trips.find(t => t.tripId === activeTripId) || trips[0];
  }, [trips, activeTripId]);

  const lastUserMessageId = useMemo(() => {
    const last = [...(activeTrip?.messages || [])].slice().reverse().find(m => m.type === 'user');
    return last?.id;
  }, [activeTrip]);

  const messages = activeTrip?.messages || [];

  // ===== Persist trips + activeTripId =====
  useEffect(() => {
    try {
      localStorage.setItem(LS_TRIPS_KEY, JSON.stringify(trips));
    } catch (_) {}
  }, [trips]);

  useEffect(() => {
    if (!activeTripId && trips.length > 0) {
      setActiveTripId(trips[0].tripId);
      return;
    }
    if (activeTripId && !trips.some(t => t.tripId === activeTripId) && trips.length > 0) {
      setActiveTripId(trips[0].tripId);
    }
  }, [activeTripId, trips]);

  useEffect(() => {
    try {
      if (activeTripId) localStorage.setItem(LS_ACTIVE_TRIP_KEY, activeTripId);
    } catch (_) {}
  }, [activeTripId]);

  // ===== Scroll =====
  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [activeTripId, messages.length]);

  // ===== API health =====
  useEffect(() => {
    checkApiConnection();
    // eslint-disable-next-line react-hooks/exhaustive-deps
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
    if ((raw.startsWith('{') && raw.endsWith('}')) || (raw.startsWith('[') && raw.endsWith(']'))) {
      try {
        const obj = JSON.parse(raw);
        if (typeof obj === 'string') return obj;
        if (obj && typeof obj === 'object' && typeof obj.response === 'string') {
          return obj.response;
        }
      } catch {
        return text;
      }
    }

    return text;
  };

  // ===== Trips update helpers =====
  const appendMessageToTrip = (tripId, msg) => {
    setTrips(prev =>
      prev.map(t => {
        if (t.tripId !== tripId) return t;
        const nextMessages = [...(t.messages || []), msg];
        return {
          ...t,
          messages: nextMessages,
          updatedAt: nowISO(),
        };
      })
    );
  };

  const setTripTitle = (tripId, title) => {
    if (!title) return;
    setTrips(prev =>
      prev.map(t => {
        if (t.tripId !== tripId) return t;
        return { ...t, title, updatedAt: nowISO() };
      })
    );
  };

  // ===== Create/Delete trip =====
  const handleNewTrip = () => {
    const nt = createNewTrip('ทริปใหม่');
    setTrips(prev => [nt, ...prev]);
    setActiveTripId(nt.tripId);
    setInputText('');

    // Reset backend trip context (agent shouldn't auto-run on new trip)
    fetch(`${API_BASE_URL}/api/chat/reset`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      credentials: 'include',
      body: JSON.stringify({
        user_id: userId,
        client_trip_id: nt.tripId
      })
    }).catch(() => {});
  };

  const handleDeleteTrip = (tripId) => {
    const ok = window.confirm('ลบทริปนี้ออกจากประวัติใช่ไหม?');
    if (!ok) return;

    setTrips(prev => {
      const next = prev.filter(t => t.tripId !== tripId);
      return next.length > 0 ? next : [createNewTrip('ทริปใหม่')];
    });

    if (activeTripId === tripId) {
      const remaining = trips.filter(t => t.tripId !== tripId);
      setActiveTripId(remaining[0]?.tripId || null);
    }
  };

  // ===== Stop current request =====
  const handleStop = () => {
    if (abortControllerRef.current) {
      abortControllerRef.current.abort();
      abortControllerRef.current = null;
    }
    setIsTyping(false);
  };

  // ===== Edit message =====
  const handleEditMessage = (messageId, messageText) => {
    setEditingMessageId(messageId);
    setInputText(messageText);
    inputRef.current?.focus();
  };

  // ===== Refresh bot message =====
  const handleRefreshBot = async (userMessageId, userMessageText) => {
    if (isTyping) return;
    await regenerateFromUserText(userMessageId, userMessageText);
  };

  // ===== Send message to backend =====
  const sendMessage = async (textToSend) => {
    const trimmed = String(textToSend || '').trim();
    if (!trimmed) return;

    if (!isConnected) {
      alert('Backend is not connected. Please start the backend server first.');
      return;
    }

    const tripId = activeTrip?.tripId;
    if (!tripId) return;

    // If editing, remove the old message and its bot response
    if (editingMessageId) {
      setTrips(prev =>
        prev.map(t => {
          if (t.tripId !== tripId) return t;
          const msgIndex = t.messages.findIndex(m => m.id === editingMessageId);
          if (msgIndex === -1) return t;
          // Remove the user message and all messages after it
          const newMessages = t.messages.slice(0, msgIndex);
          return { ...t, messages: newMessages, updatedAt: nowISO() };
        })
      );
      setEditingMessageId(null);
    }

    const userMessage = {
      id: Date.now(),
      type: 'user',
      text: trimmed
    };

    appendMessageToTrip(tripId, userMessage);
    setIsTyping(true);

    // Create abort controller for this request
    abortControllerRef.current = new AbortController();

    try {
      const response = await fetch(`${API_BASE_URL}/api/chat`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        credentials: 'include',
        signal: abortControllerRef.current.signal,
        body: JSON.stringify({
          user_id: userId,
          message: trimmed,
          trigger: 'user_message',
          client_trip_id: tripId
        })
      });

      if (!response.ok) throw new Error(`API Error: ${response.status}`);

      const data = await response.json();
      console.log('API data >>>', data);

      const botMessage = {
        id: Date.now() + 1,
        type: 'bot',
        text: data.response,
        debug: data.debug || null,
        travelSlots: data.travel_slots || null,
        searchResults: data.search_results || {},
        // หลังเลือกช้อยส์แล้ว ไม่ต้องแสดง list ช้อยส์ซ้ำ (ให้ไหลไป Trip Summary ต่อเลย)
        planChoices: data.plan_choices || [],
        agentState: data.agent_state || null,
        suggestions: data.suggestions || [],
        currentPlan: data.current_plan || null,
        tripTitle: data.trip_title || null
      };

      appendMessageToTrip(tripId, botMessage);

      // Keep plan/choices in state so cards don't disappear
      if (data.plan_choices) setLatestPlanChoices(data.plan_choices);
      if (data.current_plan) {
        setSelectedPlan(data.current_plan);
        setSelectedTravelSlots(data.travel_slots || null);
      }


      // ✅ ตั้งชื่อทริปโดย Gemini จาก backend
      if (data.trip_title) {
        setTripTitle(tripId, data.trip_title);
      }
    } catch (error) {
      console.error('Error calling API:', error);

      if (error.name === 'AbortError') {
        appendMessageToTrip(tripId, {
          id: Date.now() + 1,
          type: 'bot',
          text: '⏹️ หยุดการทำงานแล้วค่ะ'
        });
      } else {
        const errorMessage = {
          id: Date.now() + 1,
          type: 'bot',
          text: `❌ Error: ${error.message}\n\nPlease check:\n1. Backend is running\n2. API Keys are correct`
        };

        appendMessageToTrip(tripId, errorMessage);
        setIsConnected(false);
      }
    } finally {
      setIsTyping(false);
      abortControllerRef.current = null;
    }
  };

  // ===== Regenerate (refresh) last user message like ChatGPT =====
  const regenerateFromUserText = async (messageId, userText) => {
    const tripId = activeTrip?.tripId;
    if (!tripId) return;
    const trimmed = String(userText || '').trim();
    if (!trimmed) return;

    const now = Date.now();
    const lastAt = lastRefreshAtRef.current[messageId] || 0;
    if (now - lastAt < REFRESH_COOLDOWN_MS) return;
    lastRefreshAtRef.current[messageId] = now;

    setIsTyping(true);
    
    // Create abort controller for this request
    abortControllerRef.current = new AbortController();
    
    try {
      const response = await fetch(`${API_BASE_URL}/api/chat`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        credentials: 'include',
        signal: abortControllerRef.current.signal,
        body: JSON.stringify({
          user_id: userId,
          message: trimmed,
          trigger: 'refresh',
          no_memory: true,
          client_trip_id: tripId
        })
      });
      if (!response.ok) throw new Error(`API Error: ${response.status}`);
      const data = await response.json();

      const botMessage = {
        id: Date.now() + 1,
        type: 'bot',
        text: data.response,
        debug: data.debug || null,
        travelSlots: data.travel_slots || null,
        searchResults: data.search_results || {},
        // หลังเลือกช้อยส์แล้ว ให้ไหลไปหน้าสรุปทริป ไม่ต้องแสดง list ช้อยส์ซ้ำอีก
        planChoices: data.plan_choices || [],
        agentState: data.agent_state || null,
        suggestions: data.suggestions || [],
        currentPlan: data.current_plan || null,
        tripTitle: data.trip_title || null
      };

      appendMessageToTrip(tripId, botMessage);

      // Keep plan/choices in state so cards don't disappear
      if (data.plan_choices) setLatestPlanChoices(data.plan_choices);
      if (data.current_plan) {
        setSelectedPlan(data.current_plan);
        setSelectedTravelSlots(data.travel_slots || null);
      }

      if (data.trip_title) setTripTitle(tripId, data.trip_title);
    } catch (e) {
      if (e.name === 'AbortError') {
        appendMessageToTrip(tripId, {
          id: Date.now() + 1,
          type: 'bot',
          text: '⏹️ หยุดการทำงานแล้วค่ะ'
        });
      } else {
        appendMessageToTrip(tripId, {
          id: Date.now() + 1,
          type: 'bot',
          text: `❌ Error: ${e.message}`
        });
      }
    } finally {
      setIsTyping(false);
      abortControllerRef.current = null;
    }
  };

  // ===== Auto-send initial prompt (from Home 'Get Started') =====
  const didAutoSendRef = useRef(false);

  useEffect(() => {
    if (didAutoSendRef.current) return;
    const p = (initialPrompt || '').trim();
    if (!p) return;
    didAutoSendRef.current = true;
    sendMessage(p);
  }, [initialPrompt]);

  const handleSend = () => {
    if (!inputText.trim()) return;
    const currentInput = inputText;
    setInputText('');
    setEditingMessageId(null);
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

        recognition.lang = 'th-TH';
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

  // ===== Select plan choice (click card -> select immediately) =====
  const handleSelectPlanChoice = async (choiceId) => {
    if (!isConnected) {
      alert('Backend is not connected. Please start the backend server first.');
      return;
    }

    const tripId = activeTrip?.tripId;
    if (!tripId) return;

    setIsTyping(true);

    try {
      // ✅ ถ้า backend มี /api/select_choice จะเลือกได้ทันทีแบบไม่ต้องส่งข้อความ
      const res = await fetch(`${API_BASE_URL}/api/select_choice`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        credentials: 'include',
        body: JSON.stringify({
          user_id: userId,
          choice_id: choiceId
        })
      });

      // fallback ถ้า endpoint ไม่มี
      if (!res.ok) {
        setIsTyping(false);
        sendMessage(`เลือกช้อยส์ ${choiceId}`);
        return;
      }

      const data = await res.json();

      const botMessage = {
        id: Date.now() + 1,
        type: 'bot',
        text: data.response,
        debug: data.debug || null,
        travelSlots: data.travel_slots || null,
        searchResults: data.search_results || {},
        planChoices: data.plan_choices || [],
        agentState: data.agent_state || null,
        suggestions: data.suggestions || [],
        currentPlan: data.current_plan || null,
        tripTitle: data.trip_title || null
      };

      appendMessageToTrip(tripId, botMessage);

      // Keep plan/choices in state so cards don't disappear
      if (data.plan_choices) setLatestPlanChoices(data.plan_choices);
      
      // ✅ Force update selected plan immediately to trigger TripSummaryCard display
      // ✅ Clear selectedPlan if backend returns null (e.g., no choices available)
      if (data.current_plan) {
        setSelectedPlan(data.current_plan);
        setSelectedTravelSlots(data.travel_slots || null);
      } else {
        // ✅ Clear old selectedPlan if no current_plan (prevents showing stale summary cards)
        setSelectedPlan(null);
        setSelectedTravelSlots(null);
      }

      if (data.trip_title) {
        setTripTitle(tripId, data.trip_title);
      }
    } catch (e) {
      console.error('select_choice error:', e);
      // fallback
      sendMessage(`เลือกช้อยส์ ${choiceId}`);
    } finally {
      setIsTyping(false);
    }
  };

  // ===== Quick suggestions จากบอท =====
  const handleSuggestionClick = (suggestionText) => {
    sendMessage(suggestionText);
  };

  // ===== Trip summary UI actions (after selecting a choice) =====
  const handlePickEditSection = (section) => {
    const map = {
      flight: 'ขอไฟลต์ใหม่ (เช่น เช้ากว่านี้/เร็วสุด/ถูกสุด)',
      hotel: 'ขอที่พักใหม่ (เช่น ใกล้รถไฟ/ริมหาด/ถูกลง)',
      dates: 'ขยับวันเดินทาง/จำนวนคืน (เช่น +1 วัน หรือ เพิ่ม/ลดคืน)',
      pax: 'เปลี่ยนจำนวนผู้โดยสาร (เช่น ผู้ใหญ่ 2 เด็ก 1)',
      transport: 'ขอการเดินทาง/รถเช่า (เช่น รถเช่า 3 วัน)',
    };
    const text = map[section] || 'ขอแก้ไขแผน';
    setInputText(text);
    setTimeout(() => inputRef.current?.focus(), 0);
  };

  const handleConfirmBooking = async () => {
    const tripId = activeTrip?.tripId;
    if (!tripId) return;

    setIsTyping(true);
    
    try {
      const res = await fetch(`${API_BASE_URL}/api/booking/confirm`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        credentials: 'include',
        body: JSON.stringify({
          user_id: userId,
          trip_id: tripId,
          user_profile: userProfile || null,
        }),
      });
      
      const data = await res.json().catch(() => null);
      
      if (!res.ok) {
        const msg = (data && (data.detail?.message || data.detail?.detail || data.detail || data.message)) || 'Booking failed';
        const errorMsg = typeof msg === 'string' ? msg : JSON.stringify(msg);
        appendMessageToTrip(tripId, {
          id: Date.now() + 1,
          type: 'bot',
          text: `❌ จองไม่สำเร็จค่ะ: ${errorMsg}`,
        });
        return;
      }
      
      // Success - show booking confirmation
      const successMessage = data?.message || '✅ จองสำเร็จ';
      appendMessageToTrip(tripId, {
        id: Date.now() + 1,
        type: 'bot',
        text: successMessage,
        agentState: { intent: 'booking', step: 'completed', steps: [] },
      });
      
    } catch (e) {
      appendMessageToTrip(tripId, {
        id: Date.now() + 1,
        type: 'bot',
        text: `❌ จองไม่สำเร็จค่ะ: ${String(e)}`,
      });
    } finally {
      setIsTyping(false);
    }
  };


  // ===== Agent State / Typing Text =====
  const lastBotWithState = [...messages]
    .slice()
    .reverse()
    .find(m => m.type === 'bot' && m.agentState);

  const currentAgentState = lastBotWithState?.agentState || null;

  // ===== Latest selected plan (after picking a choice) =====
  // We keep this in state so the UI doesn't disappear when new messages arrive.
  // Fallback: if state is empty (e.g., after reload), derive from last bot message with currentPlan.
  const latestBotWithPlan = useMemo(() => {
    // If we have selectedPlan in state, prioritize it by creating a virtual message
    if (selectedPlan) {
      // Find the most recent bot message that has currentPlan and is not an error message
      const lastBotWithPlan = [...messages]
        .slice()
        .reverse()
        .find(m => 
          m.type === 'bot' && 
          m.currentPlan && 
          m.agentState?.step !== 'no_previous_choices' &&
          !m.text?.includes('ยังไม่มีช้อยส์')
        );
      
      // If found, return it with the selectedPlan to ensure it's up to date
      if (lastBotWithPlan) {
        return {
          ...lastBotWithPlan,
          currentPlan: selectedPlan,
          travelSlots: selectedTravelSlots || lastBotWithPlan.travelSlots,
        };
      }
      
      // If not found but we have selectedPlan, create a virtual message
      return {
        id: Date.now(),
        type: 'bot',
        text: 'แพลนที่เลือก',
        currentPlan: selectedPlan,
        travelSlots: selectedTravelSlots,
      };
    }
    
    // Otherwise, find from messages (excluding error messages)
    return [...messages]
      .slice()
      .reverse()
      .find(m => 
        m.type === 'bot' && 
        m.currentPlan &&
        m.agentState?.step !== 'no_previous_choices' &&
        !m.text?.includes('ยังไม่มีช้อยส์')
      );
  }, [messages, selectedPlan, selectedTravelSlots]);

  const effectiveSelectedPlan = selectedPlan || latestBotWithPlan?.currentPlan || null;
  const effectiveSelectedTravelSlots = selectedTravelSlots || latestBotWithPlan?.travelSlots || null;
  const userProfile = useMemo(() => {
    if (!user) return null;
    // Map your app user -> booking profile fields (can be edited later)
    const fullName = (user.name || '').trim();
    const parts = fullName.split(/\s+/).filter(Boolean);
    const first_name = parts[0] || '';
    const last_name = parts.slice(1).join(' ') || '';
    return {
      first_name,
      last_name,
      email: user.email || '',
      phone: user.phone || '',
      dob: user.dob || '',
      gender: user.gender || '',
      passport_no: user.passport_no || '',
      passport_expiry: user.passport_expiry || '',
      nationality: user.nationality || '',
    };
  }, [user]);

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

      {/* Main: Sidebar + Chat */}
      <main className="chat-main chat-main-split">
        {/* ===== Sidebar: Trip History ===== */}
        <aside className="trip-sidebar">
          <div className="trip-sidebar-header">
            <div className="trip-sidebar-title">ประวัติทริป</div>
            <button className="trip-new-btn" onClick={handleNewTrip}>
              + ทริปใหม่
            </button>
          </div>

          <div className="trip-list">
            {trips.map((t) => {
              const isActive = t.tripId === activeTrip?.tripId;
              return (
                <div
                  key={t.tripId}
                  className={`trip-item ${isActive ? 'trip-item-active' : ''}`}
                  onClick={() => setActiveTripId(t.tripId)}
                  title={t.title}
                >
                  <div className="trip-item-top">
                    <div className="trip-item-title">
                      {t.title || 'ทริป'}
                    </div>
                    <button
                      className="trip-delete-btn"
                      onClick={(e) => { e.stopPropagation(); handleDeleteTrip(t.tripId); }}
                      title="ลบทริป"
                    >
                      ✕
                    </button>
                  </div>
                  <div className="trip-item-sub">อัปเดต: {shortDate(t.updatedAt)}</div>
                  <div className="trip-item-sub">ข้อความ: {(t.messages?.length || 0) - 1}</div>
                </div>
              );
            })}
          </div>

          <div className="trip-sidebar-footer">
            <div className="connection-status">
              <div className={`status-dot ${isConnected ? 'status-connected' : 'status-disconnected'}`}></div>
              <span className="status-text">
                {isConnected ? 'Connected' : 'Disconnected'}
              </span>
            </div>
          </div>
        </aside>

        {/* ===== Chat ===== */}
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
                <h3 className="chatbox-title">{activeTrip?.title || 'AI Travel Assistant'}</h3>
                <div className="chatbox-subtitle">
                  {activeTrip?.updatedAt ? `อัปเดตล่าสุด: ${shortDate(activeTrip.updatedAt)}` : ''}
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
                  <div className="message-content-wrapper">
                    <div className={`message-bubble ${message.type === 'user' ? 'message-user' : 'message-bot'}`}>
                      {/* ข้อความหลัก */}
                      <p className="message-text">{formatMessageText(message.text)}</p>

                      {/* Debug (ช่วยตรวจปัญหา Amadeus/Slots) */}
                      {message.type === 'bot' && message.debug && (
                        <details className="debug-details">
                          <summary className="debug-summary">ดูรายละเอียด Debug</summary>
                          <pre className="debug-pre">{JSON.stringify(message.debug, null, 2)}</pre>
                        </details>
                      )}

                      {/* แสดงแพลนที่เลือกปัจจุบัน (ข... สำหรับบอทข้อความเก่า) */}
                      {message.type === 'bot' && message.currentPlan && message.id !== latestBotWithPlan?.id && (
                        <div className="current-plan-summary">
                          <div className="current-plan-title">แพลนที่เลือกปัจจุบัน</div>
                          <div className="current-plan-body">
                            {message.currentPlan.trip_meta && (
                              <div className="current-plan-row">
                                <span>
                                  {message.currentPlan.trip_meta.origin} → {message.currentPlan.trip_meta.destination}
                                </span>
                                {message.currentPlan.trip_meta.check_in && message.currentPlan.trip_meta.check_out && (
                                  <span>
                                    {' '}• {message.currentPlan.trip_meta.check_in} – {message.currentPlan.trip_meta.check_out}
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

                      {/* ✅ Seamless workflow: หลังเลือกช้อยส์ ให้แสดง Trip Summary + Edit + User + Confirm ต่อเนื่อง */}
                      {/* Show TripSummaryCard if: 
                          1. This message has currentPlan and is the latest one with plan, OR
                          2. We have selectedPlan in state and this is the latest bot message with plan
                          3. AND it's not an error message (no choices available) */}
                      {message.type === 'bot' && 
                       ((selectedPlan && message.id === latestBotWithPlan?.id) ||
                        (message.currentPlan && message.id === latestBotWithPlan?.id && !selectedPlan)) &&
                       // ✅ ตรวจสอบว่าไม่ใช่ "ยังไม่มีช้อยส์" message
                       message.currentPlan &&
                       // ✅ ตรวจสอบว่า agent_state ไม่ใช่ "no_previous_choices"
                       message.agentState?.step !== 'no_previous_choices' &&
                       !message.text?.includes('ยังไม่มีช้อยส์') && (
                        <div className="summary-flow">
                          <TripSummaryCard 
                            plan={selectedPlan || message.currentPlan} 
                            travelSlots={selectedTravelSlots || message.travelSlots} 
                          />
                          <EditSectionCard
                            onSelectSection={handlePickEditSection}
                            hints={["ขอไฟลต์เช้ากว่านี้", "ขอที่พักถูกลง", "ขยับวัน +1", "เพิ่มเด็ก 1"]}
                          />
                          <UserInfoCard userProfile={userProfile} />
                          <ConfirmBookingCard
                            canBook={true}
                            onConfirm={handleConfirmBooking}
                            note="ระบบจะจองเฉพาะ Amadeus Sandbox (test) เท่านั้น"
                          />
                        </div>
                      )}

                      {/* การ์ดแผนเที่ยวจาก planChoices */}
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
                      {message.type === 'bot' && message.suggestions && message.suggestions.length > 0 && (
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

                    {/* Action buttons under messages (ChatGPT style) */}
                    {message.type === 'user' && message.id === lastUserMessageId && (
                      <div className="message-actions message-actions-user">
                        <button
                          className="btn-action btn-refresh"
                          onClick={() => regenerateFromUserText(message.id, message.text)}
                          disabled={isTyping}
                          title="รีเฟช"
                        >
                          ↻ รีเฟช
                        </button>
                        <button
                          className="btn-action btn-edit"
                          onClick={() => handleEditMessage(message.id, message.text)}
                          disabled={isTyping}
                          title="แก้ไข"
                        >
                          ✏️ แก้ไข
                        </button>
                        {isTyping && (
                          <button
                            className="btn-action btn-stop"
                            onClick={handleStop}
                            title="หยุด"
                          >
                            ⏹️ หยุด
                          </button>
                        )}
                      </div>
                    )}
                    
                    {/* Action buttons under bot messages */}
                    {message.type === 'bot' && (
                      <div className="message-actions message-actions-bot">
                        <button
                          className="btn-action btn-refresh"
                          onClick={() => {
                            // Find the user message that triggered this bot response
                            const tripMessages = activeTrip?.messages || [];
                            const userMsg = tripMessages.find(m => m.type === 'user' && m.id < message.id);
                            if (userMsg) {
                              handleRefreshBot(userMsg.id, userMsg.text);
                            }
                          }}
                          disabled={isTyping}
                          title="รีเฟช"
                        >
                          ↻ รีเฟช
                        </button>
                        {isTyping && (
                          <button
                            className="btn-action btn-stop"
                            onClick={handleStop}
                            title="หยุด"
                          >
                            ⏹️ หยุด
                          </button>
                        )}
                      </div>
                    )}
                  </div>
                </div>
              ))}

              {/* Typing Indicator */}
              {isTyping && (
                <div className="typing-indicator">
                  <div className="typing-bubble">
                    <div className="typing-text">{getTypingText()}</div>
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

          {/* Trip Summary UI จะถูกแสดงแบบ seamless อยู่ใน bubble ของบอท “ข้อความล่าสุดที่มี currentPlan” */}

          {/* Input Area */}
          <div className="input-area">
            <div className="input-wrapper">
              <textarea
                ref={inputRef}
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
              <button onClick={handleSend} disabled={!inputText.trim()} className="btn-send">
                Send
              </button>
            </div>

            {isRecording && <div className="recording-status">Listening...</div>}
            <div className="powered-by">Powered by Google Gemini AI + Amadeus API</div>
          </div>
        </div>
      </main>
    </div>
  );
}
