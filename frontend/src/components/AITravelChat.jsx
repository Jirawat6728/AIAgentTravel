// AITravelChat.jsx
import React, { useState, useRef, useEffect, useMemo } from 'react';
import Swal from 'sweetalert2';
import './AITravelChat.css';
import AppHeader from './AppHeader';
import PlanChoiceCard from './PlanChoiceCard';
import {
  TripSummaryCard,
  UserInfoCard,
  ConfirmBookingCard,
  FinalTripSummary,
} from './TripSummaryUI';
import {
  FlightSlotCard,
  HotelSlotCard,
  TransportSlotCard,
} from './SlotCards';

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000';

// ===== LocalStorage keys =====
const LS_TRIPS_KEY = 'ai_travel_trips_v1';
const LS_ACTIVE_TRIP_KEY = 'ai_travel_active_trip_id_v1';

// ===== Helpers =====
function nowISO() {
  return new Date().toISOString();
}

const GREETINGS = [
  "สวัสดีค่ะคุณ {name} ดิฉันคือ AI Travel Agent 💙 เล่าไอเดียทริปของคุณได้เลย หรือจะให้ช่วยคิดทริปให้ตั้งแต่ศูนย์ก็ได้นะคะ",
  "ยินดีต้อนรับค่ะคุณ {name} ✈️ วันนี้อยากให้ดิฉันช่วยแพลนทริปในฝันที่ไหนดีคะ? บอกมาได้เลยค่ะ!",
  "สวัสดีค่ะคุณ {name}! พร้อมจะออกเดินทางหรือยังคะ? 🌍 จะไปทะเล ภูเขา หรือต่างประเทศ ให้ดิฉันช่วยจัดการให้นะคะ",
  "สวัสดีค่ะคุณ {name} 💙 วันนี้มีแพลนจะไปเที่ยวที่ไหนในใจหรือยังคะ? ให้ดิฉันช่วยหาไฟลต์หรือที่พักดีๆ ให้ไหมคะ?",
  "ยินดีที่ได้พบกันค่ะคุณ {name} ✨ วันนี้อยากไปพักผ่อนแบบไหนดีคะ? เล่าความต้องการของคุณให้ดิฉันฟังได้เลยค่ะ"
];

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

function defaultWelcomeMessage(userName = "คุณ") {
  const randomGreeting = GREETINGS[Math.floor(Math.random() * GREETINGS.length)];
  const personalizedGreeting = randomGreeting.replace("{name}", userName);
  
  return {
    id: 1,
    type: 'bot',
    text: personalizedGreeting
  };
}

function createNewTrip(title = 'ทริปใหม่', userName = "คุณ") {
  const tripId = makeId('trip');
  return {
    tripId,
    title,
    createdAt: nowISO(),
    updatedAt: nowISO(),
    messages: [defaultWelcomeMessage(userName)],
    pinned: false // เพิ่ม field สำหรับปักหมุด
  };
}

export default function AITravelChat({ user, onLogout, onSignIn, initialPrompt = '', onNavigateToBookings, onNavigateToFlights, onNavigateToHotels, onNavigateToCarRentals }) {
  const userId = user?.id || 'demo_user';

  // ✅ Active tab state for navigation (switch/tab indicator)
  const [activeTab, setActiveTab] = useState('flights'); // Default to 'flights'

  // Cooldown for regenerate/refresh to prevent spam
  const REFRESH_COOLDOWN_MS = 4000;
  const lastRefreshAtRef = useRef({}); // { [messageId]: number }

  const messagesEndRef = useRef(null);
  const inputRef = useRef(null);

  // ===== Trips state (sidebar history) =====
  const [trips, setTrips] = useState(() => {
    const displayName = user?.first_name || user?.name || "คุณ";
    try {
      const raw = localStorage.getItem(LS_TRIPS_KEY);
      if (raw) {
        const parsed = JSON.parse(raw);
        if (Array.isArray(parsed) && parsed.length > 0) return parsed;
      }
    } catch (_) {}
    return [createNewTrip('ทริปใหม่', displayName)];
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
  const [isVoiceMode, setIsVoiceMode] = useState(false);
  const recognitionRef = useRef(null);
  const synthesisRef = useRef(null);
  const isVoiceModeRef = useRef(false); // ใช้ ref เพื่อตรวจสอบใน callback
  
  // Cleanup voice mode เมื่อ component unmount
  useEffect(() => {
    return () => {
      stopVoiceMode();
    };
  }, []);
  const [isConnected, setIsConnected] = useState(true);
  const [editingMessageId, setEditingMessageId] = useState(null);
  const [editingTripId, setEditingTripId] = useState(null);
  const [editingTripName, setEditingTripName] = useState('');
  const abortControllerRef = useRef(null);
  // ✅ สถานะการทำงานของ Agent แบบ realtime
  const [agentStatus, setAgentStatus] = useState(null); // { status, message, step }
  // ✅ สถานะเปิด/ปิด sidebar: Desktop เปิดเสมอ, Mobile เริ่มต้นปิด
  const [isSidebarOpen, setIsSidebarOpen] = useState(() => {
    // Desktop: เปิดเสมอ, Mobile: ปิด
    return typeof window !== 'undefined' && window.innerWidth > 768;
  });
  
  // ✅ ตรวจสอบ window resize เพื่ออัปเดต sidebar state
  useEffect(() => {
    const handleResize = () => {
      if (window.innerWidth > 768) {
        // Desktop: เปิดเสมอ
        setIsSidebarOpen(true);
      } else {
        // Mobile: ปิดเมื่อเปลี่ยนเป็น mobile
        setIsSidebarOpen(false);
      }
    };
    
    window.addEventListener('resize', handleResize);
    return () => window.removeEventListener('resize', handleResize);
  }, []);
  
  // ✅ สำหรับ swipe gesture บน mobile
  const touchStartRef = useRef(null);
  const touchEndRef = useRef(null);
  
  // ✅ ปรับแต่งตามความกว้างหน้าจอ: บน mobile เริ่มต้นด้วย sidebar ปิด
  useEffect(() => {
    const handleResize = () => {
      if (window.innerWidth <= 768) {
        setIsSidebarOpen(false);
      } else {
        setIsSidebarOpen(true);
      }
    };
    
    handleResize(); // ตรวจสอบเมื่อ component mount
    window.addEventListener('resize', handleResize);
    return () => window.removeEventListener('resize', handleResize);
  }, []);

  // ===== Selected plan (persists across messages) =====
  const [selectedPlan, setSelectedPlan] = useState(null);
  const [selectedTravelSlots, setSelectedTravelSlots] = useState(null);
  const [latestPlanChoices, setLatestPlanChoices] = useState([]);
  
  // ===== Booking state =====
  const [isBooking, setIsBooking] = useState(false);
  const [bookingResult, setBookingResult] = useState(null);

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

  // ===== API health & Auto-reconnect =====
  useEffect(() => {
    checkApiConnection();
    // ตั้งเวลาตรวจสอบการเชื่อมต่อทุก 10 วินาที เพื่อ Reconnect อัตโนมัติ
    const interval = setInterval(checkApiConnection, 10000);
    return () => clearInterval(interval);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const checkApiConnection = async () => {
    try {
      const response = await fetch(`${API_BASE_URL}/health`, { cache: 'no-cache' });
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
    // ถ้า text เป็น object ให้จัดการก่อน
    if (typeof text === 'object') {
      // ถ้า object มี property response (string) ให้ใช้ response
      if (text.response && typeof text.response === 'string') {
        return text.response;
      }
      // ถ้า object มี property message (string) ให้ใช้ message
      if (text.message && typeof text.message === 'string') {
        return text.message;
      }
      // ถ้าไม่ใช่ ให้แปลงเป็น JSON string (ไม่ใช้ String() เพราะจะได้ [object Object])
      try {
        return JSON.stringify(text, null, 2);
      } catch {
        return '[ไม่สามารถแสดงข้อมูลได้]';
      }
    }
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

  // ===== Swipe gesture handlers (mobile only) =====
  const minSwipeDistance = 50; // ระยะทางขั้นต่ำสำหรับ swipe
  
  const onTouchStart = (e) => {
    // ทำงานเฉพาะ mobile
    if (window.innerWidth > 768) return;
    touchEndRef.current = null;
    touchStartRef.current = e.targetTouches[0].clientX;
  };
  
  const onTouchMove = (e) => {
    // ทำงานเฉพาะ mobile
    if (window.innerWidth > 768) return;
    touchEndRef.current = e.targetTouches[0].clientX;
  };
  
  const onTouchEnd = () => {
    // ทำงานเฉพาะ mobile
    if (window.innerWidth > 768) return;
    if (!touchStartRef.current || !touchEndRef.current) return;
    
    const distance = touchStartRef.current - touchEndRef.current;
    const isLeftSwipe = distance > minSwipeDistance; // ปัดซ้าย = ซ่อน sidebar
    const isRightSwipe = distance < -minSwipeDistance; // ปัดขวา = แสดง sidebar
    
    if (isLeftSwipe && isSidebarOpen) {
      setIsSidebarOpen(false); // ปัดซ้าย = ซ่อน
    } else if (isRightSwipe && !isSidebarOpen) {
      setIsSidebarOpen(true); // ปัดขวา = แสดง
    }
  };

  // ===== Create/Delete trip =====
  const handleNewTrip = () => {
    const displayName = user?.first_name || user?.name || "คุณ";
    const nt = createNewTrip('ทริปใหม่', displayName);
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

  const handleDeleteTrip = async (tripId) => {
    const result = await Swal.fire({
      title: "ลบทริป?",
      text: "คุณต้องการลบทริปนี้ออกจากประวัติใช่ไหม?",
      icon: "question",
      showCancelButton: true,
      confirmButtonColor: "#dc2626",
      cancelButtonColor: "#6b7280",
      confirmButtonText: "ลบ",
      cancelButtonText: "ยกเลิก",
      reverseButtons: true
    });

    if (!result.isConfirmed) return;

    setTrips(prev => {
      const next = prev.filter(t => t.tripId !== tripId);
      return next.length > 0 ? next : [createNewTrip('ทริปใหม่')];
    });

    if (activeTripId === tripId) {
      const remaining = trips.filter(t => t.tripId !== tripId);
      setActiveTripId(remaining[0]?.tripId || null);
    }
  };

  // ===== Edit trip name =====
  const handleEditTripName = (tripId, currentTitle) => {
    setEditingTripId(tripId);
    setEditingTripName(currentTitle || 'ทริปใหม่');
  };

  const handleSaveTripName = (tripId) => {
    if (!editingTripName.trim()) {
      setEditingTripId(null);
      return;
    }

    setTrips(prev =>
      prev.map(t =>
        t.tripId === tripId
          ? { ...t, title: editingTripName.trim(), updatedAt: nowISO() }
          : t
      )
    );
    setEditingTripId(null);
    setEditingTripName('');
  };

  const handleCancelEditTripName = () => {
    setEditingTripId(null);
    setEditingTripName('');
  };

  // ===== Toggle pin trip =====
  const handleTogglePin = (tripId) => {
    setTrips(prev =>
      prev.map(t =>
        t.tripId === tripId
          ? { ...t, pinned: !t.pinned, updatedAt: nowISO() }
          : t
      )
    );
  };

  // ===== Sort trips: pinned first, then by updatedAt =====
  const sortedTrips = useMemo(() => {
    return [...trips].sort((a, b) => {
      // ปักหมุดมาก่อน
      if (a.pinned && !b.pinned) return -1;
      if (!a.pinned && b.pinned) return 1;
      // ถ้าทั้งคู่ปักหมุดหรือไม่ปักหมุด ให้เรียงตาม updatedAt (ใหม่สุดมาก่อน)
      return new Date(b.updatedAt) - new Date(a.updatedAt);
    });
  }, [trips]);

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
    setAgentStatus(null); // Reset status

    // Create abort controller for this request
    abortControllerRef.current = new AbortController();

    try {
      // ✅ ใช้ SSE endpoint สำหรับ realtime status updates
      const response = await fetch(`${API_BASE_URL}/api/chat/stream`, {
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

      // ✅ อ่าน SSE stream
      const reader = response.body.getReader();
      const decoder = new TextDecoder();
      let buffer = '';

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split('\n');
        buffer = lines.pop() || ''; // Keep incomplete line in buffer

        for (const line of lines) {
          const trimmedLine = line.trim();
          if (!trimmedLine) continue;

          if (trimmedLine.startsWith('data: ')) {
            try {
              const data = JSON.parse(trimmedLine.slice(6));
              
              // ✅ จัดการ error จาก stream
              if (data.status === 'error') {
                throw new Error(data.message || 'Unknown stream error');
              }
              
              // ✅ อัปเดตสถานะการทำงานแบบ realtime
              if (data.status && data.message) {
                setAgentStatus({
                  status: data.status,
                  message: data.message,
                  step: data.step
                });
              }
              
              // ✅ เมื่อเสร็จสิ้น ให้ใช้ข้อมูลผลลัพธ์
              if (data.status === 'completed' && data.data) {
                const finalData = data.data;
                console.log('API data (completed) >>>', finalData);

                const botMessage = {
                  id: Date.now() + 1,
                  type: 'bot',
                  text: typeof finalData.response === 'string' ? finalData.response : String(finalData.response || ''),
                  debug: finalData.debug || null,
                  travelSlots: finalData.travel_slots || null,
                  searchResults: finalData.search_results || {},
                  planChoices: Array.isArray(finalData.plan_choices) ? finalData.plan_choices : (finalData.plan_choices ? [finalData.plan_choices] : []),
                  agentState: finalData.agent_state || null,
                  suggestions: finalData.suggestions || [],
                  currentPlan: finalData.current_plan || null,
                  tripTitle: finalData.trip_title || null,
                  slotIntent: finalData.slot_intent || null,
                  slotChoices: finalData.slot_choices || [],
                  reasoning: finalData.reasoning || null,  // Level 3: Reasoning light
                  memorySuggestions: finalData.memory_suggestions || null,  // Level 3: Memory toggle
                };
                
                // Debug: log plan choices
                if (botMessage.planChoices && botMessage.planChoices.length > 0) {
                  console.log('📋 Plan choices received:', botMessage.planChoices.length, 'choices');
                }

                appendMessageToTrip(tripId, botMessage);

                // ✅ ถ้าอยู่ในโหมดเสียง ให้ Agent พูดตอบกลับ
                if (isVoiceMode && botMessage.text) {
                  // ลบ emoji และ markdown formatting ออกก่อนพูด
                  const cleanText = botMessage.text
                    .replace(/[🎯💡📋✅❌⏹️💙]/g, '')
                    .replace(/\*\*(.*?)\*\*/g, '$1')
                    .replace(/\*(.*?)\*/g, '$1')
                    .replace(/```[\s\S]*?```/g, '')
                    .replace(/`(.*?)`/g, '$1')
                    .trim();
                  
                  if (cleanText) {
                    speakText(cleanText);
                  }
                }

                // Keep plan/choices in state so cards don't disappear
                if (finalData.plan_choices) setLatestPlanChoices(finalData.plan_choices);
                // ✅ ตั้ง selectedPlan เฉพาะเมื่อมี current_plan และ slot workflow เสร็จแล้ว
                const agentState = finalData.agent_state || {};
                const slotWorkflow = agentState.slot_workflow || {};
                const currentSlot = slotWorkflow.current_slot;
                const isSlotWorkflowComplete = (
                  currentSlot === "summary" || 
                  agentState.step === "trip_summary" ||
                  (!currentSlot && !finalData.slot_choices && !finalData.slot_intent)
                );
                
                if (finalData.current_plan && isSlotWorkflowComplete) {
                  setSelectedPlan(finalData.current_plan);
                  setSelectedTravelSlots(finalData.travel_slots || null);
                } else {
                  // ✅ Clear selectedPlan ถ้าไม่มี current_plan หรือยังอยู่ใน slot workflow
                  setSelectedPlan(null);
                  setSelectedTravelSlots(null);
                }

                // ✅ ตั้งชื่อทริปโดย Gemini จาก backend
                if (finalData.trip_title) {
                  setTripTitle(tripId, finalData.trip_title);
                }
              }
            } catch (err) {
              console.error('Error parsing SSE data line:', trimmedLine, err);
            }
          }
        }
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
      setAgentStatus(null); // Clear status
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
    
    // ✅ Revert chat: ลบข้อความหลังจากข้อความที่กดรีเฟรชออกให้หมด
    setTrips(prev =>
      prev.map(t => {
        if (t.tripId !== tripId) return t;
        const msgIndex = t.messages.findIndex(m => m.id === messageId);
        if (msgIndex === -1) return t;
        // เก็บไว้เฉพาะข้อความจนถึงข้อความ user ที่เรากำลังรีเฟรช
        const newMessages = t.messages.slice(0, msgIndex + 1);
        return { ...t, messages: newMessages, updatedAt: nowISO() };
      })
    );
    
    // Create abort controller for this request
    abortControllerRef.current = new AbortController();
    setAgentStatus(null); // Reset status
    
    try {
      // ✅ ใช้ SSE endpoint เพื่อให้แสดงการทำงานแบบ realtime
      const response = await fetch(`${API_BASE_URL}/api/chat/stream`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        credentials: 'include',
        signal: abortControllerRef.current.signal,
        body: JSON.stringify({
          user_id: userId,
          message: trimmed,
          trigger: 'refresh',
          client_trip_id: tripId
        })
      });

      if (!response.ok) throw new Error(`API Error: ${response.status}`);

      // ✅ อ่าน SSE stream
      const reader = response.body.getReader();
      const decoder = new TextDecoder();
      let buffer = '';

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split('\n');
        buffer = lines.pop() || '';

        for (const line of lines) {
          const trimmedLine = line.trim();
          if (!trimmedLine) continue;
          
          if (trimmedLine.startsWith('data: ')) {
            try {
              const data = JSON.parse(trimmedLine.slice(6));
              
              // ✅ Handle error from stream
              if (data.status === 'error') {
                throw new Error(data.message || 'Unknown stream error');
              }

              // ✅ อัปเดตสถานะการทำงานแบบ realtime
              if (data.status && data.message) {
                setAgentStatus({
                  status: data.status,
                  message: data.message,
                  step: data.step
                });
              }
              
              // ✅ เมื่อเสร็จสิ้น ให้ใช้ข้อมูลผลลัพธ์
              if (data.status === 'completed' && data.data) {
                const finalData = data.data;
                console.log('Refresh API data (completed) >>>', finalData);

      const botMessage = {
        id: Date.now() + 1,
        type: 'bot',
                  text: typeof finalData.response === 'string' ? finalData.response : String(finalData.response || ''),
                  debug: finalData.debug || null,
                  travelSlots: finalData.travel_slots || null,
                  searchResults: finalData.search_results || {},
                  planChoices: Array.isArray(finalData.plan_choices) ? finalData.plan_choices : (finalData.plan_choices ? [finalData.plan_choices] : []),
                  agentState: finalData.agent_state || null,
                  suggestions: finalData.suggestions || [],
                  currentPlan: finalData.current_plan || null,
                  tripTitle: finalData.trip_title || null,
                  slotIntent: finalData.slot_intent || null,
                  slotChoices: finalData.slot_choices || [],
                  reasoning: finalData.reasoning || null,
                  memorySuggestions: finalData.memory_suggestions || null,
      };

      appendMessageToTrip(tripId, botMessage);

                // ✅ ถ้าอยู่ในโหมดเสียง ให้ Agent พูดตอบกลับ
                if (isVoiceMode && botMessage.text) {
                  const cleanText = botMessage.text
                    .replace(/[🎯💡📋✅❌⏹️💙]/g, '')
                    .replace(/\*\*(.*?)\*\*/g, '$1')
                    .replace(/\*(.*?)\*/g, '$1')
                    .replace(/```[\s\S]*?```/g, '')
                    .replace(/`(.*?)`/g, '$1')
                    .trim();
                  
                  if (cleanText) speakText(cleanText);
                }

                // Keep plan/choices in state
                if (finalData.plan_choices) setLatestPlanChoices(finalData.plan_choices);
                
                const agentState = finalData.agent_state || {};
                const slotWorkflow = agentState.slot_workflow || {};
                const isSlotWorkflowComplete = (
                  slotWorkflow.current_slot === "summary" || 
                  agentState.step === "trip_summary" ||
                  (!slotWorkflow.current_slot && !finalData.slot_choices && !finalData.slot_intent)
                );
                
                if (finalData.current_plan && isSlotWorkflowComplete) {
                  setSelectedPlan(finalData.current_plan);
                  setSelectedTravelSlots(finalData.travel_slots || null);
                } else {
                  setSelectedPlan(null);
      }

                if (finalData.trip_title) setTripTitle(tripId, finalData.trip_title);
              }
            } catch (err) {
              console.error('Error parsing SSE data line:', trimmedLine, err);
            }
          }
        }
      }
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

  // ===== Set initial prompt to input field (from Home 'Get Started') =====
  // ✅ ไม่ส่งอัตโนมัติ แต่ให้ผู้ใช้กดส่งเอง
  const didSetInitialPromptRef = useRef(false);

  useEffect(() => {
    if (didSetInitialPromptRef.current) return;
    const p = (initialPrompt || '').trim();
    if (!p) return;
    didSetInitialPromptRef.current = true;
    // แสดงใน input field แทนการส่งอัตโนมัติ
    setInputText(p);
    // Focus input field เพื่อให้ผู้ใช้เห็นและสามารถแก้ไข/ส่งได้
    setTimeout(() => {
      inputRef.current?.focus();
    }, 100);
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

  // ===== Memory Commit Handler (Level 3) =====
  const handleMemoryCommit = async (suggestion, messageId) => {
    try {
      const response = await fetch(`${API_BASE_URL}/api/memory/commit`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        credentials: 'include',
        body: JSON.stringify({
          user_id: userId,
          memory_type: suggestion.type || 'preference',
          data: {
            [suggestion.key]: suggestion.value
          },
          description: suggestion.description || ''
        })
      });
      
      if (response.ok) {
        // Show success feedback
        const data = await response.json();
        console.log('Memory committed:', data);
        // TODO: Show toast notification
      }
    } catch (error) {
      console.error('Memory commit failed:', error);
    }
  };

  // ===== Voice Conversation Mode =====
  const handleVoiceInput = () => {
    if (!isVoiceMode) {
      // เริ่มโหมดเสียง
      startVoiceMode();
    } else {
      // หยุดโหมดเสียง
      stopVoiceMode();
    }
  };

  const startVoiceMode = () => {
    if (!('webkitSpeechRecognition' in window || 'SpeechRecognition' in window)) {
      alert('เบราว์เซอร์ของคุณไม่รองรับการรู้จำเสียง กรุณาใช้ Chrome หรือ Edge');
      return;
    }

    if (!('speechSynthesis' in window)) {
      alert('เบราว์เซอร์ของคุณไม่รองรับการพูด กรุณาใช้ Chrome หรือ Edge');
      return;
    }

    setIsVoiceMode(true);
    setIsRecording(true);
    isVoiceModeRef.current = true;

    const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
    const recognition = new SpeechRecognition();
    recognitionRef.current = recognition;

    recognition.lang = 'th-TH';
    recognition.continuous = true; // ฟังต่อเนื่อง
    recognition.interimResults = true; // แสดงผลลัพธ์ชั่วคราว

    let finalTranscript = '';

    recognition.onresult = async (event) => {
      let interimTranscript = '';
      
      for (let i = event.resultIndex; i < event.results.length; i++) {
        const transcript = event.results[i][0].transcript;
        if (event.results[i].isFinal) {
          finalTranscript += transcript + ' ';
        } else {
          interimTranscript += transcript;
        }
      }

      // แสดงผลลัพธ์ชั่วคราวใน input field
      if (interimTranscript) {
        setInputText(finalTranscript + interimTranscript);
      }

      // เมื่อได้ข้อความสุดท้าย ให้ส่งไปยัง Agent
      if (finalTranscript.trim()) {
        const userMessage = finalTranscript.trim();
        setInputText(''); // เคลียร์ input
        finalTranscript = ''; // รีเซ็ตทันที
        
        // ส่งข้อความไปยัง Agent
        await sendMessage(userMessage);
      }
    };

    recognition.onerror = (event) => {
      console.error('Speech recognition error:', event.error);
      if (event.error === 'no-speech') {
        // ไม่มีเสียงพูด ไม่ต้องทำอะไร ฟังต่อ
        return;
      } else if (event.error === 'audio-capture') {
        alert('ไม่สามารถเข้าถึงไมโครโฟนได้ กรุณาตรวจสอบการตั้งค่า');
        stopVoiceMode();
      } else if (event.error === 'not-allowed') {
        alert('ไมโครโฟนถูกปฏิเสธ กรุณาอนุญาตการเข้าถึงไมโครโฟน');
        stopVoiceMode();
      } else {
        // Error อื่นๆ ให้ฟังต่อ
        console.warn('Speech recognition error (continuing):', event.error);
      }
    };

    recognition.onend = () => {
      // ถ้ายังอยู่ในโหมดเสียง ให้เริ่มใหม่
      // ใช้ ref เพื่อตรวจสอบสถานะ
      if (isVoiceModeRef.current && recognitionRef.current === recognition) {
        setTimeout(() => {
          if (isVoiceModeRef.current && recognitionRef.current === recognition) {
            try {
              recognitionRef.current.start();
            } catch (e) {
              // อาจจะกำลังรันอยู่แล้ว
              console.log('Recognition already running');
            }
          }
        }, 100);
      }
    };

    try {
      recognition.start();
    } catch (e) {
      console.error('Failed to start recognition:', e);
      setIsVoiceMode(false);
      setIsRecording(false);
    }
  };

  const stopVoiceMode = () => {
    setIsVoiceMode(false);
    setIsRecording(false);
    isVoiceModeRef.current = false;
    
    if (recognitionRef.current) {
      try {
        recognitionRef.current.stop();
      } catch (e) {
        console.error('Error stopping recognition:', e);
      }
      recognitionRef.current = null;
    }

    // หยุดการพูดถ้ากำลังพูดอยู่
    window.speechSynthesis.cancel();
    synthesisRef.current = null;
  };

  // ฟังก์ชันให้ Agent พูด
  const speakText = (text) => {
    if (!isVoiceModeRef.current) return; // ถ้าไม่อยู่ในโหมดเสียง ไม่ต้องพูด
    
    // หยุดการพูดก่อนหน้า
    window.speechSynthesis.cancel();
    
    const utterance = new SpeechSynthesisUtterance(text);
    utterance.lang = 'th-TH';
    utterance.rate = 1.0;
    utterance.pitch = 1.0;
    utterance.volume = 1.0;
    
    // รอให้ voices โหลดเสร็จก่อน
    const speak = () => {
      const voices = window.speechSynthesis.getVoices();
      const thaiVoice = voices.find(voice => 
        voice.lang.includes('th') || voice.lang.includes('TH')
      );
      if (thaiVoice) {
        utterance.voice = thaiVoice;
      }
      
      synthesisRef.current = utterance;
      
      utterance.onend = () => {
        synthesisRef.current = null;
        // หลังจากพูดเสร็จ ให้เริ่มฟังต่อ
        if (isVoiceModeRef.current && recognitionRef.current) {
          setIsRecording(true);
        }
      };
      
      utterance.onerror = (e) => {
        console.error('Speech synthesis error:', e);
        synthesisRef.current = null;
        // ถ้าเกิด error ก็ให้เริ่มฟังต่อ
        if (isVoiceModeRef.current && recognitionRef.current) {
          setIsRecording(true);
        }
      };
      
      window.speechSynthesis.speak(utterance);
    };
    
    // ถ้า voices ยังไม่โหลด ให้รอ
    if (window.speechSynthesis.getVoices().length === 0) {
      window.speechSynthesis.onvoiceschanged = speak;
    } else {
      speak();
    }
    
    // ระหว่างที่ Agent กำลังพูด ให้หยุดฟัง
    setIsRecording(false);
  };

  // ===== Select slot choice (for flight/hotel slots) =====
  const handleSelectSlotChoice = async (choiceId, slotType, slotChoice, message) => {
    if (!isConnected) {
      alert('Backend is not connected. Please start the backend server first.');
      return;
    }

    const tripId = activeTrip?.tripId;
    if (!tripId) return;

    // ✅ เพิ่มข้อความฝั่งผู้ใช้ว่าเลือก slot X
    const slotName = slotType === 'flight' ? 'ไฟลต์' : slotType === 'hotel' ? 'ที่พัก' : slotType === 'car' ? 'รถ' : 'การเดินทาง';
    const userMessage = {
      id: Date.now(),
      type: 'user',
      text: `เลือก${slotName} ${choiceId}`
    };
    appendMessageToTrip(tripId, userMessage);

    setIsTyping(true);
    
    try {
      const currentPlan = selectedPlan;
      
      // ✅ ถ้าไม่มี currentPlan → ใช้ /api/select_choice เพื่อเลือก slot (slot workflow)
      if (!currentPlan) {
        const res = await fetch(`${API_BASE_URL}/api/select_choice`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          credentials: 'include',
          body: JSON.stringify({
            user_id: userId,
            choice_id: choiceId,
            trip_id: tripId
          })
        });

        if (!res.ok) {
          // Fallback: ส่งข้อความแทน
          await sendMessage(`เลือก${slotName} ${choiceId}`);
          return;
        }

        const data = await res.json();
        
        // ✅ ตรวจสอบว่า slot workflow เสร็จแล้วหรือยัง
        const agentState = data.agent_state || {};
        const slotWorkflow = agentState.slot_workflow || {};
        const currentSlot = slotWorkflow.current_slot;
        const isSlotWorkflowComplete = (
          currentSlot === "summary" || 
          agentState.step === "trip_summary" ||
          (!currentSlot && !data.slot_choices && !data.slot_intent)
        );
        
        // ✅ สร้าง bot message จาก response
        const botMessage = {
          id: Date.now() + 1,
          type: 'bot',
          text: typeof data.response === 'string' ? data.response : String(data.response || ''),
          debug: data.debug || null,
          travelSlots: data.travel_slots || null,
          searchResults: data.search_results || {},
          planChoices: data.plan_choices || [],
          agentState: data.agent_state || null,
          suggestions: data.suggestions || [],
          currentPlan: data.current_plan || null,
          tripTitle: data.trip_title || null,
          slotIntent: data.slot_intent || null,
          slotChoices: data.slot_choices || [],
        };

        appendMessageToTrip(tripId, botMessage);

        // ✅ Update state
        if (data.plan_choices) setLatestPlanChoices(data.plan_choices);
        // ✅ ตั้ง selectedPlan เฉพาะเมื่อมี current_plan และ slot workflow เสร็จแล้ว
        if (data.current_plan && isSlotWorkflowComplete) {
          setSelectedPlan(data.current_plan);
          setSelectedTravelSlots(data.travel_slots || null);
        } else {
          setSelectedPlan(null);
          setSelectedTravelSlots(null);
        }
        if (data.trip_title) setTripTitle(tripId, data.trip_title);
        
        return;
      }
      
      // ✅ ถ้ามี currentPlan → แก้ไข slot (editing mode)
      const updatedPlan = { ...currentPlan };
      
      // ✅ Check if this is segment replacement (from editing specific segment)
      const agentState = message?.agentState;
      const targetSegments = agentState?.target_segments;
      
      if (slotType === 'hotel' && targetSegments && Array.isArray(targetSegments) && targetSegments.length > 0) {
        // ✅ This is replacing specific hotel segments
        const hotelSegments = [...(updatedPlan.hotel?.segments || [])];
        const chosenHotel = slotChoice.hotel;
        
        // Replace specific segments
        targetSegments.forEach(segIdx => {
          if (segIdx >= 0 && segIdx < hotelSegments.length) {
            // ✅ Replace only this segment, keep segment-specific info if needed
            const originalSeg = hotelSegments[segIdx];
            hotelSegments[segIdx] = {
              ...chosenHotel,
              // Keep segment-specific info
              nights: originalSeg.nights || chosenHotel.nights,
              cityCode: originalSeg.cityCode || chosenHotel.cityCode,
            };
          }
        });
        
        // Recalculate price
        const newPrice = hotelSegments.reduce((sum, seg) => {
          return sum + (seg.price_total || seg.price || 0);
        }, 0);
        
        updatedPlan.hotel = {
          ...updatedPlan.hotel,
          segments: hotelSegments,
          price_total: newPrice,
        };
        
        updatedPlan.total_price = 
          (updatedPlan.flight?.total_price || 0) + 
          newPrice + 
          (updatedPlan.transport?.price || 0);
        
        setSelectedPlan(updatedPlan);
        
        // ✅ Send message with segment info
        const segmentNums = targetSegments.map(i => i + 1).join(', ');
        await sendMessage(`เลือกที่พัก ${choiceId} สำหรับ segment ${segmentNums}`);
        return;
      }
      
      if (slotType === 'flight' && targetSegments && Array.isArray(targetSegments) && targetSegments.length > 0) {
        // ✅ This is replacing specific flight segments
        const flightSegments = [...(updatedPlan.flight?.segments || [])];
        const chosenFlight = slotChoice.flight;
        const chosenSegments = chosenFlight.segments || [];
        
        // ✅ Validate connection between segments
        for (let i = 0; i < targetSegments.length; i++) {
          const segIdx = targetSegments[i];
          if (segIdx >= 0 && segIdx < flightSegments.length) {
            const originalSeg = flightSegments[segIdx];
            const newSeg = chosenSegments[i] || chosenSegments[0]; // Use first segment if multiple
            
            // ✅ Check connection
            // Segment ก่อนหน้า (ถ้ามี) ต้องไปถึง origin ของ segment ใหม่
            if (segIdx > 0) {
              const prevSeg = flightSegments[segIdx - 1];
              if (prevSeg.to !== newSeg.from) {
                alert(`⚠️ Segment ${segIdx + 1} ไม่เชื่อมต่อกับ segment ${segIdx}\n${prevSeg.to} → ${newSeg.from}`);
                setIsTyping(false);
                return;
              }
            }
            
            // Segment ถัดไป (ถ้ามี) ต้องมาจาก destination ของ segment ใหม่
            if (segIdx < flightSegments.length - 1) {
              const nextSeg = flightSegments[segIdx + 1];
              if (newSeg.to !== nextSeg.from) {
                alert(`⚠️ Segment ${segIdx + 1} ไม่เชื่อมต่อกับ segment ${segIdx + 2}\n${newSeg.to} → ${nextSeg.from}`);
                setIsTyping(false);
                return;
              }
            }
            
            // ✅ Replace segment
            flightSegments[segIdx] = newSeg;
          }
        }
        
        // Recalculate flight price
        const newPrice = chosenFlight.total_price || 
          flightSegments.reduce((sum, seg) => sum + (seg.price || 0), 0);
        
        // Recalculate total duration
        const totalDuration = flightSegments.reduce((sum, seg) => {
          return sum + (seg.duration_sec || 0);
        }, 0);
        
        updatedPlan.flight = {
          ...updatedPlan.flight,
          segments: flightSegments,
          total_price: newPrice,
          total_duration_sec: totalDuration,
          // Update other flight metadata
          is_non_stop: flightSegments.length === 1,
          num_stops: flightSegments.length - 1,
        };
        
        updatedPlan.total_price = 
          newPrice + 
          (updatedPlan.hotel?.price_total || 0) + 
          (updatedPlan.transport?.price || 0);
        
        setSelectedPlan(updatedPlan);
        
        // ✅ Send to backend
        const segmentNums = targetSegments.map(i => i + 1).join(', ');
        await sendMessage(`เลือกไฟลต์ ${choiceId} สำหรับ segment ${segmentNums}`);
        return;
      }
      
      // ✅ General replacement (replace entire slot)
      if (slotType === 'flight' && slotChoice?.flight) {
        updatedPlan.flight = slotChoice.flight;
      } else if (slotType === 'hotel' && slotChoice?.hotel) {
        updatedPlan.hotel = slotChoice.hotel;
      } else if (slotType === 'transport' && slotChoice?.transport) {
        updatedPlan.transport = slotChoice.transport;
      }
      
      // Recalculate total price
      const flightPrice = updatedPlan.flight?.total_price || 0;
      const hotelPrice = updatedPlan.hotel?.price_total || 0;
      const transportPrice = updatedPlan.transport?.price || 0;
      updatedPlan.total_price = flightPrice + hotelPrice + transportPrice;
      
      setSelectedPlan(updatedPlan);
      
      // Send message to backend to update
      await sendMessage(`เลือก${slotType === 'flight' ? 'ไฟลต์' : slotType === 'hotel' ? 'ที่พัก' : 'การเดินทาง'} ${choiceId}`);
    } catch (error) {
      console.error('Error selecting slot choice:', error);
    } finally {
      setIsTyping(false);
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

    // ✅ เพิ่มข้อความฝั่งผู้ใช้ว่าเลือกช้อยส์ X
    const userMessage = {
      id: Date.now(),
      type: 'user',
      text: `เลือกช้อยส์ ${choiceId}`
    };
    appendMessageToTrip(tripId, userMessage);

    setIsTyping(true);

    try {
      // ✅ ถ้า backend มี /api/select_choice จะเลือกได้ทันทีแบบไม่ต้องส่งข้อความ
      const res = await fetch(`${API_BASE_URL}/api/select_choice`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        credentials: 'include',
        body: JSON.stringify({
          user_id: userId,
          choice_id: choiceId,
          trip_id: tripId
        })
      });

      // fallback ถ้า endpoint ไม่มี
      if (!res.ok) {
        setIsTyping(false);
        sendMessage(`เลือกช้อยส์ ${choiceId}`);
        return;
      }

      const data = await res.json();
      
      // Debug: log response data
      console.log('📥 select_choice response:', {
        hasCurrentPlan: !!data.current_plan,
        currentPlanKeys: data.current_plan ? Object.keys(data.current_plan) : [],
        agentState: data.agent_state,
        planChoicesCount: data.plan_choices?.length || 0,
        planChoices: data.plan_choices,
        response: data.response,
        choiceId: choiceId
      });
      
      // ✅ If no plan_choices, try to get from latest message
      if (!data.plan_choices || data.plan_choices.length === 0) {
        console.warn('⚠️ No plan_choices in response, checking latest message...');
        const latestBotMessage = [...(activeTrip?.messages || [])]
          .slice()
          .reverse()
          .find(m => m.type === 'bot' && m.planChoices && m.planChoices.length > 0);
        
        if (latestBotMessage?.planChoices) {
          console.log('✅ Found plan_choices in latest message:', latestBotMessage.planChoices.length);
          data.plan_choices = latestBotMessage.planChoices;
          
          // Try to find the choice by id
          const foundChoice = latestBotMessage.planChoices.find(p => {
            const pId = typeof p.id === 'number' ? p.id : (typeof p.get === 'function' ? p.get('id') : p.id);
            return parseInt(pId) === parseInt(choiceId);
          });
          if (foundChoice && !data.current_plan) {
            console.log('✅ Found choice in latest message, using as current_plan');
            data.current_plan = foundChoice;
          }
        }
      }
      
      // ✅ If still no current_plan but we have plan_choices, try to find by choice_id
      if (!data.current_plan && data.plan_choices && data.plan_choices.length > 0) {
        const foundChoice = data.plan_choices.find(p => {
          const pId = typeof p.id === 'number' ? p.id : (typeof p.get === 'function' ? p.get('id') : p.id);
          return parseInt(pId) === parseInt(choiceId);
        });
        if (foundChoice) {
          console.log('✅ Found choice in plan_choices, using as current_plan');
          data.current_plan = foundChoice;
        }
      }

      const botMessage = {
        id: Date.now() + 1,
        type: 'bot',
        text: typeof data.response === 'string' ? data.response : String(data.response || ''),
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
      
      // ✅ ตรวจสอบว่า slot workflow เสร็จแล้วหรือยัง
      const agentState = data.agent_state || {};
      const slotWorkflow = agentState.slot_workflow || {};
      const currentSlot = slotWorkflow.current_slot;
      const isSlotWorkflowComplete = (
        currentSlot === "summary" || 
        agentState.step === "trip_summary" ||
        (!currentSlot && !data.slot_choices && !data.slot_intent)
      );
      
      // ✅ ตั้ง selectedPlan เฉพาะเมื่อมี current_plan และ slot workflow เสร็จแล้ว
      if (data.current_plan && isSlotWorkflowComplete) {
        setSelectedPlan(data.current_plan);
        setSelectedTravelSlots(data.travel_slots || null);
        
        // Debug: log selection
        console.log('✅ Plan selected:', {
          choiceId,
          hasCurrentPlan: !!data.current_plan,
          agentState: data.agent_state,
          travelSlots: !!data.travel_slots,
          isSlotWorkflowComplete
        });
      } else {
        // ✅ Clear old selectedPlan if no current_plan หรือยังอยู่ใน slot workflow
        setSelectedPlan(null);
        setSelectedTravelSlots(null);
        console.warn('⚠️ No current_plan or slot workflow not complete:', {
          hasCurrentPlan: !!data.current_plan,
          currentSlot,
          isSlotWorkflowComplete
        });
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

  // ===== Slot-based editing - พิมพ์ในแชทได้เลย ไม่ต้องมี popup =====

  const handleConfirmBooking = async () => {
    const tripId = activeTrip?.tripId;
    if (!tripId) return;

    setIsBooking(true);
    setBookingResult(null);
    setIsTyping(true);
    
    try {
      // Step 1: Create booking (pending payment)
      const res = await fetch(`${API_BASE_URL}/api/booking/create`, {
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
        const result = {
          ok: false,
          message: `❌ สร้างการจองไม่สำเร็จ: ${errorMsg}`,
          detail: data?.detail || errorMsg,
        };
        setBookingResult(result);
        appendMessageToTrip(tripId, {
          id: Date.now() + 1,
          type: 'bot',
          text: typeof result.message === 'string' ? result.message : String(result.message || ''),
        });
        return;
      }
      
      // Success - show booking created, ready for payment
      const result = {
        ok: true,
        message: data?.message || '✅ สร้างการจองสำเร็จ',
        booking_id: data?.booking_id || null,
        status: data?.status || 'pending_payment',
        total_price: data?.total_price || 0,
        currency: data?.currency || 'THB',
        needs_payment: true,
      };
      setBookingResult(result);
      const messageText = typeof result.message === 'string' ? result.message : String(result.message || '');
      appendMessageToTrip(tripId, {
        id: Date.now() + 1,
        type: 'bot',
        text: messageText + '\nกรุณาชำระเงินเพื่อยืนยันการจอง\n\n📋 คุณสามารถดูรายการจองได้ที่ "My Bookings"',
        agentState: { intent: 'booking', step: 'pending_payment', steps: [] },
      });
    } catch (error) {
      const result = {
        ok: false,
        message: `❌ เกิดข้อผิดพลาด: ${error.message || 'Unknown error'}`,
        detail: error.message,
      };
      setBookingResult(result);
    } finally {
      setIsBooking(false);
      setIsTyping(false);
    }
  };

  const handlePayment = async (bookingId) => {
    setIsBooking(true);
    setBookingResult(null);
    
    try {
      const res = await fetch(`${API_BASE_URL}/api/booking/payment?booking_id=${bookingId}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        credentials: 'include',
      });
      
      const data = await res.json().catch(() => null);
      
      if (!res.ok) {
        const msg = (data && (data.detail?.message || data.detail?.detail || data.detail || data.message)) || 'Payment failed';
        const errorMsg = typeof msg === 'string' ? msg : JSON.stringify(msg);
        const result = {
          ok: false,
          message: `❌ ชำระเงินไม่สำเร็จ: ${errorMsg}`,
          detail: data?.detail || errorMsg,
        };
        setBookingResult(result);
        return;
      }
      
      // Success - payment and booking confirmed
      const result = {
        ok: true,
        message: data?.message || '✅ ชำระเงินและจองสำเร็จ',
        booking_reference: data?.booking_reference || null,
        status: data?.status || 'confirmed',
        needs_payment: false,
      };
      setBookingResult(result);
      
      // Show success message in chat
      const tripId = activeTrip?.tripId;
      if (tripId) {
        const messageText = typeof result.message === 'string' ? result.message : String(result.message || '');
        appendMessageToTrip(tripId, {
          id: Date.now() + 1,
          type: 'bot',
          text: messageText + 
                (result.booking_reference ? `\n📋 หมายเลขการจอง: ${result.booking_reference}` : '') +
                '\n\n📋 คุณสามารถดูรายการจองได้ที่ "My Bookings"',
          agentState: { intent: 'booking', step: 'completed', steps: [] },
        });
      }
    } catch (error) {
      const result = {
        ok: false,
        message: `❌ เกิดข้อผิดพลาด: ${error.message || 'Unknown error'}`,
        detail: error.message,
      };
      setBookingResult(result);
    } finally {
      setIsBooking(false);
    }
  };
  
  const handleEditUserProfile = () => {
    // TODO: Open user profile edit modal/form
    alert('ฟีเจอร์แก้ไขข้อมูลผู้ใช้จะเปิดใช้งานเร็วๆ นี้');
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
      // Prioritize messages with choice_selected step (just selected)
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
          agentState: lastBotWithPlan.agentState || { intent: 'edit', step: 'choice_selected', steps: [] },
        };
      }
      
      // If not found but we have selectedPlan, create a virtual message
      return {
        id: Date.now(),
        type: 'bot',
        text: 'แพลนที่เลือก',
        currentPlan: selectedPlan,
        travelSlots: selectedTravelSlots,
        agentState: { intent: 'edit', step: 'choice_selected', steps: [] },
      };
    }
    
    // Otherwise, find from messages (excluding error messages)
    // Prioritize messages with choice_selected step
    const choiceSelectedMsg = [...messages]
      .slice()
      .reverse()
      .find(m => 
        m.type === 'bot' && 
        m.currentPlan &&
        m.agentState?.step === 'choice_selected' &&
        !m.text?.includes('ยังไม่มีช้อยส์')
      );
    
    if (choiceSelectedMsg) {
      return choiceSelectedMsg;
    }
    
    // Fallback to any message with currentPlan
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
    // ✅ แสดงสถานะการทำงานแบบ realtime จาก SSE
    if (agentStatus && agentStatus.message) {
      return agentStatus.message;
    }
    
    // Fallback: ใช้ agent_state ถ้าไม่มี realtime status
    if (!currentAgentState) return 'กำลังเริ่มต้น...';

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
      <AppHeader
        activeTab="ai"
        user={user}
        onTabChange={(tab) => {
          // Handle navigation to other tabs from AI page
          if (tab === 'flights' && onNavigateToFlights) {
            onNavigateToFlights();
          } else if (tab === 'hotels' && onNavigateToHotels) {
            onNavigateToHotels();
          } else if (tab === 'car-rentals' && onNavigateToCarRentals) {
            onNavigateToCarRentals();
          } else {
            setActiveTab(tab);
          }
        }}
        onNavigateToBookings={onNavigateToBookings}
        onNavigateToAI={() => {
          // Already on AI page, just focus input
          const chatInput = document.querySelector('.chat-input-textarea');
          if (chatInput) {
            chatInput.focus();
          }
        }}
        onLogout={onLogout}
        onSignIn={onSignIn}
        onAIClick={() => {
          // Scroll to chat input or focus on input
          const chatInput = document.querySelector('.chat-input-textarea');
          if (chatInput) {
            chatInput.focus();
          }
        }}
        notificationCount={0}
        isConnected={isConnected}
        notifications={[]}
      />

      {/* Main: Sidebar + Chat */}
      <main 
        className={`chat-main chat-main-split ${isSidebarOpen ? 'sidebar-open' : 'sidebar-closed'}`}
        onTouchStart={onTouchStart}
        onTouchMove={onTouchMove}
        onTouchEnd={onTouchEnd}
      >
        {/* Overlay สำหรับ mobile เมื่อ sidebar เปิด */}
        {isSidebarOpen && (
          <div 
            className="sidebar-overlay-mobile"
            onClick={() => setIsSidebarOpen(false)}
          />
        )}
        
        {/* ===== Sidebar: Trip History ===== */}
        <aside className={`trip-sidebar ${isSidebarOpen ? 'trip-sidebar-open' : 'trip-sidebar-closed'}`}>
          <div className="trip-sidebar-header">
            <div className="trip-sidebar-title">ประวัติทริป</div>
            <div className="trip-sidebar-header-actions">
              <button className="trip-new-btn" onClick={handleNewTrip}>
                + ทริปใหม่
              </button>
              {/* ปุ่ม toggle แสดงเฉพาะ mobile */}
              <button 
                className="trip-sidebar-toggle mobile-only"
                onClick={() => setIsSidebarOpen(!isSidebarOpen)}
                title={isSidebarOpen ? 'ซ่อนประวัติทริป' : 'แสดงประวัติทริป'}
              >
                {isSidebarOpen ? '◀' : '▶'}
              </button>
            </div>
          </div>

          {isSidebarOpen && (
            <>
              <div className="trip-list">
                {sortedTrips.map((t) => {
                  const isActive = t.tripId === activeTrip?.tripId;
                  const isEditing = editingTripId === t.tripId;
                  return (
                    <div
                      key={t.tripId}
                      className={`trip-item ${isActive ? 'trip-item-active' : ''} ${t.pinned ? 'trip-item-pinned' : ''}`}
                      onClick={() => !isEditing && setActiveTripId(t.tripId)}
                      title={t.title}
                    >
                      <div className="trip-item-top">
                        {isEditing ? (
                          <input
                            type="text"
                            value={editingTripName}
                            onChange={(e) => setEditingTripName(e.target.value)}
                            onKeyPress={(e) => {
                              if (e.key === 'Enter') {
                                handleSaveTripName(t.tripId);
                              } else if (e.key === 'Escape') {
                                handleCancelEditTripName();
                              }
                            }}
                            onBlur={() => handleSaveTripName(t.tripId)}
                            className="trip-edit-input"
                            autoFocus
                            onClick={(e) => e.stopPropagation()}
                          />
                        ) : (
                          <div className="trip-item-title-wrapper">
                            {t.pinned && <span className="trip-pin-icon" title="ปักหมุด">📌</span>}
                            <div className="trip-item-title">
                              {t.title || 'ทริป'}
                            </div>
                          </div>
                        )}
                        <div className="trip-item-actions">
                          {!isEditing && (
                            <>
                              <button
                                className="trip-edit-btn"
                                onClick={(e) => { 
                                  e.stopPropagation(); 
                                  handleEditTripName(t.tripId, t.title); 
                                }}
                                title="แก้ไขชื่อทริป"
                              >
                                ✏️
                              </button>
                              <button
                                className={`trip-pin-btn ${t.pinned ? 'trip-pin-btn-active' : ''}`}
                                onClick={(e) => { 
                                  e.stopPropagation(); 
                                  handleTogglePin(t.tripId); 
                                }}
                                title={t.pinned ? 'ยกเลิกปักหมุด' : 'ปักหมุดทริป'}
                              >
                                📌
                              </button>
                            </>
                          )}
                          <button
                            className="trip-delete-btn"
                            onClick={(e) => { e.stopPropagation(); handleDeleteTrip(t.tripId); }}
                            title="ลบทริป"
                          >
                            ✕
                          </button>
                        </div>
                      </div>
                      {!isEditing && (
                        <>
                          <div className="trip-item-sub">อัปเดต: {shortDate(t.updatedAt)}</div>
                          <div className="trip-item-sub">ข้อความ: {(t.messages?.length || 0) - 1}</div>
                        </>
                      )}
                    </div>
                  );
                })}
              </div>

              <div className="trip-sidebar-footer">
                {/* Connection status moved to AI button in header */}
              </div>
            </>
          )}
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
            {/* Live Status Indicator */}
            <div className="agent-live-status" style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
              {agentStatus ? (
                <>
                  <span className="agent-live-status-dot" style={{ width: 8, height: 8, borderRadius: '50%', background: '#4ade80', display: 'inline-block', boxShadow: '0 0 8px #4ade80' }} />
                  <span className="agent-live-status-text" style={{ fontSize: '12px', color: '#64748b', fontWeight: '500' }}>
                    {agentStatus.status === 'completed' ? 'พร้อมตอบแล้ว' : agentStatus.message || 'กำลังประมวลผล...'}
                  </span>
                </>
              ) : isTyping && (
                <>
                  <span className="agent-live-status-dot" style={{ width: 8, height: 8, borderRadius: '50%', background: '#fbbf24', display: 'inline-block', boxShadow: '0 0 8px #fbbf24' }} />
                  <span className="agent-live-status-text" style={{ fontSize: '12px', color: '#64748b', fontWeight: '500' }}>
                    กำลังประมวลผลแบบ Real-time...
                  </span>
                </>
              )}
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
                    <div className={`message-bubble ${message.type === 'user' ? 'message-user' : 'message-bot'} ${
                      message.type === 'bot' && (
                        formatMessageText(message.text)?.includes('❌') || 
                        formatMessageText(message.text)?.includes('ไม่สำเร็จ') ||
                        formatMessageText(message.text)?.includes('Error:')
                      ) ? 'message-error' : ''
                    } ${
                      message.type === 'bot' && (
                        formatMessageText(message.text)?.includes('ยังไม่มีซ้อยส์') ||
                        formatMessageText(message.text)?.includes('ไม่มีช้อยส์') ||
                        formatMessageText(message.text)?.includes('ลองพิมพ์ทริป')
                      ) ? 'message-empty-state' : ''
                    }`}>
                      {/* ข้อความหลัก */}
                      <p className="message-text">{formatMessageText(message.text)}</p>

                      {/* Reasoning light (Level 3) */}
                      {message.reasoning && (
                        <div className="reasoning-light" style={{
                          marginTop: '8px',
                          padding: '8px 12px',
                          background: 'rgba(255, 255, 255, 0.1)',
                          borderRadius: '8px',
                          fontSize: '13px',
                          fontStyle: 'italic',
                          color: 'rgba(255, 255, 255, 0.9)'
                        }}>
                          💡 {message.reasoning}
                        </div>
                      )}

                      {/* Memory suggestions toggle (Level 3) */}
                      {message.memorySuggestions && message.memorySuggestions.length > 0 && (
                        <div className="memory-toggle" style={{
                          marginTop: '12px',
                          padding: '12px',
                          background: 'rgba(255, 255, 255, 0.15)',
                          borderRadius: '8px',
                          fontSize: '13px'
                        }}>
                          <div style={{ marginBottom: '8px', fontWeight: '600' }}>
                            💾 จำไว้ใช้ครั้งหน้าหรือไม่?
                          </div>
                          {message.memorySuggestions.map((suggestion, idx) => (
                            <div key={idx} style={{
                              marginBottom: '8px',
                              padding: '8px',
                              background: 'rgba(255, 255, 255, 0.1)',
                              borderRadius: '6px',
                              display: 'flex',
                              justifyContent: 'space-between',
                              alignItems: 'center'
                            }}>
                              <span>{suggestion.description || suggestion.key}: {suggestion.value}</span>
                              <button
                                onClick={() => handleMemoryCommit(suggestion, message.id)}
                                style={{
                                  padding: '4px 12px',
                                  background: 'rgba(255, 255, 255, 0.2)',
                                  border: '1px solid rgba(255, 255, 255, 0.3)',
                                  borderRadius: '4px',
                                  color: '#fff',
                                  cursor: 'pointer',
                                  fontSize: '12px'
                                }}
                              >
                                จำไว้
                              </button>
                            </div>
                          ))}
                        </div>
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
                      {/* Show TripSummaryCard ONLY when slot workflow is complete (trip_summary) */}
                      {(() => {
                        const hasCurrentPlan = message.currentPlan;
                        const hasSelectedPlan = selectedPlan;
                        const agentStep = message.agentState?.step;
                        const slotWorkflow = message.agentState?.slot_workflow || {};
                        const currentSlot = slotWorkflow.current_slot;
                        const hasSlotChoices = message.slotChoices && message.slotChoices.length > 0;
                        const hasSlotIntent = message.slotIntent;
                        
                        // ✅ ตรวจสอบว่าทริปเสร็จสมบูรณ์จริงหรือไม่ (ทุก segment ต้อง confirmed)
                        const plan = selectedPlan || message.currentPlan;
                        const isPlanComplete = plan && (
                          (plan.flights || []).length > 0 || 
                          (plan.accommodations || []).length > 0 || 
                          (plan.ground_transport || []).length > 0
                        ) && [
                          ...(plan.flights || []),
                          ...(plan.accommodations || []),
                          ...(plan.ground_transport || [])
                        ].every(seg => seg.status === 'confirmed');
                        
                        // ✅ ตรวจสอบว่า slot workflow เสร็จแล้วหรือยัง
                        // แสดง TripSummary เฉพาะเมื่อ:
                        // 1. แผนเสร็จสมบูรณ์ (isPlanComplete)
                        // 2. หรือ backend บอกว่าเป็น trip_summary
                        // 3. และไม่มี slot choices ที่กำลังแสดงอยู่
                        const isSlotWorkflowComplete = (
                          isPlanComplete ||
                          currentSlot === "summary" || 
                          agentStep === "trip_summary"
                        ) && (!hasSlotChoices && !hasSlotIntent);
                        
                        // ✅ ไม่แสดง TripSummary ถ้ายังอยู่ใน slot workflow (กำลังเลือก slot)
                        const isInSlotWorkflow = (
                          currentSlot && 
                          currentSlot !== "summary" && 
                          (hasSlotChoices || hasSlotIntent)
                        );
                        
                        const isValidMessage = message.agentState?.step !== 'no_previous_choices' &&
                                             !message.text?.includes('ยังไม่มีช้อยส์');
                        
                        // Debug log
                        if (hasCurrentPlan || hasSelectedPlan) {
                          console.log('🔍 TripSummaryCard display check:', {
                            messageId: message.id,
                            hasCurrentPlan,
                            hasSelectedPlan,
                            agentStep,
                            currentSlot,
                            hasSlotChoices,
                            hasSlotIntent,
                            isSlotWorkflowComplete,
                            isInSlotWorkflow,
                            isValidMessage
                          });
                        }
                        
                        // ✅ แสดง TripSummaryCard เฉพาะเมื่อ:
                        // 1. เป็น bot message
                        // 2. มี currentPlan หรือ selectedPlan
                        // 3. เป็น valid message (ไม่ใช่ error)
                        // 4. slot workflow เสร็จแล้ว (ไม่ใช่กำลังเลือก slot)
                        const shouldShow = message.type === 'bot' && 
                               (hasCurrentPlan || hasSelectedPlan) &&
                               isValidMessage &&
                               isSlotWorkflowComplete &&
                               !isInSlotWorkflow;
                        
                        if (shouldShow && (hasCurrentPlan || hasSelectedPlan)) {
                          console.log('✅ Showing TripSummaryCard for message:', message.id, {
                            hasCurrentPlan,
                            hasSelectedPlan,
                            agentStep,
                            currentSlot,
                            isSlotWorkflowComplete
                          });
                        } else if ((hasCurrentPlan || hasSelectedPlan) && isValidMessage) {
                          console.warn('⚠️ TripSummaryCard NOT showing for message:', message.id, {
                            hasCurrentPlan,
                            hasSelectedPlan,
                            agentStep,
                            currentSlot,
                            isSlotWorkflowComplete,
                            isInSlotWorkflow,
                            hasSlotChoices,
                            hasSlotIntent
                          });
                        }
                        
                        return shouldShow;
                      })() && (
                        <div className="summary-flow">
                          <TripSummaryCard 
                            plan={selectedPlan || message.currentPlan} 
                            travelSlots={selectedTravelSlots || message.travelSlots} 
                          />
                          {/* Slot-based editing cards */}
                          <div className="slots-container">
                            <FlightSlotCard 
                              flight={selectedPlan?.flight || message.currentPlan?.flight} 
                            />
                            <TransportSlotCard 
                              transport={selectedPlan?.transport || message.currentPlan?.transport} 
                            />
                            <HotelSlotCard 
                              hotel={selectedPlan?.hotel || message.currentPlan?.hotel}
                              travelSlots={selectedTravelSlots || message.travelSlots}
                            />
                          </div>
                          {/* ✅ Final Trip Summary - แสดงก่อนจอง */}
                          <FinalTripSummary
                            plan={selectedPlan || message.currentPlan}
                            travelSlots={selectedTravelSlots || message.travelSlots}
                            userProfile={userProfile}
                          />
                          <UserInfoCard 
                            userProfile={userProfile} 
                            onEdit={handleEditUserProfile}
                          />
                          <ConfirmBookingCard
                            canBook={!!selectedPlan && !!userProfile}
                            onConfirm={handleConfirmBooking}
                            onPayment={handlePayment}
                            note="ระบบจะจองเฉพาะ Amadeus Sandbox (test) เท่านั้น"
                            isBooking={isBooking}
                            bookingResult={bookingResult}
                          />
                        </div>
                      )}

                      {/* ✅ แสดง Slot Choices (เมื่อกำลังแก้ไข slot) */}
                      {message.slotChoices && message.slotChoices.length > 0 && message.slotIntent && (
                        <div className="plan-choices-block">
                          <div className="plan-choices-header">
                            {message.slotIntent === 'flight' && '✈️ ตัวเลือกเที่ยวบิน'}
                            {message.slotIntent === 'hotel' && '🏨 ตัวเลือกที่พัก'}
                            {message.slotIntent === 'transport' && '🚗 ตัวเลือกการเดินทาง'}
                            {!['flight', 'hotel', 'transport'].includes(message.slotIntent) && 'ตัวเลือก'}
                            {' '}({message.slotChoices.length} รายการ)
                          </div>
                          <div className="plan-choices-grid">
                            {message.slotChoices.map((choice) => (
                              <PlanChoiceCard
                                key={choice.id}
                                choice={choice}
                                onSelect={(id) => handleSelectSlotChoice(id, message.slotIntent, choice, message)}
                              />
                            ))}
                          </div>
                        </div>
                      )}

                      {/* ✅ แสดง PlanChoiceCard เฉพาะเมื่อยังไม่ได้เลือกช้อยส์ (full plan choices) */}
                      {/* การ์ดแผนเที่ยวจาก planChoices */}
                      {(() => {
                        const hasPlanChoices = message.planChoices && 
                          Array.isArray(message.planChoices) && 
                          message.planChoices.length > 0;
                        const hasSlotChoices = message.slotChoices && message.slotChoices.length > 0;
                        // ✅ ตรวจสอบ currentPlan อย่างถูกต้อง (ต้องเป็น object ที่มีข้อมูล ไม่ใช่ null, undefined, หรือ object ว่าง)
                        const hasCurrentPlan = message.currentPlan && 
                          typeof message.currentPlan === 'object' && 
                          Object.keys(message.currentPlan).length > 0;
                        const agentStep = message.agentState?.step;
                        
                        // Debug log
                        if (hasPlanChoices) {
                          console.log('🔍 PlanChoices display check:', {
                            hasPlanChoices,
                            hasSlotChoices,
                            hasCurrentPlan,
                            agentStep,
                            planChoicesCount: message.planChoices.length
                          });
                        }
                        
                        // ✅ แสดง planChoices เฉพาะเมื่อ:
                        // 1. มี planChoices และ
                        // 2. ไม่มี slotChoices หรือไม่มี slotIntent (เพื่อให้แสดง slotChoices ก่อน) และ
                        // 3. ไม่มี currentPlan (ถ้ามี currentPlan แสดงว่าเลือกแล้ว ไม่ต้องแสดง planChoices)
                        // ✅ สำคัญ: ถ้ามี slotChoices และ slotIntent ให้แสดง slotChoices เท่านั้น ไม่แสดง planChoices
                        const shouldShowPlanChoices = hasPlanChoices && 
                               (!hasSlotChoices || !message.slotIntent) && 
                               !hasCurrentPlan;
                        
                        // Debug log
                        if (hasPlanChoices) {
                          console.log('🔍 PlanChoices display decision:', {
                            hasPlanChoices,
                            hasSlotChoices,
                            hasSlotIntent: !!message.slotIntent,
                            hasCurrentPlan,
                            shouldShowPlanChoices,
                            agentStep,
                            planChoicesCount: message.planChoices.length
                          });
                        }
                        
                        return shouldShowPlanChoices ? (
                          <div className="plan-choices-block">
                            <div className="plan-choices-header">
                              แผนเที่ยวที่จัดให้คุณเลือกทั้งหมด {message.planChoices.length} ช้อยส์
                            </div>
                            <div className="plan-choices-grid">
                              {message.planChoices.map((choice) => (
                                <PlanChoiceCard
                                  key={choice.id || `choice-${Math.random()}`}
                                  choice={choice}
                                  onSelect={handleSelectPlanChoice}
                                />
                              ))}
                            </div>
                          </div>
                        ) : null;
                      })()}

                      {/* ✅ ซ่อน suggestion chips ตามที่ผู้ใช้ขอ */}
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

          {/* Trip Summary UI จะถูกแสดงแบบ seamless อยู่ใน bubble ของบอท "ข้อความล่าสุดที่มี currentPlan" */}


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
                className={`btn-mic ${isVoiceMode ? 'btn-mic-recording' : ''}`}
                title={isVoiceMode ? 'กดเพื่อหยุดการสนทนาด้วยเสียง' : 'กดเพื่อเริ่มการสนทนาด้วยเสียง'}
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

            {isVoiceMode && (
              <div className="recording-status">
                {isRecording ? '🎤 กำลังฟัง... พูดได้เลย' : '⏸️ รอ Agent ตอบ...'}
              </div>
            )}
            <div className="powered-by">Powered by Gemini + Amadeus อาจมีข้อผิดพลาด ควรตรวจสอบข้อมูลสำคัญ</div>
          </div>
        </div>
      </main>
    </div>
  );
}
