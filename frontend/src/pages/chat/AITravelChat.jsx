import React, { useState, useRef, useEffect, useMemo, useCallback } from 'react';
import Swal from 'sweetalert2';
import './AITravelChat.css';
import AppHeader from '../../components/common/AppHeader';
import { useTheme } from '../../context/ThemeContext';
import { useFontSize } from '../../context/FontSizeContext';
import { useLanguage } from '../../context/LanguageContext';
import { formatPriceInThb } from '../../utils/currency';

class ChatErrorBoundary extends React.Component {
  constructor(props) {
    super(props);
    this.state = { hasError: false, error: null, errorInfo: null };
  }

  static getDerivedStateFromError(error) {
    return { hasError: true };
  }

  componentDidCatch(error, errorInfo) {
    console.error('Chat Error Boundary caught an error:', error, errorInfo);
    // #region frontend error debug log (H1) - ใช้ sendTelemetry จะส่งเฉพาะเมื่อ VITE_TELEMETRY_ENABLED=true
    sendTelemetry({ location: 'AITravelChat.jsx:ChatErrorBoundary.componentDidCatch', message: 'ErrorBoundary caught error', data: { errorMessage: String(error?.message), errorName: error?.name, componentStack: (errorInfo?.componentStack || '').slice(0, 500) }, timestamp: Date.now(), runId: 'run1', hypothesisId: 'H1' });
    // #endregion
    this.setState({
      error: error,
      errorInfo: errorInfo
    });
  }

  render() {
    if (this.state.hasError) {
      return (
        <div style={{
          padding: '2rem',
          textAlign: 'center',
          color: '#fff',
          background: 'rgba(220, 38, 38, 0.1)',
          borderRadius: '8px',
          margin: '1rem'
        }}>
          <h3 style={{ color: '#ef4444', marginBottom: '1rem' }}>⚠️ เกิดข้อผิดพลาดในการแสดงผล</h3>
          <p style={{ marginBottom: '1rem', opacity: 0.8 }}>
            เกิดข้อผิดพลาดที่ไม่คาดคิด กรุณารีเฟรชหน้าหรือลองใหม่อีกครั้ง
          </p>
          <button
            onClick={() => {
              this.setState({ hasError: false, error: null, errorInfo: null });
              window.location.reload();
            }}
            style={{
              padding: '8px 16px',
              background: '#2563eb',
              color: '#fff',
              border: 'none',
              borderRadius: '6px',
              cursor: 'pointer',
              fontSize: '14px'
            }}
          >
            🔄 รีเฟรชหน้า
          </button>
          {process.env.NODE_ENV === 'development' && this.state.error && (
            <details style={{ marginTop: '1rem', textAlign: 'left', fontSize: '12px', opacity: 0.7 }}>
              <summary style={{ cursor: 'pointer', marginBottom: '0.5rem' }}>รายละเอียดข้อผิดพลาด (Development)</summary>
              <pre style={{ background: 'rgba(0,0,0,0.3)', padding: '1rem', borderRadius: '4px', overflow: 'auto' }}>
                {this.state.error.toString()}
                {this.state.errorInfo?.componentStack}
              </pre>
            </details>
          )}
        </div>
      );
    }

    return this.props.children;
  }
}
import PlanChoiceCard from '../../components/bookings/PlanChoiceCard';
import PlanChoiceCardFlights from '../../components/bookings/PlanChoiceCardFlights';
import PlanChoiceCardHotels from '../../components/bookings/PlanChoiceCardHotels';
import PlanChoiceCardTransfer from '../../components/bookings/PlanChoiceCardTransfer';
import BookingProgressBar from '../../components/chat/BookingProgressBar';
import {
  TripSummaryCard,
  UserInfoCard,
  ConfirmBookingCard,
  FinalTripSummary,
  isLocationInThailand,
} from '../../components/bookings/TripSummaryUI';
import {
  FlightSlotCard,
  HotelSlotCard,
  TransportSlotCard,
} from '../../components/chat/SlotCards';
import { correctTypos, suggestCorrections, detectLanguage, detectLanguageMismatch } from '../../utils/textCorrection';

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? 'http://localhost:8000';

// ===== LocalStorage keys =====
const LS_TRIPS_KEY = 'ai_travel_trips_v1';
const LS_ACTIVE_TRIP_KEY = 'ai_travel_active_trip_id_v1';

// ===== Helpers =====
function nowISO() {
  return new Date().toISOString();
}

const GREETINGS = [
  "สวัสดีค่ะคุณ {name} ดิฉันคือ AI Travel Agent 💙 เล่าไอเดียทริปของคุณได้เลย",
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

let _msgSeq = 0;
function makeId(prefix = 'trip') {
  _msgSeq += 1;
  return `${prefix}_${Date.now()}_${_msgSeq}_${Math.random().toString(36).slice(2, 10)}`;
}

// ✅ Helper function for silent telemetry (optional service - fail silently)
// เปิดใช้เฉพาะเมื่อตั้ง VITE_TELEMETRY_ENABLED=true เพื่อลด request ที่ถูกยกเลิกเมื่อไม่มี ingest service
function sendTelemetry(data) {
  if (import.meta.env.VITE_TELEMETRY_ENABLED !== 'true') return;
  try {
    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), 50);
    fetch('http://127.0.0.1:7243/ingest/40f320da-1b3b-4d52-a48b-ec2dd1dbba89', {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify(data),
      signal: controller.signal,
      mode: 'no-cors'
    })
      .then(() => clearTimeout(timeoutId))
      .catch(() => { clearTimeout(timeoutId); });
  } catch (e) {
    // Silently ignore - telemetry is optional
  }
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
  const chatId = makeId('chat'); // ✅ เพิ่ม chat_id สำหรับแต่ละแชท
  return {
    tripId, // ✅ trip_id: สำหรับ 1 ทริป (1 trip = หลาย chat ได้)
    chatId, // ✅ chat_id: สำหรับแต่ละแชท (1 chat = 1 chat_id)
    title,
    createdAt: nowISO(),
    updatedAt: nowISO(),
    messages: [defaultWelcomeMessage(userName)],
    pinned: false // เพิ่ม field สำหรับปักหมุด
  };
}

export default function AITravelChat({ user, onLogout, onSignIn, initialPrompt = '', onNavigateToBookings, onNavigateToFlights, onNavigateToHotels, onNavigateToCarRentals, notificationCount = 0, notifications = [], onNavigateToProfile = null, onNavigateToSettings = null, onNavigateToHome = null, onRefreshNotifications = null, onMarkNotificationAsRead = null }) {
  // ✅ Use user.user_id (from backend) or user.id (fallback) - backend uses user_id
  const userId = user?.user_id || user?.id || 'demo_user';

  // Loading state สำหรับการโหลด sessions จาก backend (แบบ ChatGPT: โหลดรายการแชทครั้งเดียว)
  const [isLoadingSessions, setIsLoadingSessions] = useState(false);

  // ===== ระบบโหลดแชทแบบ ChatGPT =====
  // 1) โหลดรายการแชทจาก backend ครั้งเดียวเมื่อ login
  useEffect(() => {
    if (!user?.id) return;

    let cancelled = false;
    setIsLoadingSessions(true);

    const headers = {
      'Content-Type': 'application/json',
      'X-User-ID': user?.user_id || user?.id || '',
    };

    fetch(`${API_BASE_URL}/api/chat/sessions`, { headers, credentials: 'include' })
      .then((res) => res.json())
      .then((data) => {
        if (cancelled) return;
        const list = data.sessions || [];
        if (data.require_login) {
          setTrips([]);
          setIsLoadingSessions(false);
          return;
        }
        const nextTrips = list.map((s) => ({
          tripId: s.trip_id || s.chat_id,
          chatId: s.chat_id || (s.session_id && s.session_id.split('::')[1]) || s.session_id,
          title: s.title || 'การสนทนาใหม่',
          updatedAt: s.last_updated || s.created_at,
          messages: [],
          userId: user.id,
          pinned: false,
        })).filter((t) => t.chatId);

        if (nextTrips.length > 0) {
          setTrips(nextTrips);
          localStorage.setItem(LS_TRIPS_KEY, JSON.stringify(nextTrips));
        } else {
          const displayName = user?.first_name || user?.name || 'คุณ';
          const newTrip = createNewTrip('ทริปใหม่', displayName);
          newTrip.userId = user.id;
          setTrips([newTrip]);
          localStorage.setItem(LS_TRIPS_KEY, JSON.stringify([newTrip]));
        }
      })
      .catch((err) => {
        if (!cancelled) console.error('Fetch sessions error:', err);
      })
      .finally(() => {
        if (!cancelled) setIsLoadingSessions(false);
      });

    return () => { cancelled = true; };
  }, [user?.id]);

  // ===== userTrips: trip entities from /api/trips (independent from chats) =====
  const [userTrips, setUserTrips] = useState([]);
  const [isLoadingUserTrips, setIsLoadingUserTrips] = useState(false);
  const [tripSelectorOpen, setTripSelectorOpen] = useState(false);
  const tripSelectorRef = useRef(null);

  const fetchUserTrips = async () => {
    if (!user?.id) return;
    setIsLoadingUserTrips(true);
    try {
      const res = await fetch(`${API_BASE_URL}/api/trips`, {
        credentials: 'include',
        headers: { 'X-User-ID': user?.user_id || user?.id || '' },
      });
      if (res.ok) {
        const data = await res.json();
        setUserTrips(data.trips || []);
      }
    } catch (err) {
      console.error('fetchUserTrips error:', err);
    } finally {
      setIsLoadingUserTrips(false);
    }
  };

  useEffect(() => {
    fetchUserTrips();
  }, [user?.id]); // eslint-disable-line react-hooks/exhaustive-deps

  // Close trip selector on outside click
  useEffect(() => {
    const handler = (e) => {
      if (tripSelectorRef.current && !tripSelectorRef.current.contains(e.target)) {
        setTripSelectorOpen(false);
      }
    };
    document.addEventListener('mousedown', handler);
    return () => document.removeEventListener('mousedown', handler);
  }, []);

  // Register trip on backend when a new chat is created (idempotent)
  const ensureTripRegistered = async (tripId, title) => {
    if (!tripId || !user?.id) return;
    try {
      await fetch(`${API_BASE_URL}/api/trips`, {
        method: 'POST',
        credentials: 'include',
        headers: {
          'Content-Type': 'application/json',
          'X-User-ID': user?.user_id || user?.id || '',
        },
        body: JSON.stringify({ trip_id: tripId, title: title || 'ทริปใหม่' }),
      });
    } catch (err) {
      console.warn('ensureTripRegistered failed (non-fatal):', err);
    }
  };

  // Link current chat to a different trip
  const linkChatToTrip = async (tripId) => {
    const currentChat = trips.find(t => (t.chatId || t.tripId) === activeTripId);
    if (!currentChat || !tripId) return;
    const chatId = currentChat.chatId || currentChat.tripId;
    try {
      const res = await fetch(`${API_BASE_URL}/api/trips/${tripId}/link-chat`, {
        method: 'POST',
        credentials: 'include',
        headers: {
          'Content-Type': 'application/json',
          'X-User-ID': user?.user_id || user?.id || '',
        },
        body: JSON.stringify({ chat_id: chatId }),
      });
      if (res.ok) {
        // Update local state: set tripId on the active chat
        setTrips(prev => prev.map(t =>
          (t.chatId || t.tripId) === activeTripId
            ? { ...t, tripId }
            : t
        ));
        await fetchUserTrips();
        console.log(`✅ Linked chat ${chatId} to trip ${tripId}`);
      }
    } catch (err) {
      console.error('linkChatToTrip error:', err);
    }
    setTripSelectorOpen(false);
  };

  // Create new trip entity and link current chat to it
  const handleCreateAndLinkTrip = async () => {
    if (!user?.id) return;
    try {
      const res = await fetch(`${API_BASE_URL}/api/trips`, {
        method: 'POST',
        credentials: 'include',
        headers: {
          'Content-Type': 'application/json',
          'X-User-ID': user?.user_id || user?.id || '',
        },
        body: JSON.stringify({ title: 'ทริปใหม่' }),
      });
      if (res.ok) {
        const newTrip = await res.json();
        await linkChatToTrip(newTrip.trip_id);
        await fetchUserTrips();
      }
    } catch (err) {
      console.error('handleCreateAndLinkTrip error:', err);
    }
  };

  // ✅ Active tab state for navigation (switch/tab indicator)
  const [activeTab, setActiveTab] = useState('flights'); // Default to 'flights'

  // Cooldown for regenerate/refresh to prevent spam
  const REFRESH_COOLDOWN_MS = 4000;
  const lastRefreshAtRef = useRef({}); // { [messageId]: number }

  const messagesEndRef = useRef(null);
  const inputRef = useRef(null);

  // ===== Trips state (sidebar history) =====
  // ✅ SECURITY: Store trips with user_id to prevent data leakage between users
  const [trips, setTrips] = useState(() => {
    const displayName = user?.first_name || user?.name || "คุณ";
    const currentUserId = user?.id || userId;
    
    try {
      const raw = localStorage.getItem(LS_TRIPS_KEY);
      if (raw) {
        const parsed = JSON.parse(raw);
        if (Array.isArray(parsed) && parsed.length > 0) {
          // ✅ SECURITY: Filter trips by current user_id to prevent showing other users' data
          const userTrips = parsed.filter(trip => {
            // ✅ Only show trips that belong to current user
            const tripUserId = trip.userId || trip.user_id;
            if (tripUserId && tripUserId !== currentUserId) {
              console.warn(`⚠️ Filtered out trip from different user: ${trip.tripId} (user: ${tripUserId}, current: ${currentUserId})`);
              return false;
            }
            // ✅ If trip doesn't have userId, assume it's from current user (backward compatibility)
            return true;
          });
          
          if (userTrips.length > 0) {
            // ✅ Migrate old trips ที่ไม่มี chatId → เพิ่ม chatId ให้อัตโนมัติ
            const migrated = userTrips.map(trip => {
              if (!trip.chatId) {
                // ✅ ถ้าไม่มี chatId → สร้างใหม่ (ใช้ tripId เป็นฐาน)
                trip.chatId = trip.tripId || makeId('chat');
                console.log(`🔄 Migrated trip to add chatId: ${trip.tripId} → ${trip.chatId}`);
              }
              // ✅ Ensure userId is set
              if (!trip.userId && !trip.user_id) {
                trip.userId = currentUserId;
              }
              return trip;
            });
            console.log(`✅ Loaded ${migrated.length} trips for user: ${currentUserId}`);
            return migrated;
          } else {
            console.log(`ℹ️ No trips found for user: ${currentUserId}, creating new trip`);
          }
        }
      }
    } catch (e) {
      console.error('❌ Failed to load trips from localStorage:', e);
    }
    // ✅ Create new trip with userId
    const newTrip = createNewTrip('ทริปใหม่', displayName);
    newTrip.userId = currentUserId;
    return [newTrip];
  });
  
  // ✅ SECURITY: Clear trips when user changes
  useEffect(() => {
    const currentUserId = user?.id || userId;
    const tripsUserId = trips[0]?.userId || trips[0]?.user_id;
    
    // ✅ If user changed, clear trips and reload from backend
    if (currentUserId && tripsUserId && tripsUserId !== currentUserId) {
      console.warn(`🚨 SECURITY: User changed from ${tripsUserId} to ${currentUserId}, clearing trips`);
      setTrips(() => {
        const displayName = user?.first_name || user?.name || "คุณ";
        const newTrip = createNewTrip('ทริปใหม่', displayName);
        newTrip.userId = currentUserId;
        return [newTrip];
      });
      // ✅ Clear localStorage trips
      localStorage.removeItem(LS_TRIPS_KEY);
      localStorage.removeItem(LS_ACTIVE_TRIP_KEY);
      sessionStorage.removeItem('ai_travel_loaded_trips');
    }
  }, [user?.id, userId]);

  // ✅ ใช้ chatId เป็น key หลัก (เพราะแต่ละ chat มี chatId unique)
  // แต่ยังเก็บชื่อ activeTripId เพื่อ backward compatibility
  // ✅ Restore activeTripId from localStorage on mount
  const [activeTripId, setActiveTripId] = useState(() => {
    try {
      const saved = localStorage.getItem(LS_ACTIVE_TRIP_KEY);
      if (saved) {
        console.log(`✅ Restored activeTripId from localStorage: ${saved}`);
        return saved;
      }
    } catch (e) {
      console.warn('Failed to restore activeTripId from localStorage:', e);
    }
    return null;
  });

  // ✅ Helper: หา active chat จาก activeTripId (อาจเป็น tripId หรือ chatId)
  const activeChat = useMemo(() => {
    if (!activeTripId) return null;
    
    // ✅ SECURITY: Filter trips by current user_id first
    const currentUserId = user?.id || userId;
    const userTrips = trips.filter(t => {
      const tripUserId = t.userId || t.user_id;
      return !tripUserId || tripUserId === currentUserId;
    });
    
    // ✅ ลองหาโดยใช้ chatId ก่อน (ถ้า activeTripId เป็น chatId)
    let found = userTrips.find(t => t.chatId === activeTripId);
    if (found) return found;
    // ✅ ถ้าไม่เจอ → ลองหาโดยใช้ tripId (backward compatibility)
    found = userTrips.find(t => t.tripId === activeTripId);
    if (found) return found;
    // ✅ ถ้ายังไม่เจอ → หาแชทแรกที่มี tripId นี้ (ถ้ามีหลายแชทในทริปเดียวกัน)
    const tripsWithSameTripId = userTrips.filter(t => t.tripId === activeTripId);
    return tripsWithSameTripId.length > 0 ? tripsWithSameTripId[0] : null;
  }, [trips, activeTripId, user?.id, userId]);

  // Admin check (is_admin จาก DB หรืออีเมลตรงกับ admin; backend ใช้ ADMIN_EMAIL / is_admin เช่นกัน)
  const isAdmin = Boolean(user?.is_admin) || user?.email === 'admin@example.com';

  // Loading state สำหรับการโหลด chat history (แบบ ChatGPT: โหลดเมื่อคลิกแชท)
  const [isLoadingHistory, setIsLoadingHistory] = useState(false);
  const [isRefreshingHistory, setIsRefreshingHistory] = useState(false);
  const isRefreshingRef = useRef(false);
  // Cache ประวัติแชทแบบ ChatGPT: chatId → messages[]
  const historyCache = useRef(new Map());
  const loadedTripsRef = useRef(new Set());
  const isFetchingHistoryRef = useRef(false);

  // ===== Helper: แปลง history จาก backend เป็น messages format =====
  // ตรวจว่าข้อความเป็น tool call / tool result (ไม่ควรแสดงใน chat)
  const isToolCallText = (text) => {
    if (!text || typeof text !== 'string') return false;
    const t = text.trim();
    if (!t.startsWith('{')) return false;
    try {
      const obj = JSON.parse(t);
      return obj && typeof obj === 'object' && typeof obj.tool === 'string';
    } catch {
      return false;
    }
  };

  const mapHistoryToMessages = (data) => {
    if (!data.history || data.history.length === 0) return null;
    return data.history
      .filter(m => {
        // ซ่อน tool role messages และ assistant messages ที่เป็น tool call JSON
        if (m.role === 'tool') return false;
        if (isToolCallText(m.text || m.content || '')) return false;
        return true;
      })
      .map((m, idx) => ({
      ...m,
      id: m.id || `restored_${idx}_${makeId('hist')}`,
      type: m.role === 'assistant' ? 'bot' : (m.role || m.type),
      planChoices: m.planChoices || m.plan_choices || [],
      slotChoices: m.slotChoices || m.slot_choices || [],
      slotIntent: m.slotIntent || m.slot_intent || null,
      agentState: m.agentState || m.agent_state || null,
      travelSlots: m.travelSlots || m.travel_slots || null,
      currentPlan: m.currentPlan || m.current_plan || null,
      tripTitle: m.tripTitle || m.trip_title || null,
      searchResults: m.searchResults || m.search_results || {},
      suggestions: m.suggestions || [],
      cachedOptions: m.cachedOptions || m.cached_options || null,
      cacheValidation: m.cacheValidation || m.cache_validation || null,
      workflowValidation: m.workflowValidation || m.workflow_validation || null,
      reasoning: m.reasoning || null,
      memorySuggestions: m.memorySuggestions || m.memory_suggestions || null,
      debug: m.debug || null
    }));
  };

  // แบบ ChatGPT: ใส่ messages เข้า trip และอัปเดต plan/slots จากข้อความล่าสุด
  const applyMessagesToTrip = useCallback((chatId, messages, setError = false) => {
    const findIdx = (list) => list.findIndex(t => t.chatId === chatId || t.tripId === chatId);
    setTrips(prev => {
      const idx = findIdx(prev);
      if (idx === -1) return prev;
      const next = [...prev];
      next[idx] = { ...next[idx], messages: messages || [], _loadError: setError };
      return next;
    });
    if (messages && messages.length > 0) {
      const latest = messages.slice().reverse().find(m => m.type === 'bot' && (m.planChoices?.length || m.currentPlan || m.travelSlots));
      if (latest) {
        if (latest.planChoices?.length) setLatestPlanChoices(latest.planChoices);
        if (latest.currentPlan) setSelectedPlan(latest.currentPlan);
        if (latest.travelSlots) setSelectedTravelSlots(latest.travelSlots);
        setLatestBotMessage(latest);
      }
    }
  }, []);

  // โหลดประวัติแชทเมื่อเลือกแชท (แบบ ChatGPT: on-demand, มี cache แสดงทันที)
  const loadHistoryForChat = useCallback((chatIdToLoad) => {
    if (!chatIdToLoad) return;

    const cached = historyCache.current.get(chatIdToLoad);
    if (cached !== undefined) {
      loadedTripsRef.current.add(chatIdToLoad);
      if (cached && cached.length > 0) applyMessagesToTrip(chatIdToLoad, cached, false);
      return;
    }

    if (isFetchingHistoryRef.current) return;
    isFetchingHistoryRef.current = true;
    const findTripIndex = (list) => list.findIndex(t => t.chatId === chatIdToLoad || t.tripId === chatIdToLoad);
    isFetchingHistoryRef.current = true;

    (async () => {
      try {
        setIsLoadingHistory(true);
        const historyHeaders = {
          'Content-Type': 'application/json',
          'X-Trip-ID': chatIdToLoad,
          'X-User-ID': user?.user_id || user?.id || '',
        };

        const res = await fetch(`${API_BASE_URL}/api/chat/history/${chatIdToLoad}`, {
          headers: historyHeaders,
          credentials: 'include',
        });

        if (!res.ok) {
          historyCache.current.set(chatIdToLoad, []);
          loadedTripsRef.current.add(chatIdToLoad);
          setTrips(prev => {
            const idx = findTripIndex(prev);
            if (idx === -1) return prev;
            const next = [...prev];
            next[idx] = { ...next[idx], messages: [], _loadError: true };
            return next;
          });
          return;
        }

        const data = await res.json();
        let restoredMessages;
        try {
          restoredMessages = mapHistoryToMessages(data);
        } catch (mapErr) {
          console.warn('Failed to map history (malformed data):', mapErr);
          restoredMessages = [];
        }
        loadedTripsRef.current.add(chatIdToLoad);
        const currentUserId = user?.id || userId;

        if (!restoredMessages || restoredMessages.length === 0) {
          historyCache.current.set(chatIdToLoad, []);
          setTrips(prev => {
            const idx = findTripIndex(prev);
            if (idx === -1) return prev;
            const next = [...prev];
            next[idx] = { ...next[idx], messages: [], updatedAt: next[idx].updatedAt, userId: next[idx].userId || currentUserId, _loadError: false };
            return next;
          });
          return;
        }

        const seen = new Set();
        const uniqueMessages = restoredMessages.filter(msg => {
          const key = msg.id || `${msg.type}_${msg.text}_${msg.timestamp || ''}`;
          if (seen.has(key)) return false;
          seen.add(key);
          return true;
        });
        historyCache.current.set(chatIdToLoad, uniqueMessages);
        setTrips(prev => {
          const idx = findTripIndex(prev);
          if (idx === -1) return prev;
          const newTrips = [...prev];
          newTrips[idx] = { ...newTrips[idx], messages: uniqueMessages, updatedAt: nowISO(), userId: newTrips[idx].userId || currentUserId, _loadError: false };
          return newTrips;
        });
        const latestBotWithData = uniqueMessages.slice().reverse().find(m => m.type === 'bot' && (m.planChoices?.length || m.currentPlan || m.travelSlots));
        if (latestBotWithData) {
          if (latestBotWithData.planChoices?.length) setLatestPlanChoices(latestBotWithData.planChoices);
          if (latestBotWithData.currentPlan) setSelectedPlan(latestBotWithData.currentPlan);
          if (latestBotWithData.travelSlots) setSelectedTravelSlots(latestBotWithData.travelSlots);
          setLatestBotMessage(latestBotWithData);
        }
      } catch (err) {
        console.error('Fetch chat history error:', err);
        historyCache.current.set(chatIdToLoad, []);
        loadedTripsRef.current.add(chatIdToLoad);
        setTrips(prev => {
          const idx = findTripIndex(prev);
          if (idx === -1) return prev;
          const next = [...prev];
          next[idx] = { ...next[idx], messages: [], _loadError: true };
          return next;
        });
      } finally {
        setIsLoadingHistory(false);
        isFetchingHistoryRef.current = false;
      }
    })();
  }, [user?.id, user?.user_id, userId, mapHistoryToMessages, applyMessagesToTrip]);

  // ===== โหลดประวัติเมื่อเลือกแชท (แบบ ChatGPT) =====
  useEffect(() => {
    if (!activeTripId) return;

    setShowTripSummary(false);
    const chatId = activeChat?.chatId || activeTripId;

    // ✅ แบบ Gemini/ChatGPT: มี cache แสดงทันที ไม่ fetch ซ้ำ; ไม่มี cache จึงโหลด (แสดง loading แล้วได้ประวัติ)
    const cached = historyCache.current.get(chatId);
    if (cached !== undefined) {
      loadedTripsRef.current.add(chatId);
      if (cached && cached.length > 0) {
        setTrips(prev => {
          const idx = prev.findIndex(t => t.chatId === chatId || t.tripId === chatId);
          if (idx === -1) return prev;
          const existing = prev[idx].messages || [];
          if (existing.length >= cached.length) return prev;
          const next = [...prev];
          next[idx] = { ...next[idx], messages: cached, _loadError: false };
          return next;
        });
        const latestBotWithData = cached.slice().reverse().find(m => m.type === 'bot' && (m.planChoices?.length || m.currentPlan || m.travelSlots));
        if (latestBotWithData) {
          if (latestBotWithData.planChoices?.length) setLatestPlanChoices(latestBotWithData.planChoices);
          if (latestBotWithData.currentPlan) setSelectedPlan(latestBotWithData.currentPlan);
          if (latestBotWithData.travelSlots) setSelectedTravelSlots(latestBotWithData.travelSlots);
          setLatestBotMessage(latestBotWithData);
        }
      }
      return;
    }

    loadHistoryForChat(chatId);
  }, [activeTripId, activeChat?.chatId, loadHistoryForChat]);

  const [inputText, setInputText] = useState('');
  const [processingTripId, setProcessingTripId] = useState(null);
  // ✅ แสดง TripSummary เมื่อผู้ใช้พิมพ์ข้อความที่มีคำว่า "จองเลย"
  const [showTripSummary, setShowTripSummary] = useState(false);
  // ✅ แก้ไข isTyping ให้ตรวจสอบทั้ง tripId และ chatId
  const isTyping = processingTripId !== null && activeChat && 
                   (processingTripId === activeTripId ||
                    processingTripId === activeChat.tripId ||
                    processingTripId === activeChat.chatId);
  const [isRecording, setIsRecording] = useState(false);
  const [isVoiceMode, setIsVoiceMode] = useState(false);
  const recognitionRef = useRef(null);
  const synthesisRef = useRef(null);
  const isVoiceModeRef = useRef(false); // ใช้ ref เพื่อตรวจสอบใน callback
  const liveAudioWebSocketRef = useRef(null); // ✅ WebSocket สำหรับ Live Audio
  const audioContextRef = useRef(null); // ✅ AudioContext สำหรับ real-time audio
  const mediaRecorderRef = useRef(null); // ✅ MediaRecorder สำหรับ capture audio
  const isMountedRef = useRef(true); // ✅ ป้องกัน setState หลัง unmount
  
  // ✅ Cleanup voice mode เมื่อ component unmount
  useEffect(() => {
    return () => {
      isMountedRef.current = false;
      stopLiveVoiceMode();
    };
  }, []);
  // #region frontend error debug log (H3 H4) - ใช้ sendTelemetry จะส่งเฉพาะเมื่อ VITE_TELEMETRY_ENABLED=true
  useEffect(() => {
    const onError = (msg, url, line, col, err) => {
      sendTelemetry({ location: 'window.onerror', message: 'Uncaught error', data: { message: String(msg), url, line, col, errorMessage: err?.message }, timestamp: Date.now(), runId: 'run1', hypothesisId: 'H3' });
    };
    const onUnhandledRejection = (ev) => {
      sendTelemetry({ location: 'unhandledrejection', message: 'Unhandled promise rejection', data: { reason: String(ev?.reason?.message || ev?.reason) }, timestamp: Date.now(), runId: 'run1', hypothesisId: 'H4' });
    };
    window.addEventListener('error', (e) => { onError(e.message, e.filename, e.lineno, e.colno, e.error); });
    window.addEventListener('unhandledrejection', onUnhandledRejection);
    return () => {
      window.removeEventListener('error', onError);
      window.removeEventListener('unhandledrejection', onUnhandledRejection);
    };
  }, []);
  // #endregion
  const [isConnected, setIsConnected] = useState(null); // null = unknown, true = connected, false = disconnected
  const [connectionError, setConnectionError] = useState(null); // ข้อความเมื่อเชื่อมต่อ backend ไม่ได้ (สำหรับแสดงแบนเนอร์)
  const [connectionRetryCount, setConnectionRetryCount] = useState(0); // Track retry attempts
  const [shouldRetry, setShouldRetry] = useState(false); // Flag to trigger retry
  const [editingMessageId, setEditingMessageId] = useState(null);
  const [editingTripId, setEditingTripId] = useState(null);
  const [editingTripName, setEditingTripName] = useState('');
  const abortControllerRef = useRef(null);
  // ✅ ป้องกัน double send (double-click / StrictMode)
  const sendInProgressRef = useRef(false);
  // ✅ ป้องกัน SSE "completed" ถูกประมวลผลมากกว่าหนึ่งครั้งต่อ request
  const completedProcessedRef = useRef(false);
  // ✅ สถานะการทำงานของ Agent แบบ realtime
  const [agentStatus, setAgentStatus] = useState(null); // { status, message, step }
  // ✅ ข้อความแก้ไขทริป (สำหรับปุ่ม "รัน Flow ใหม่" ในโหมดแก้ไข) — ใช้ state เพื่อให้ปุ่มแสดงหลังโหลดจากประวัติ
  const [editModeMessageForRerun, setEditModeMessageForRerun] = useState(null);
  // ✅ โหมดแก้ไข (มาจาก My Bookings กดแก้ไข) — บังคับใช้โหมดถามเท่านั้น
  const [isEditMode, setIsEditMode] = useState(() => {
    try {
      const editStr = localStorage.getItem('edit_booking_context');
      if (!editStr) return false;
      const edit = JSON.parse(editStr);
      return edit?.action === 'edit_trip';
    } catch (_) {
      return false;
    }
  });
  // ✅ ID การจองเดิมที่จะแทนที่ในโหมดแก้ไข (ยกเลิกอันเดิมแล้วจองอันใหม่ใน trip id เดิม)
  const [editReplaceBookingId, setEditReplaceBookingId] = useState(null);
  // ✅ Chat Mode: 'normal' = ผู้ใช้เลือกช้อยส์เอง, 'agent' = AI ดำเนินการเอง
  const [chatMode, setChatMode] = useState(() => {
    try {
      const editStr = localStorage.getItem('edit_booking_context');
      if (editStr) {
        try {
          const edit = JSON.parse(editStr);
          if (edit?.action === 'edit_trip') return 'normal'; // โหมดแก้ไขใช้ Normal เท่านั้น
        } catch (_) {}
      }
      const saved = localStorage.getItem('chat_mode');
      return saved === 'agent' ? 'agent' : 'normal';
    } catch (_) {
      return 'normal';
    }
  });
  // ✅ เมื่อเป็นโหมดแก้ไข ให้คงเป็น Normal และไม่ให้สลับไป Agent
  useEffect(() => {
    if (isEditMode && chatMode !== 'normal') {
      setChatMode('normal');
      localStorage.setItem('chat_mode', 'normal');
    }
  }, [isEditMode, chatMode]);
  // ✅ Mobile: Dropdown state for chat mode
  const [isChatModeDropdownOpen, setIsChatModeDropdownOpen] = useState(false);
  const chatModeDropdownRef = useRef(null);
  
  // ✅ Close dropdown when clicking outside
  useEffect(() => {
    const handleClickOutside = (event) => {
      if (chatModeDropdownRef.current && !chatModeDropdownRef.current.contains(event.target)) {
        setIsChatModeDropdownOpen(false);
      }
    };
    
    if (isChatModeDropdownOpen) {
      document.addEventListener('mousedown', handleClickOutside);
    }
    
    return () => {
      document.removeEventListener('mousedown', handleClickOutside);
    };
  }, [isChatModeDropdownOpen]);
  // ✅ สถานะเปิด/ปิด sidebar: Desktop เปิดเสมอ, Mobile เริ่มต้นปิด
  const [isSidebarOpen, setIsSidebarOpen] = useState(() => {
    // Desktop: เปิดเสมอ, Mobile: ปิด
    return typeof window !== 'undefined' && window.innerWidth > 768;
  });
  
  // ===== Selected plan (persists across messages) =====
  // ✅ ต้องประกาศก่อน useEffect ที่ใช้ selectedPlan
  const [selectedPlan, setSelectedPlan] = useState(null);
  const [selectedTravelSlots, setSelectedTravelSlots] = useState(null);
  const [latestPlanChoices, setLatestPlanChoices] = useState([]);
  const [latestBotMessage, setLatestBotMessage] = useState(null); // ✅ Store latest bot message for agentState
  // ✅ ลำดับการแสดงหมวด: แสดงเที่ยวบินก่อน → เมื่อผู้ใช้เลือกเที่ยวบินแล้วจึงแสดงที่พัก → จากนั้นการเดินทาง
  const [messageIdsWithFlightSelected, setMessageIdsWithFlightSelected] = useState(() => new Set());
  const [messageIdsWithHotelSelected, setMessageIdsWithHotelSelected] = useState(() => new Set());
  const [messageIdsWithOutboundSelected, setMessageIdsWithOutboundSelected] = useState(() => new Set());
  
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
  
  // ===== Booking state =====
  const [isBooking, setIsBooking] = useState(false);
  const [bookingResult, setBookingResult] = useState(null);

  // ===== Derived: active trip =====
  // ✅ Use activeChat as activeTrip (already computed above)
  const activeTrip = activeChat;

  const lastUserMessageId = useMemo(() => {
    const last = [...(activeTrip?.messages || [])].slice().reverse().find(m => m.type === 'user');
    return last?.id;
  }, [activeTrip]);

  // ✅ Get messages from activeTrip, with fallback to localStorage if activeTrip is not loaded yet
  const messages = useMemo(() => {
    if (activeTrip?.messages && activeTrip.messages.length > 0) {
      return activeTrip.messages;
    }
    // ✅ Fallback: Try to get messages from localStorage if activeTrip is not loaded yet
    if (activeTripId) {
      try {
        const savedTrips = localStorage.getItem(LS_TRIPS_KEY);
        if (savedTrips) {
          const allTrips = JSON.parse(savedTrips);
          // ✅ SECURITY: Filter trips by current user_id
          const currentUserId = user?.id || userId;
          const userTrips = allTrips.filter(t => {
            const tripUserId = t.userId || t.user_id;
            return !tripUserId || tripUserId === currentUserId;
          });
          
          const trip = userTrips.find(t => t.tripId === activeTripId || t.chatId === activeTripId);
          if (trip?.messages && trip.messages.length > 0) {
            console.log(`✅ Restored ${trip.messages.length} messages from localStorage for trip: ${activeTripId}`);
            return trip.messages;
          }
        }
      } catch (e) {
        console.warn('Failed to restore messages from localStorage:', e);
      }
    }
    return [];
  }, [activeTrip?.messages, activeTripId, user?.id, userId]);

  // ✅ Ref เพื่อเก็บ trips ล่าสุด สำหรับ save ตอนปิดแชทหรือ refresh หน้า
  const tripsRef = useRef(trips);
  tripsRef.current = trips;

  // ===== Persist trips เฉพาะตอนปิดแชท (unmount) หรือ refresh หน้า (beforeunload) =====
  useEffect(() => {
    const saveTripsToStorage = () => {
      try {
        const current = tripsRef.current;
        if (!current?.length) return;
        const currentUserId = user?.id || userId;
        // ✅ Merge messages จาก historyCache เข้า trips ก่อน save
        const userTrips = current.map(trip => {
          const cid = trip.chatId || trip.tripId;
          const cached = historyCache.current?.get(cid);
          const stateMs = trip.messages || [];
          const bestMs = stateMs.length > 0 ? stateMs : (cached?.length > 0 ? cached : []);
          return {
            ...trip,
            messages: bestMs.slice(-100),
            userId: currentUserId,
          };
        });
        localStorage.setItem(LS_TRIPS_KEY, JSON.stringify(userTrips));
      } catch (_) {}
    };
    const onBeforeUnload = () => { saveTripsToStorage(); };
    window.addEventListener('beforeunload', onBeforeUnload);
    return () => {
      window.removeEventListener('beforeunload', onBeforeUnload);
      saveTripsToStorage(); // ✅ ปิดแชท (ออกจากหน้า) = save
    };
  }, [user?.id, userId]);

  useEffect(() => {
    // ✅ SECURITY: Filter trips by current user before processing
    const currentUserId = user?.id || userId;
    const userTrips = trips.filter(t => {
      const tripUserId = t.userId || t.user_id;
      return !tripUserId || tripUserId === currentUserId;
    });
    
    if (!activeTripId && userTrips.length > 0) {
      // ✅ Try to restore from localStorage first
      const savedActiveTripId = localStorage.getItem(LS_ACTIVE_TRIP_KEY);
      if (savedActiveTripId && userTrips.some(t => t.tripId === savedActiveTripId || t.chatId === savedActiveTripId)) {
        console.log(`✅ Restored activeTripId from localStorage: ${savedActiveTripId}`);
        setActiveTripId(savedActiveTripId);
        return;
      }
      // ✅ Fallback: Auto-select first trip
      console.log(`🎯 Auto-selecting first trip (no activeTripId): ${userTrips[0].tripId}, messages: ${userTrips[0].messages?.length || 0}`);
      // ✅ ใช้ chatId แทน tripId เพื่อให้แชทแยกกันถูกต้อง
      setActiveTripId(userTrips[0].chatId || userTrips[0].tripId);
      return;
    }
    // ✅ Check if activeTripId exists in user trips (support both tripId and chatId)
    if (activeTripId && !userTrips.some(t => t.tripId === activeTripId || t.chatId === activeTripId) && userTrips.length > 0) {
      console.log(`⚠️ Active trip not found (${activeTripId}), switching to first trip: ${userTrips[0].tripId}`);
      // ✅ ใช้ chatId แทน tripId เพื่อให้แชทแยกกันถูกต้อง
      setActiveTripId(userTrips[0].chatId || userTrips[0].tripId);
    }
  }, [activeTripId, trips, user?.id, userId]);

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
  const DEBUG_CHAT = import.meta.env.VITE_DEBUG_CHAT === 'true';
  const checkApiConnection = React.useCallback(async () => {
    if (DEBUG_CHAT) console.log('🔍 Checking API connection...', API_BASE_URL);
    // Create abort controller for timeout
    // Increased timeout to 15 seconds to account for slow MongoDB/Redis checks
    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), 15000); // 15 second timeout
    
    try {
      const response = await fetch(`${API_BASE_URL}/health`, { 
        cache: 'no-cache',
        method: 'GET',
        headers: {
          'Accept': 'application/json'
        },
        signal: controller.signal
      });
      
      clearTimeout(timeoutId);
      
      // Check if response is ok (status 200-299)
      if (!response.ok) {
        let healthBody = {};
        try {
          healthBody = await response.json();
        } catch (_) { /* ignore */ }
        const checksMsg = healthBody?.checks?.startup?.message || healthBody?.checks?.mongodb?.message;
        if (DEBUG_CHAT || response.status === 503) {
          console.warn(`❌ Health check failed: HTTP ${response.status}`, checksMsg ? `— ${checksMsg}` : '');
        }
        // Try fallback: ถ้า /health คืน 503 (เช่น MongoDB ยังไม่พร้อม) แต่ backend รันอยู่ การเรียก / อาจได้ 200
        const fallbackController = new AbortController();
        const fallbackTimeoutId = setTimeout(() => fallbackController.abort(), 5000);
        try {
          const fallbackResponse = await fetch(`${API_BASE_URL}/`, {
            cache: 'no-cache',
            signal: fallbackController.signal
          });
          clearTimeout(fallbackTimeoutId);
          if (fallbackResponse.ok) {
            console.log('✅ Fallback check: Backend is reachable (health reported degraded/unhealthy)');
            setIsConnected(true);
            setConnectionError(null);
            return;
          }
        } catch (fallbackError) {
          clearTimeout(fallbackTimeoutId);
          console.error('❌ Fallback check also failed:', fallbackError);
        }
        setIsConnected(false);
        setConnectionError(
          response.status === 503 && checksMsg
            ? `เซิร์ฟเวอร์รายงาน: ${checksMsg} กรุณาตรวจสอบ MongoDB หรือลองใหม่ในภายหลัง`
            : 'ไม่สามารถเชื่อมต่อกับเซิร์ฟเวอร์ — ตรวจสอบว่า Backend รันอยู่ (เช่น พอร์ต 8000) และ VITE_API_BASE_URL ถูกต้อง'
        );
        return;
      }
      
      const data = await response.json();
      if (DEBUG_CHAT) console.log('✅ Health check response:', data);
      
      // Backend returns 'healthy' or 'degraded', but 'ok' is also possible from older versions
      // Also accept any status that indicates the server is running (not 'unhealthy')
      // 'degraded' means some services are slow but server is still operational
      const isHealthy = data.status === 'healthy' || 
                       data.status === 'ok' || 
                       data.status === 'degraded' ||
                       (data.status && data.status !== 'unhealthy');
      
      if (DEBUG_CHAT) console.log(`📊 Connection status: ${isHealthy ? '✅ CONNECTED' : '❌ DISCONNECTED'} (status: ${data.status})`);
      setIsConnected(isHealthy);
      if (isHealthy) setConnectionError(null);
      
      if (!isHealthy) {
        console.warn('⚠️ Backend status is not healthy:', data.status);
        if (data.checks) {
          console.warn('⚠️ Service checks:', data.checks);
        }
      } else if (data.status === 'degraded') {
        console.warn('⚠️ Backend is degraded (some services slow/unavailable but operational)');
        if (data.checks) {
          console.warn('⚠️ Service checks:', data.checks);
        }
      }
    } catch (error) {
      clearTimeout(timeoutId);
      // Handle AbortError (timeout) separately
      if (error.name === 'AbortError' || error.name === 'TimeoutError') {
        console.warn('⏱️ Health check timed out (15s), backend may be slow but assuming reachable');
        // Don't set to false immediately, might just be slow
        // Health check endpoint may be checking MongoDB/Redis which can be slow
        return;
      }
      console.error('❌ API connection error:', error);
      // Only set to false if it's a real network error (not timeout)
      if (error.message && !error.message.includes('timeout') && !error.message.includes('aborted')) {
        console.error('❌ Setting connection status to DISCONNECTED');
        setIsConnected(false);
        setConnectionError(
          'ไม่สามารถเชื่อมต่อกับเซิร์ฟเวอร์ (Failed to fetch) — ตรวจสอบว่า Backend รันอยู่ และ VITE_API_BASE_URL ถูกต้อง (เช่น http://localhost:8000)'
        );
      }
    }
  }, [API_BASE_URL]);
  
  useEffect(() => {
    if (DEBUG_CHAT) console.log('🚀 Initializing health check...');
    // Check immediately on mount
    checkApiConnection();
    // ตั้งเวลาตรวจสอบการเชื่อมต่อทุก 10 วินาที เพื่อ Reconnect อัตโนมัติ
    const interval = setInterval(() => {
      if (DEBUG_CHAT) console.log('🔄 Periodic health check...');
      checkApiConnection();
    }, 10000);
    return () => {
      if (DEBUG_CHAT) console.log('🛑 Cleaning up health check interval');
      clearInterval(interval);
    };
  }, [checkApiConnection]);

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

  // แปลงค่า response/message จาก API เป็น string สำหรับเก็บใน message.text (หลีกเลี่ยง [object Object])
  const toMessageText = (val) => {
    if (val == null) return '';
    if (typeof val === 'string') return val;
    if (typeof val === 'object') {
      if (typeof val.response === 'string') return val.response;
      if (typeof val.message === 'string') return val.message;
      try { return JSON.stringify(val, null, 2); } catch { return '[ไม่สามารถแสดงข้อมูลได้]'; }
    }
    return String(val);
  };

  // ===== Trips update helpers =====
  const appendMessageToTrip = (tripId, msg) => {
    if (!tripId || !msg) {
      console.warn('⚠️ appendMessageToTrip: tripId or msg is missing', { tripId, msg });
      return;
    }
    setTrips(prev => {
      const currentUserId = user?.id || userId;
      return prev.map(t => {
        const tripUserId = t.userId || t.user_id;
        if (tripUserId && tripUserId !== currentUserId) return t;
        if (t.tripId !== tripId && t.chatId !== tripId) return t;
        const currentMessages = Array.isArray(t.messages) ? t.messages : [];

        // Zero-Duplicate Guard: check if exact same message ID already exists
        if (msg.id && currentMessages.some(m => m.id === msg.id)) {
          return t;
        }

        // Content-based dedup: if bot msg with identical text arrived within 2s, replace
        if (msg.type === 'bot' && currentMessages.length > 0) {
          const last = currentMessages[currentMessages.length - 1];
          if (last.type === 'bot' && (last.text || '') === (msg.text || '')) {
            const nextMessages = [...currentMessages.slice(0, -1), msg];
            // ✅ Sync to in-memory cache
            const cid = t.chatId || t.tripId;
            historyCache.current.set(cid, nextMessages);
            return { ...t, messages: nextMessages, updatedAt: nowISO() };
          }
        }

        const nextMessages = [...currentMessages, msg];
        // ✅ Sync to in-memory cache whenever a message is appended
        const cid = t.chatId || t.tripId;
        historyCache.current.set(cid, nextMessages);
        return { ...t, messages: nextMessages, updatedAt: nowISO() };
      });
    });
  };

  const setTripTitle = (tripId, title) => {
    if (!title) return;
    setTrips(prev => {
      // ✅ SECURITY: Filter by user_id and update
      const currentUserId = user?.id || userId;
      return prev.map(t => {
        const tripUserId = t.userId || t.user_id;
        // ✅ Only update trips that belong to current user
        if (tripUserId && tripUserId !== currentUserId) {
          return t; // Don't modify trips from other users
        }
        if (t.tripId !== tripId) return t;
        return { ...t, title, updatedAt: nowISO() };
      });
    });
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

  // ===== Force refresh: โหลด session list จาก backend ใหม่ =====
  const handleRefreshHistory = async () => {
    if (isRefreshingRef.current) return;
    isRefreshingRef.current = true;
    setIsRefreshingHistory(true);

    try {
      const currentUserId = user?.id || userId;
      const headers = { 'Content-Type': 'application/json' };
      if (currentUserId) headers['X-User-ID'] = currentUserId;

      const res = await fetch(`${API_BASE_URL}/api/chat/sessions`, {
        headers,
        credentials: 'include',
      });

      if (!res.ok) {
        console.warn('⚠️ Failed to fetch sessions:', res.status);
        return;
      }

      const data = await res.json();
      const backendSessions = data.sessions || [];
      console.log(`✅ Fetched ${backendSessions.length} sessions from backend`);

      const backendTrips = backendSessions.map(session => ({
        tripId: session.trip_id || session.chat_id,
        chatId: session.chat_id || session.session_id?.split('::')?.[1] || session.session_id,
        title: session.title || 'แชทใหม่',
        updatedAt: session.last_updated || session.created_at,
        messages: [],
        userId: currentUserId,
        pinned: false
      }));

      // Clear loaded cache so history will be re-fetched when switching chats
      loadedTripsRef.current.clear();

      setTrips(prev => {
        const userTrips = prev.filter(t => {
          const tUserId = t.userId || t.user_id;
          return !tUserId || tUserId === currentUserId;
        });
        const existingChatIds = new Set(backendTrips.map(t => t.chatId));
        // Keep local-only trips (not yet synced to backend)
        const localOnlyTrips = userTrips.filter(t => !existingChatIds.has(t.chatId || t.tripId));
        // Merge: backend trips + preserve pinned state from existing
        const merged = backendTrips.map(bt => {
          const existing = userTrips.find(t => (t.chatId || t.tripId) === bt.chatId);
          return existing ? { ...bt, pinned: existing.pinned || false } : bt;
        });
        return [...merged, ...localOnlyTrips];
      });

      // Reload active chat history
      if (activeTripId) {
        const chatId = activeChat?.chatId || activeTripId;
        const tripId = activeChat?.tripId || activeTripId;
        if (chatId) {
          try {
            setIsLoadingHistory(true);
            const histHeaders = { 'Content-Type': 'application/json', 'X-Trip-ID': tripId || chatId };
            if (currentUserId) histHeaders['X-User-ID'] = currentUserId;
            const histRes = await fetch(`${API_BASE_URL}/api/chat/history/${chatId}`, {
              headers: histHeaders,
              credentials: 'include',
            });
            if (histRes.ok) {
              const histData = await histRes.json();
              const restoredMessages = mapHistoryToMessages(histData);
              if (restoredMessages && restoredMessages.length > 0) {
                loadedTripsRef.current.add(chatId);
                setTrips(prev => {
                  const idx = prev.findIndex(t => (t.chatId || t.tripId) === chatId);
                  if (idx === -1) return prev;
                  const newTrips = [...prev];
                  newTrips[idx] = { ...newTrips[idx], messages: restoredMessages, updatedAt: nowISO() };
                  return newTrips;
                });
              }
            }
          } catch (e) {
            console.error('❌ Error reloading active chat history:', e);
          } finally {
            setIsLoadingHistory(false);
          }
        }
      }
    } catch (error) {
      console.error('❌ Error refreshing sessions:', error);
    } finally {
      isRefreshingRef.current = false;
      setIsRefreshingHistory(false);
    }
  };

  // ===== Sync conversations on enter + flush to MongoDB on leave =====
  // ✅ Sync once on mount (when user enters chat), flush session to MongoDB on unmount/leave
  useEffect(() => {
    if (!user?.id) return;

    const currentUserId = user?.id || userId;

    // ✅ Sync history once when entering chat
    const initialSync = setTimeout(() => {
      if (!isRefreshingRef.current) {
        handleRefreshHistory();
      }
    }, 500);

    // ✅ Flush session to MongoDB when user leaves the page (tab close / navigate away)
    const flushSessionToMongo = () => {
      if (!currentUserId) return;
      // Use fetch with keepalive:true — works on page unload and supports custom headers
      const url = `${API_BASE_URL}/api/chat/flush-session`;
      try {
        fetch(url, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            'X-User-ID': currentUserId,
          },
          body: JSON.stringify({ session_id: null }), // flush all user sessions
          keepalive: true,
          credentials: 'include',
        }).catch(() => {});
      } catch (e) { /* ignore */ }
      // Save last active trip for restore
      if (activeTripId) {
        try {
          sessionStorage.setItem('ai_travel_last_active_trip', activeTripId);
        } catch (e) { /* ignore */ }
      }
    };

    window.addEventListener('beforeunload', flushSessionToMongo);

    return () => {
      clearTimeout(initialSync);
      window.removeEventListener('beforeunload', flushSessionToMongo);
      // Also flush when component unmounts (user navigates away within SPA)
      flushSessionToMongo();
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [user?.id]);

  // ===== Create/Delete trip =====
  const handleNewTrip = () => {
    try {
      console.log('🆕 Creating new trip...');
      const displayName = user?.first_name || user?.name || "คุณ";
      const currentUserId = user?.id || userId;
      const nt = createNewTrip('ทริปใหม่', displayName);
      // ✅ SECURITY: Set userId for new trip
      nt.userId = currentUserId;
      
      console.log('✅ New trip created:', { tripId: nt.tripId, chatId: nt.chatId, userId: currentUserId });

      // Register trip on backend (idempotent)
      ensureTripRegistered(nt.tripId, 'ทริปใหม่').then(() => fetchUserTrips());

      setTrips(prev => {
        // ✅ SECURITY: Filter out trips from other users before adding new trip
        const userTrips = prev.filter(t => {
          const tripUserId = t.userId || t.user_id;
          return !tripUserId || tripUserId === currentUserId;
        });
        const newTrips = [nt, ...userTrips];
        // ✅ ไม่ save ที่นี่ — จะ save ตอนปิดแชทหรือ refresh หน้าเท่านั้น
        return newTrips;
      });
      
      // ✅ ใช้ chatId เป็น activeTripId เพื่อให้แชทแยกกันถูกต้อง
      setActiveTripId(nt.chatId);
      setInputText('');
      
      console.log('🔄 Resetting backend chat context...');

      // Reset backend trip context (agent shouldn't auto-run on new trip)
      fetch(`${API_BASE_URL}/api/chat/reset`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        credentials: 'include',
        body: JSON.stringify({
          user_id: userId,
          chat_id: nt.chatId, // ✅ ใช้ chat_id แทน client_trip_id
          client_trip_id: nt.tripId // ✅ เก็บไว้สำหรับ backward compatibility
        })
      })
      .then(response => {
        if (response.ok) {
          console.log('✅ Backend chat context reset successfully');
        } else {
          console.warn('⚠️ Backend reset failed:', response.status);
        }
      })
      .catch(error => {
        console.error('❌ Backend reset error:', error);
      });
      
    } catch (error) {
      console.error('❌ Error creating new trip:', error);
      alert('เกิดข้อผิดพลาดในการสร้างทริปใหม่ กรุณาลองอีกครั้ง');
    }
  };

  const handleDeleteTrip = async (tripId) => {
    const result = await Swal.fire({
      title: "ลบแชท?",
      text: "คุณต้องการลบแชทนี้ออกจากประวัติใช่ไหม? การกระทำนี้ไม่สามารถย้อนกลับได้",
      icon: "question",
      showCancelButton: true,
      confirmButtonColor: "#dc2626",
      cancelButtonColor: "#6b7280",
      confirmButtonText: "ลบ",
      cancelButtonText: "ยกเลิก",
      reverseButtons: true
    });

    if (!result.isConfirmed) return;

    const currentUserId = user?.id || userId;
    const userTrips = trips.filter(t => {
      const tripUserId = t.userId || t.user_id;
      return !tripUserId || tripUserId === currentUserId;
    });

    const tripToDelete = userTrips.find(t => t.tripId === tripId || t.chatId === tripId);
    const chatIdToDelete = tripToDelete?.chatId || tripToDelete?.tripId || tripId;

    loadedTripsRef.current.delete(chatIdToDelete);
    loadedTripsRef.current.delete(tripId);
    historyCache.current.delete(chatIdToDelete);
    historyCache.current.delete(tripId);

    // ลบจาก backend ก่อน แล้วค่อย sync UI + localStorage
    let backendOk = false;
    if (chatIdToDelete) {
      try {
        const res = await fetch(`${API_BASE_URL}/api/chat/sessions/${chatIdToDelete}`, {
          method: 'DELETE',
          credentials: 'include',
          headers: { 'X-User-ID': currentUserId || '' },
        });
        backendOk = res.ok;
        if (!res.ok) console.warn(`⚠️ Backend delete failed: ${res.status}`);
      } catch (err) {
        console.error('❌ Backend delete error:', err);
      }
    }

    // อัปเดต UI + localStorage พร้อมกัน
    setTrips(prev => {
      const filtered = prev.filter(t => {
        const tUserId = t.userId || t.user_id;
        if (tUserId && tUserId !== currentUserId) return true;
        return t.tripId !== tripId;
      });
      const remaining = filtered.filter(t => {
        const tUserId = t.userId || t.user_id;
        return !tUserId || tUserId === currentUserId;
      });
      let nextTrips;
      if (remaining.length === 0) {
        const displayName = user?.first_name || user?.name || "คุณ";
        const newTrip = createNewTrip('ทริปใหม่', displayName);
        newTrip.userId = currentUserId;
        nextTrips = [newTrip];
      } else {
        nextTrips = filtered;
      }
      localStorage.setItem(LS_TRIPS_KEY, JSON.stringify(nextTrips));
      return nextTrips;
    });

    // Switch active trip ถ้าลบ trip ที่กำลังดูอยู่
    const isActiveTrip = userTrips.some(t =>
      (t.tripId === tripId && activeTripId === t.tripId) ||
      (t.chatId === activeTripId && t.tripId === tripId)
    );
    if (isActiveTrip) {
      const remaining = userTrips.filter(t => t.tripId !== tripId);
      setActiveTripId(remaining[0]?.chatId || remaining[0]?.tripId || null);
    }

    if (backendOk) console.log(`✅ Deleted chat from backend + localStorage: ${chatIdToDelete}`);
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

    setTrips(prev => {
      // ✅ SECURITY: Filter by user_id and update
      const currentUserId = user?.id || userId;
      return prev.map(t => {
        const tripUserId = t.userId || t.user_id;
        // ✅ Only update trips that belong to current user
        if (tripUserId && tripUserId !== currentUserId) {
          return t; // Don't modify trips from other users
        }
        return t.tripId === tripId
          ? { ...t, title: editingTripName.trim(), updatedAt: nowISO() }
          : t;
      });
    });
    setEditingTripId(null);
    setEditingTripName('');
  };

  const handleCancelEditTripName = () => {
    setEditingTripId(null);
    setEditingTripName('');
  };

  // ===== Toggle pin trip =====
  const handleTogglePin = (tripId) => {
    setTrips(prev => {
      // ✅ SECURITY: Filter by user_id and update
      const currentUserId = user?.id || userId;
      return prev.map(t => {
        const tripUserId = t.userId || t.user_id;
        // ✅ Only update trips that belong to current user
        if (tripUserId && tripUserId !== currentUserId) {
          return t; // Don't modify trips from other users
        }
        return t.tripId === tripId
          ? { ...t, pinned: !t.pinned, updatedAt: nowISO() }
          : t;
      });
    });
  };

  // ===== Sort trips: pinned first, then by updatedAt =====
  // ✅ SECURITY: Filter trips by current user before sorting
  const sortedTrips = useMemo(() => {
    const currentUserId = user?.id || userId;
    // ✅ Filter trips by current user_id
    const userTrips = trips.filter(t => {
      const tripUserId = t.userId || t.user_id;
      return !tripUserId || tripUserId === currentUserId;
    });
    if (!Array.isArray(userTrips) || userTrips.length === 0) return [];
    return [...userTrips].sort((a, b) => {
      // ปักหมุดมาก่อน
      if (a.pinned && !b.pinned) return -1;
      if (!a.pinned && b.pinned) return 1;
      // ถ้าทั้งคู่ปักหมุดหรือไม่ปักหมุด ให้เรียงตาม updatedAt (ใหม่สุดมาก่อน)
      try {
        const dateA = a.updatedAt ? new Date(a.updatedAt) : new Date(0);
        const dateB = b.updatedAt ? new Date(b.updatedAt) : new Date(0);
        return dateB.getTime() - dateA.getTime();
      } catch (e) {
        console.error('Error sorting trips by updatedAt:', e);
        return 0;
      }
    });
  }, [trips, user?.id, userId]);

  // ===== Stop current request =====
  const handleStop = () => {
    if (abortControllerRef.current) {
      abortControllerRef.current.abort();
      abortControllerRef.current = null;
    }
    setProcessingTripId(null);
  };

  // ===== Edit message =====
  const handleEditMessage = (messageId, messageText) => {
    setEditingMessageId(messageId);
    setInputText(messageText);
    // scroll ลงมาที่ input และ focus
    setTimeout(() => {
      inputRef.current?.focus();
      inputRef.current?.scrollIntoView({ behavior: 'smooth', block: 'end' });
    }, 50);
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

    // ✅ เปิด Trip Summary เลย เมื่อผู้ใช้พิมพ์ข้อความที่มีคำว่า "จองเลย" (รองรับ จองเลย / จอง เลย)
    if (/จอง\s*เลย/.test(trimmed)) {
      setShowTripSummary(true);
    }

    // ✅ ป้องกัน double send (double-click / StrictMode)
    if (sendInProgressRef.current) {
      console.warn('⚠️ sendMessage: already in progress, skipping duplicate send');
      return;
    }
    sendInProgressRef.current = true;
    completedProcessedRef.current = false; // ✅ Reset so we process exactly one "completed" per request

    // Only show alert if we're sure backend is disconnected (false), not if unknown (null)
    if (isConnected === false) {
      sendInProgressRef.current = false;
      alert('ไม่สามารถเชื่อมต่อกับเซิร์ฟเวอร์ กรุณาตรวจสอบว่า Backend รันอยู่ (เช่น พอร์ต 8000) หรือกด "ลองใหม่" ที่แถบแจ้งเตือนด้านบน');
      return;
    }
    
    // If status is unknown (null), try to send anyway - let the actual request fail gracefully

    const tripId = activeTrip?.tripId;
    // ✅ ใช้ chatId เป็น target ของการ append เพื่อให้ข้อความไปแสดงในแชทที่เลือก (แก้บั๊กแชทซ้อนเมื่อมีหลายแชทในทริปเดียวกัน)
    const targetId = activeTrip?.chatId || activeTrip?.tripId;
    if (!tripId || !targetId) {
      sendInProgressRef.current = false;
      return;
    }

    // If editing, remove the old message and its bot response (match by targetId = แชทปัจจุบัน)
    if (editingMessageId) {
      setTrips(prev =>
        prev.map(t => {
          if (t.tripId !== targetId && t.chatId !== targetId) return t;
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
      id: makeId('msg_user'),
      type: 'user',
      text: trimmed
    };

    appendMessageToTrip(targetId, userMessage);
    setProcessingTripId(targetId);
    setAgentStatus(null); // Reset status

    // Create abort controller for this request
    abortControllerRef.current = new AbortController();

    try {
      // ✅ ใช้ SSE endpoint สำหรับ realtime status updates
      const chatId = activeTrip?.chatId || tripId; // ✅ ใช้ chatId ถ้ามี (fallback ไป tripId สำหรับ backward compatibility)
      const response = await fetch(`${API_BASE_URL}/api/chat/stream`, {
        method: 'POST',
        headers: { 
          'Content-Type': 'application/json',
          'X-Conversation-ID': chatId, // ✅ ส่ง chat_id ใน header
        },
        credentials: 'include',
        signal: abortControllerRef.current.signal,
        body: JSON.stringify({
          user_id: userId,
          message: trimmed,
          trigger: 'user_message',
          trip_id: tripId, // ✅ trip_id: สำหรับ 1 ทริป
          chat_id: chatId, // ✅ chat_id: สำหรับแต่ละแชท
          client_trip_id: tripId, // ✅ เก็บไว้สำหรับ backward compatibility
          mode: chatMode // ✅ 'normal' หรือ 'agent'
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
              // ✅ ไม่ส่ง telemetry ทุก chunk — ส่งเฉพาะตอน error หรือ completed เพื่อลด request ที่ถูกยกเลิก
              
              // ✅ จัดการ error จาก stream
              if (data.status === 'error') {
                // ✅ Telemetry service (optional - fail silently)
                sendTelemetry({
                  location: 'AITravelChat.jsx:1050',
                  message: 'SSE error received',
                  data: {error_message: data.message},
                  timestamp: Date.now(),
                  sessionId: 'debug-session',
                  runId: 'run1',
                  hypothesisId: 'A'
                });
                throw new Error(data.message || 'Unknown stream error');
              }
              
              // ✅ อัปเดตสถานะการทำงานแบบ realtime (ไม่ใช้ heartbeat — เอาออกเพื่อให้แสดงเฉพาะขั้นตอนจริง)
              if (data.status && data.message && data.status !== 'heartbeat' && data.step !== 'heartbeat') {
                setAgentStatus({
                  status: data.status,
                  message: data.message,
                  step: data.step
                });
              }

              // ✅ Agent Mode: แสดง Trip Summary ทันทีเมื่อได้ summary_ready (ก่อนจอง) แล้วค่อยจองต่อ
              if (data.status === 'summary_ready' && data.current_plan) {
                setSelectedPlan(data.current_plan);
                if (data.travel_slots) setSelectedTravelSlots(data.travel_slots);
                if (data.agent_state) setLatestBotMessage(prev => prev ? { ...prev, agentState: data.agent_state } : { agentState: data.agent_state });
              }
              
              // ✅ เมื่อเสร็จสิ้น ให้ใช้ข้อมูลผลลัพธ์ (ประมวลผลเพียงครั้งเดียวต่อ request)
              if (data.status === 'completed' && data.data) {
                if (completedProcessedRef.current) {
                  console.warn('⚠️ SSE completed already processed for this request, skipping duplicate');
                  continue;
                }
                completedProcessedRef.current = true;
                const finalData = data.data;
                console.log('API data (completed) >>>', finalData);
                // #region agent debug log (H4) - ใช้ sendTelemetry จะส่งเฉพาะเมื่อ VITE_TELEMETRY_ENABLED=true
                sendTelemetry({ location: 'AITravelChat.jsx:completed', message: 'SSE completed received', data: { has_current_plan: !!finalData?.current_plan, auto_booked: finalData?.auto_booked, will_set_selected_plan: !!finalData?.current_plan }, timestamp: Date.now(), runId: 'run1', hypothesisId: 'H4' });
                // #endregion
                
                // ✅ Telemetry service (optional - fail silently)
                sendTelemetry({
                  location: 'AITravelChat.jsx:1062',
                  message: 'Received completed status',
                  data: {has_response: !!finalData.response, response_length: finalData.response?.length || 0, has_plan_choices: !!finalData.plan_choices},
                  timestamp: Date.now(),
                  sessionId: 'debug-session',
                  runId: 'run1',
                  hypothesisId: 'A'
                });

                // ✅ Extract response text - try multiple fallbacks
                let responseText = '';
                if (finalData?.auto_booked && finalData?.agent_booking_success_message) {
                  responseText = finalData.agent_booking_success_message;
                } else if (typeof finalData?.response === 'string' && finalData.response.trim()) {
                  responseText = finalData.response.trim();
                } else if (finalData?.message && typeof finalData.message === 'string') {
                  responseText = finalData.message.trim();
                } else if (finalData?.text && typeof finalData.text === 'string') {
                  responseText = finalData.text.trim();
                } else if (finalData?.response) {
                  responseText = toMessageText(finalData.response).trim();
                }
                
                // ✅ If still empty, use default message
                if (!responseText) {
                  responseText = 'ได้รับข้อมูลตอบกลับแล้ว แต่ไม่มีข้อความ กรุณาลองใหม่อีกครั้ง';
                  console.warn('⚠️ No response text found in finalData:', finalData);
                }

                // ✅ Safe null checks for all fields
                const botMessage = {
                  id: makeId('msg_bot'),
                  type: 'bot',
                  text: responseText,
                  debug: finalData?.debug || null,
                  travelSlots: finalData?.travel_slots || null,
                  searchResults: finalData?.search_results || {},
                  planChoices: Array.isArray(finalData?.plan_choices) 
                    ? finalData.plan_choices 
                    : (finalData?.plan_choices ? [finalData.plan_choices] : []),
                  agentState: finalData?.agent_state || null,
                  suggestions: Array.isArray(finalData?.suggestions) ? finalData.suggestions : [],
                  currentPlan: finalData?.current_plan || null,
                  tripTitle: finalData?.trip_title || null,
                  slotIntent: finalData?.slot_intent || null,
                  slotChoices: Array.isArray(finalData?.slot_choices) ? finalData.slot_choices : [],
                  reasoning: finalData?.reasoning || null,
                  memorySuggestions: finalData?.memory_suggestions || null,
                  cachedOptions: finalData?.cached_options || null,
                  cacheValidation: finalData?.cache_validation || null,
                  workflowValidation: finalData?.workflow_validation || null,
                };
                
                // Debug: log plan choices and slot choices
                if (botMessage.planChoices && botMessage.planChoices.length > 0) {
                  console.log('📋 Plan choices received:', botMessage.planChoices.length, 'choices');
                }
                if (botMessage.slotChoices && botMessage.slotChoices.length > 0) {
                  console.log('🎯 Slot choices received:', botMessage.slotChoices.length, 'choices, intent:', botMessage.slotIntent);
                  console.log('🎯 Slot choices data:', botMessage.slotChoices);
                } else {
                  console.log('⚠️ No slot choices received. finalData.slot_choices:', finalData?.slot_choices);
                }

                appendMessageToTrip(targetId, botMessage);
                
                // ✅ Store latest bot message for agentState access
                setLatestBotMessage(botMessage);

                // ✅ ตรวจสอบว่า Agent Mode จองอัตโนมัติสำเร็จ (จาก backend ส่ง auto_booked หรือจากข้อความตอบกลับ)
                const responseTextLower = botMessage.text?.toLowerCase() || '';
                const isAgentModeBooking = (
                  chatMode === 'agent' && 
                  (finalData.auto_booked === true ||
                   responseTextLower.includes('จองสำเร็จ') || 
                   responseTextLower.includes('จองเสร็จ') ||
                   responseTextLower.includes('สร้างการจองสำเร็จ') ||
                   responseTextLower.includes('auto-booked') ||
                   responseTextLower.includes('my bookings'))
                );
                
                if (isAgentModeBooking) {
                  const accuracyScore = finalData.agent_accuracy_score != null ? Number(finalData.agent_accuracy_score) : null;
                  // แสดงการแจ้งเตือนเมื่อจองอัตโนมัติสำเร็จ แล้วต่อด้วย SweetAlert คะแนนวัดผล AI
                  Swal.fire({
                    icon: 'success',
                    title: '✅ จองอัตโนมัติสำเร็จ',
                    html: `
                      <div style="text-align: left;">
                        <p style="margin-bottom: 12px;">Agent จองทริปให้คุณเรียบร้อยแล้ว</p>
                        <p style="margin-bottom: 12px; color: #dc2626; font-weight: 600;">
                          ⚠️ กรุณาชำระเงินที่ My Bookings เพื่อยืนยันการจอง
                        </p>
                        <p style="margin-bottom: 0; color: #6b7280; font-size: 14px;">
                          📋 ดูรายการจองได้ที่ "การจองของฉัน"
                        </p>
                      </div>
                    `,
                    confirmButtonText: 'ไปที่ My Bookings',
                    cancelButtonText: 'ปิด',
                    showCancelButton: true,
                    confirmButtonColor: '#2563eb',
                    cancelButtonColor: '#6b7280',
                    reverseButtons: true,
                    allowOutsideClick: true,
                    allowEscapeKey: true
                  }).then((result) => {
                    if (result.isConfirmed && onNavigateToBookings) {
                      onNavigateToBookings();
                    }
                    return showAgentEvaluationSwal(accuracyScore, chatId);
                  });
                }

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
                if (finalData?.plan_choices) {
                  setLatestPlanChoices(finalData.plan_choices);
                }
                
                // ✅ SYNC TRIP PLAN STATE: Sync selectedPlan and travelSlots with backend data
                // Always update from backend response to keep frontend in sync
                if (finalData?.current_plan) {
                  setSelectedPlan(finalData.current_plan);
                  // #region agent debug log (H4) - ใช้ sendTelemetry จะส่งเฉพาะเมื่อ VITE_TELEMETRY_ENABLED=true
                  sendTelemetry({ location: 'AITravelChat.jsx:setSelectedPlan', message: 'setSelectedPlan called from current_plan', data: { has_current_plan: true }, timestamp: Date.now(), runId: 'run1', hypothesisId: 'H4' });
                  // #endregion
                  setSelectedTravelSlots(finalData?.travel_slots || null);
                  // ✅ ไม่เปิด Trip Summary อัตโนมัติ — แสดงเฉพาะเมื่อมีคำว่า "จองเลย" (ดูเงื่อนไขใน shouldShow)
                  // ✅ Update latestBotMessage with agentState
                  if (finalData.agent_state) {
                    setLatestBotMessage(prev => prev ? { ...prev, agentState: finalData.agent_state } : { agentState: finalData.agent_state });
                  }
                  console.log('✅ TripPlan state synced from backend:', {
                    hasPlan: !!finalData.current_plan,
                    hasSlots: !!finalData.travel_slots,
                    step: finalData.agent_state?.step
                  });
                } else if (finalData?.travel_slots) {
                  // If we have travel_slots but no current_plan, still update slots
                  setSelectedTravelSlots(finalData.travel_slots);
                  console.log('✅ Travel slots synced from backend');
                }

                // ✅ ตั้งชื่อทริปโดย Gemini จาก backend
                if (finalData.trip_title) {
                  setTripTitle(tripId, finalData.trip_title);
                }
              }
            } catch (err) {
              console.error('Error parsing SSE data line:', trimmedLine, err);
              // #region frontend error debug log (H2) - ใช้ sendTelemetry จะส่งเฉพาะเมื่อ VITE_TELEMETRY_ENABLED=true
              sendTelemetry({ location: 'AITravelChat.jsx:SSE parse catch', message: 'SSE line parse error', data: { errorMessage: String(err?.message), linePreview: (trimmedLine || '').slice(0, 100) }, timestamp: Date.now(), runId: 'run1', hypothesisId: 'H2' });
              // #endregion
            }
          }
        }
      }
    } catch (error) {
      console.error('Error calling API:', error);
      // #region frontend error debug log (H2) - ใช้ sendTelemetry จะส่งเฉพาะเมื่อ VITE_TELEMETRY_ENABLED=true
      sendTelemetry({ location: 'AITravelChat.jsx:sendMessage catch', message: 'API/stream error', data: { errorName: error?.name, errorMessage: String(error?.message) }, timestamp: Date.now(), runId: 'run1', hypothesisId: 'H2' });
      // #endregion

      if (error.name === 'AbortError') {
        appendMessageToTrip(targetId, {
          id: Date.now() + 1,
          type: 'bot',
          text: '⏹️ หยุดการทำงานแล้วค่ะ'
        });
      } else {
        // ✅ Connection error - set disconnected and offer retry
        setIsConnected(false);
        const isNetworkError = !error.message || /failed to fetch|connection reset|network error|ERR_CONNECTION/i.test(String(error.message));
        const shortMessage = 'การเชื่อมต่อถูกตัดกลางทาง กรุณาลองส่งอีกครั้งหรือกด Regenerate ค่ะ';
        const longMessage = `❌ เกิดข้อผิดพลาดในการเชื่อมต่อ\n\n${error.message}\n\nโปรดตรวจสอบ:\n1. Backend กำลังทำงานอยู่\n2. API Keys ถูกต้อง\n3. การเชื่อมต่ออินเทอร์เน็ต`;
        const errorMessage = {
          id: Date.now() + 1,
          type: 'bot',
          text: isNetworkError ? `❌ ${shortMessage}` : longMessage,
          error: true,
          retryAvailable: true,
          onRetry: () => {
            setShouldRetry(true);
            setConnectionRetryCount(prev => prev + 1);
            setTimeout(() => {
              sendMessage(trimmed);
            }, 1000 * Math.min(connectionRetryCount + 1, 5));
          }
        };

        appendMessageToTrip(targetId, errorMessage);
      }
    } finally {
      setProcessingTripId(null);
      setAgentStatus(null); // Clear status
      abortControllerRef.current = null;
      sendInProgressRef.current = false; // Allow next send (fix duplicate messages from double-send)
    }
  };

  // ===== Regenerate (refresh) last user message like ChatGPT =====
  const regenerateFromUserText = async (messageId, userText) => {
    const tripId = activeTrip?.tripId;
    const targetId = activeTrip?.chatId || activeTrip?.tripId;
    if (!tripId || !targetId) return;
    const trimmed = String(userText || '').trim();
    if (!trimmed) return;

    const now = Date.now();
    const lastAt = lastRefreshAtRef.current[messageId] || 0;
    if (now - lastAt < REFRESH_COOLDOWN_MS) return;
    lastRefreshAtRef.current[messageId] = now;

    setProcessingTripId(targetId);
    
    // ✅ Revert chat: ลบข้อความหลังจากข้อความที่กดรีเฟรชออกให้หมด (match by targetId = แชทปัจจุบัน)
    setTrips(prev =>
      prev.map(t => {
        if (t.tripId !== targetId && t.chatId !== targetId) return t;
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
      const chatId = activeTrip?.chatId || tripId; // ✅ ใช้ chatId ถ้ามี
      const response = await fetch(`${API_BASE_URL}/api/chat/stream`, {
        method: 'POST',
        headers: { 
          'Content-Type': 'application/json',
          'X-Conversation-ID': chatId, // ✅ ส่ง chat_id ใน header
        },
        credentials: 'include',
        signal: abortControllerRef.current.signal,
        body: JSON.stringify({
          user_id: userId,
          message: trimmed,
          trigger: 'refresh',
          trip_id: tripId, // ✅ trip_id: สำหรับ 1 ทริป
          chat_id: chatId, // ✅ chat_id: สำหรับแต่ละแชท
          client_trip_id: tripId // ✅ เก็บไว้สำหรับ backward compatibility
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

              // ✅ อัปเดตสถานะการทำงานแบบ realtime (ไม่ใช้ heartbeat)
              if (data.status && data.message && data.status !== 'heartbeat' && data.step !== 'heartbeat') {
                setAgentStatus({
                  status: data.status,
                  message: data.message,
                  step: data.step
                });
              }

              // ✅ Agent Mode: แสดง Trip Summary เมื่อได้ summary_ready
              if (data.status === 'summary_ready' && data.current_plan) {
                setSelectedPlan(data.current_plan);
                if (data.travel_slots) setSelectedTravelSlots(data.travel_slots);
                if (data.agent_state) setLatestBotMessage(prev => prev ? { ...prev, agentState: data.agent_state } : { agentState: data.agent_state });
              }
              
              // ✅ เมื่อเสร็จสิ้น ให้ใช้ข้อมูลผลลัพธ์
              if (data.status === 'completed' && data.data) {
                const finalData = data.data;
                console.log('Refresh API data (completed) >>>', finalData);

      const botMessage = {
        id: Date.now() + 1,
        type: 'bot',
                  text: toMessageText(finalData.response),
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
                  cachedOptions: finalData.cached_options || null,
                  cacheValidation: finalData.cache_validation || null,
                  workflowValidation: finalData.workflow_validation || null,
      };

      appendMessageToTrip(targetId, botMessage);

                // ✅ ไม่แสดง popup แล้ว - ให้ LLM บอกในแชทแทน
                // Notification จะแสดงใน My Bookings แทน

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
                const workflowValidation = finalData.workflow_validation || agentState.workflow_validation || {};
                
                // ✅ ตรวจสอบ workflow step จาก validator (ห้ามข้ามขั้นตอน)
                const currentWorkflowStep = workflowValidation.current_step || agentState.step || "planning";
                const isWorkflowComplete = workflowValidation.is_complete || false;
                const workflowIssues = workflowValidation.completeness_issues || [];
                
                // ✅ Log workflow step เพื่อ debug
                if (currentWorkflowStep) {
                  console.log('📋 Current Workflow Step:', currentWorkflowStep, {
                    is_complete: isWorkflowComplete,
                    issues: workflowIssues.length
                  });
                }
                
                const isSlotWorkflowComplete = (
                  slotWorkflow.current_slot === "summary" || 
                  agentState.step === "trip_summary" ||
                  currentWorkflowStep === "trip_summary" ||
                  (!slotWorkflow.current_slot && !finalData.slot_choices && !finalData.slot_intent)
                );
                
                // ✅ แสดง Summary ได้เมื่อ: workflow complete และ current_step = trip_summary
                const hasOnlyTransferPending = finalData.slot_intent === 'transfer' || finalData.slot_intent === 'transport';
                const shouldShowSummary = (isSlotWorkflowComplete && isWorkflowComplete) || 
                                         (currentWorkflowStep === "trip_summary" && isWorkflowComplete) ||
                                         hasOnlyTransferPending;
                
                // ✅ Agent Mode: ถ้ามี current_plan → แสดงทันที (ไม่ต้องรอ workflow เสร็จ)
                const isAgentMode = finalData.agent_state?.agent_mode || chatMode === 'agent';
                
                if (finalData.current_plan) {
                  // Agent Mode: แสดง plan ทันที
                  if (isAgentMode || shouldShowSummary) {
                    setSelectedPlan(finalData.current_plan);
                    setSelectedTravelSlots(finalData.travel_slots || null);
                    setShowTripSummary(true); // ✅ เปิด TripSummary ให้แสดงแม้หลังจอง
                    console.log('✅ Agent Mode: Auto-set selectedPlan from current_plan');
                  } else {
                    // โหมดถาม: แสดง plan แม้ workflow ยังไม่เสร็จ (เพื่อให้เห็น progress)
                    setSelectedPlan(finalData.current_plan);
                    setSelectedTravelSlots(finalData.travel_slots || null);
                    if (currentWorkflowStep === 'trip_summary' || currentWorkflowStep === 'completed') {
                      setShowTripSummary(true);
                    }
                  }
                } else {
                  setSelectedPlan(null);
                  setSelectedTravelSlots(null);
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
        appendMessageToTrip(targetId, {
          id: Date.now() + 1,
          type: 'bot',
          text: '⏹️ หยุดการทำงานแล้วค่ะ'
        });
      } else {
        const isNetworkError = !e.message || /failed to fetch|connection reset|network error|ERR_CONNECTION/i.test(String(e.message));
        const text = isNetworkError
          ? '❌ การเชื่อมต่อถูกตัดกลางทาง กรุณาลองกด Regenerate อีกครั้งค่ะ'
          : `❌ Error: ${e.message}`;
        if (isNetworkError) setIsConnected(false);
        appendMessageToTrip(targetId, {
          id: Date.now() + 1,
          type: 'bot',
          text
        });
      }
    } finally {
      setProcessingTripId(null);
      abortControllerRef.current = null;
    }
  };

  // ===== Set initial prompt to input field (from Home 'Get Started') =====
  // ✅ ไม่ส่งอัตโนมัติ แต่ให้ผู้ใช้กดส่งเอง
  const didSetInitialPromptRef = useRef(false);
  const didSendEditMessageRef = useRef(false);

  // ✅ เมื่อกดแก้ไขจาก My Bookings: ถ้ามี edit context แต่ยังไม่มี trip ในรายการ ให้เพิ่ม trip เพื่อให้โหลดแชทที่จองมาได้
  useEffect(() => {
    const editContextStr = localStorage.getItem('edit_booking_context');
    if (!editContextStr || !activeTripId || activeChat) return;
    try {
      const editContext = JSON.parse(editContextStr);
      if (editContext.action !== 'edit_trip' || !editContext.tripId || !editContext.chatId) return;
      const tripId = editContext.tripId;
      const chatId = editContext.chatId || tripId;
      const currentUserId = user?.id || userId;
      setTrips(prev => {
        const hasTrip = prev.some(t => (t.chatId === chatId || t.tripId === tripId) && (!t.userId || t.userId === currentUserId));
        if (hasTrip) return prev;
        return [...prev, {
          tripId,
          chatId,
          title: 'ทริปที่จอง',
          messages: [],
          userId: currentUserId,
          pinned: false,
          updatedAt: new Date().toISOString(),
        }];
      });
    } catch (e) {
      console.warn('Failed to add edit trip:', e);
    }
  }, [activeTripId, activeChat, user?.id, userId]);

  // ✅ Handle edit booking context - send message after activeChat is ready
  useEffect(() => {
    if (didSendEditMessageRef.current) return;
    
    const editContextStr = localStorage.getItem('edit_booking_context');
    if (!editContextStr) return;
    
    // ✅ Wait for activeChat to be ready
    if (!activeChat || !activeChat.tripId) {
      return; // Wait for activeChat to be set
    }
    
    try {
      const editContext = JSON.parse(editContextStr);
      if (editContext.action === 'edit_trip' && editContext.booking) {
        // ✅ โหมดแก้ไข: บังคับใช้โหมดถามเท่านั้น (เก็บสถานะไว้ทั้ง session)
        setIsEditMode(true);
        setEditReplaceBookingId(editContext.bookingId || null); // เก็บ ID การจองเดิม — ยกเลิกแล้วจองใหม่ใน trip id เดิม
        setChatMode('normal');
        localStorage.setItem('chat_mode', 'normal');
        // ✅ Mark as sent to prevent duplicate
        didSendEditMessageRef.current = true;
        
        const booking = editContext.booking;
        const travelSlots = booking.travel_slots || {};
        const origin = travelSlots.origin_city || travelSlots.origin || '';
        const destination = travelSlots.destination_city || travelSlots.destination || '';
        const route = origin && destination ? `${origin} → ${destination}` : 'ทริปนี้';
        const departureDate = travelSlots.departure_date || travelSlots.start_date || '';
        const returnDate = travelSlots.return_date || travelSlots.end_date || '';
        const totalPrice = booking.total_price || 0;
        const currency = booking.currency || 'THB';
        
        const formattedPrice = formatPriceInThb(totalPrice, currency);
        
        // ✅ สร้างข้อความที่บอก AI ว่าเรามาแก้ไขทริป พร้อมข้อมูล booking
        const editMessage = `ฉันต้องการแก้ไขทริปที่จองไว้\n\n📋 ข้อมูลการจองปัจจุบัน:\n- เส้นทาง: ${route}\n${departureDate ? `- วันเดินทาง: ${departureDate}` : ''}${returnDate ? `\n- วันกลับ: ${returnDate}` : ''}\n- ราคารวม: ${formattedPrice}\n- Booking ID: ${editContext.bookingId}\n\nกรุณาช่วยฉันแก้ไขทริปนี้ด้วยค่ะ`;
        // ✅ เก็บข้อความไว้สำหรับปุ่ม "รัน Flow ใหม่"
        setEditModeMessageForRerun(editMessage);

        // Clear edit context
        localStorage.removeItem('edit_booking_context');
        
        // Auto-send message after a delay to ensure chat is fully ready
        setTimeout(() => {
          if (activeChat && activeChat.tripId) {
            sendMessage(editMessage);
          }
        }, 1000);
      }
    } catch (e) {
      console.error('Failed to parse edit context:', e);
      localStorage.removeItem('edit_booking_context');
    }
  }, [activeChat]); // ✅ Run when activeChat changes

  // ✅ โหมดแก้ไข: ถ้ายังไม่มีข้อความสำหรับ "รัน Flow ใหม่" ให้ดึงจากข้อความ user ล่าสุดที่เหมือน edit prompt (รองรับหลัง reload)
  useEffect(() => {
    if (!isEditMode || editModeMessageForRerun) return;
    const msgs = activeTrip?.messages || [];
    const editLike = msgs.slice().reverse().find(m => m.type === 'user' && (m.text || '').includes('ฉันต้องการแก้ไขทริปที่จองไว้'));
    if (editLike && editLike.text) setEditModeMessageForRerun(editLike.text);
  }, [isEditMode, editModeMessageForRerun, activeTrip?.messages]);

  useEffect(() => {
    if (didSetInitialPromptRef.current) return;
    const p = (initialPrompt || '').trim();
    if (!p) return;
    didSetInitialPromptRef.current = true;
    
    // แสดงใน input field แทนการส่งอัตโนมัติ (สำหรับกรณีปกติ)
    setInputText(p);
    // Focus input field เพื่อให้ผู้ใช้เห็นและสามารถแก้ไข/ส่งได้
    setTimeout(() => {
      inputRef.current?.focus();
    }, 100);
  }, [initialPrompt]);

  const handleSend = async () => {
    if (!inputText.trim()) return;
    const currentInput = inputText;
    
    // Check for typos and language issues
    const correctionResult = correctTypos(currentInput);
    const languageMismatch = detectLanguageMismatch(currentInput, 'thai'); // Expect Thai by default
    
    // If there are corrections or language mismatch, show suggestion
    if (correctionResult.hasCorrections || languageMismatch.mismatch) {
      let suggestionText = '';
      let correctedText = currentInput;
      
      if (correctionResult.hasCorrections) {
        correctedText = correctionResult.corrected;
        const corrections = correctionResult.corrections.map(c => 
          `"${c.original}" → "${c.corrected}"`
        ).join(', ');
        suggestionText += `พบคำที่อาจจะพิมพ์ผิด: ${corrections}\n\n`;
      }
      
      if (languageMismatch.mismatch) {
        suggestionText += languageMismatch.suggestion + '\n\n';
      }
      
      suggestionText += `ข้อความที่แก้ไขแล้ว:\n"${correctedText}"`;
      
      const result = await Swal.fire({
        title: 'ตรวจพบข้อความที่อาจจะผิด',
        text: suggestionText,
        icon: 'info',
        showCancelButton: true,
        confirmButtonText: 'ใช้ข้อความที่แก้ไขแล้ว',
        cancelButtonText: 'ส่งข้อความเดิม',
        reverseButtons: true,
        customClass: {
          popup: 'swal-custom-popup',
          title: 'swal-custom-title',
          text: 'swal-custom-text'
        }
      });
      
      if (result.isConfirmed) {
        // Use corrected text
        setInputText('');
        setEditingMessageId(null);
        sendMessage(correctedText);
      } else if (result.dismiss === Swal.DismissReason.cancel) {
        // Use original text
        setInputText('');
        setEditingMessageId(null);
        sendMessage(currentInput);
      }
      // If dismissed (ESC), do nothing - keep the text in input
    } else {
      // No corrections needed, send normally
      setInputText('');
      setEditingMessageId(null);
      sendMessage(currentInput);
    }
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
  // ✅ โหมดสนทนาด้วยเสียง: ลอง Live API ก่อน ถ้าไม่ได้ใช้โหมดพูด→พิมพ์→อ่าน (Speech Recognition + แชท + TTS)
  const handleVoiceInput = () => {
    if (!isVoiceMode) {
      if (!user?.id && !user?.user_id) {
        alert('กรุณาเข้าสู่ระบบเพื่อใช้โหมดแชทด้วยเสียง');
        return;
      }
      startLiveVoiceMode();
    } else {
      stopLiveVoiceMode();
    }
  };

  // ✅ เริ่มโหมด Live Voice Conversation (ใช้ Gemini Live API)
  // ส่ง PCM 16-bit 16kHz mono ตรงๆ ผ่าน WebSocket binary frame
  const startLiveVoiceMode = async () => {
    const liveConnectedRef = { current: false };
    const fallbackDone = { current: false };

    const doFallbackToSimpleMode = (message) => {
      if (fallbackDone.current) return;
      fallbackDone.current = true;
      if (mediaRecorderRef.current) {
        try {
          const { stream, scriptNode, sourceNode } = mediaRecorderRef.current;
          if (scriptNode) {
            scriptNode.onaudioprocess = null;
            scriptNode.disconnect();
          }
          if (sourceNode) sourceNode.disconnect();
          if (stream) stream.getTracks().forEach(track => track.stop());
        } catch (e) {
          console.error('Error stopping audio nodes:', e);
        }
        mediaRecorderRef.current = null;
      }
      if (liveAudioWebSocketRef.current) {
        try {
          liveAudioWebSocketRef.current.close();
        } catch (e) {
          console.error('Error closing WebSocket:', e);
        }
        liveAudioWebSocketRef.current = null;
      }
      if (audioContextRef.current) {
        audioContextRef.current.close().catch(() => {});
        audioContextRef.current = null;
      }
      if (playbackCtx) {
        playbackCtx.close().catch(() => {});
      }
      if (message) alert(message);
      startSimpleVoiceMode();
    };

    let playbackCtx = null;
    try {
      if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
        alert('เบราว์เซอร์ของคุณไม่รองรับการบันทึกเสียง กรุณาใช้ Chrome หรือ Edge');
        return;
      }

      setIsVoiceMode(true);
      setIsRecording(true);
      isVoiceModeRef.current = true;

      // ── AudioContext 16kHz สำหรับ capture + 24kHz สำหรับ playback ──
      const AudioCtx = window.AudioContext || window.webkitAudioContext;
      const captureCtx = new AudioCtx({ sampleRate: 16000 });
      audioContextRef.current = captureCtx;

      // playback context แยกต่างหาก (24kHz ตาม Gemini output)
      playbackCtx = new AudioCtx({ sampleRate: 24000 });

      // ── Audio playback queue ──────────────────────────────────────
      let nextPlayTime = 0;
      let isAgentSpeaking = false;
      const isMicMutedRef = { current: false }; // หยุดส่ง mic ขณะ AI พูด

      const scheduleAudioChunk = (pcmBytes) => {
        const numSamples = pcmBytes.length / 2;
        const audioBuffer = playbackCtx.createBuffer(1, numSamples, 24000);
        const channelData = audioBuffer.getChannelData(0);
        const view = new DataView(pcmBytes.buffer, pcmBytes.byteOffset, pcmBytes.byteLength);
        for (let i = 0; i < numSamples; i++) {
          channelData[i] = view.getInt16(i * 2, true) / 32768.0;
        }
        const source = playbackCtx.createBufferSource();
        source.buffer = audioBuffer;
        source.connect(playbackCtx.destination);

        const now = playbackCtx.currentTime;
        const startAt = Math.max(now, nextPlayTime);
        source.start(startAt);
        nextPlayTime = startAt + audioBuffer.duration;

        if (!isAgentSpeaking) {
          isAgentSpeaking = true;
          isMicMutedRef.current = true;
          setIsRecording(false);
        }

        source.onended = () => {
          // ถ้าไม่มี chunk ใหม่ใน 200ms ถือว่า AI พูดจบ
          setTimeout(() => {
            if (playbackCtx.currentTime >= nextPlayTime - 0.05) {
              isAgentSpeaking = false;
              isMicMutedRef.current = false;
              if (isVoiceModeRef.current) setIsRecording(true);
            }
          }, 200);
        };
      };

      // ── ขออนุญาตใช้ไมโครโฟน ──────────────────────────────────────
      const stream = await navigator.mediaDevices.getUserMedia({
        audio: {
          channelCount: 1,
          sampleRate: 16000,
          echoCancellation: true,
          noiseSuppression: true,
          autoGainControl: true,
        }
      });

      // ── ScriptProcessorNode: capture PCM float32 → Int16 → binary ─
      const sourceNode = captureCtx.createMediaStreamSource(stream);
      const bufferSize = 4096;
      // eslint-disable-next-line no-undef
      const scriptNode = captureCtx.createScriptProcessor(bufferSize, 1, 1);
      sourceNode.connect(scriptNode);
      scriptNode.connect(captureCtx.destination);

      mediaRecorderRef.current = { stream, scriptNode, sourceNode }; // เก็บไว้สำหรับ cleanup

      // ── เชื่อมต่อ WebSocket ───────────────────────────────────────
      const wsProtocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
      const apiUrl = new URL(API_BASE_URL);
      const wsUrl = `${wsProtocol}//${apiUrl.host}/api/chat/live-audio?user_id=${encodeURIComponent(userId || 'anonymous')}&chat_id=${encodeURIComponent(activeTripId || 'default')}`;
      const ws = new WebSocket(wsUrl);
      ws.binaryType = 'arraybuffer';
      liveAudioWebSocketRef.current = ws;

      // ── ส่ง PCM binary เมื่อ WebSocket พร้อม ─────────────────────
      scriptNode.onaudioprocess = (e) => {
        if (!isVoiceModeRef.current) return;
        if (isMicMutedRef.current) return; // หยุดส่งขณะ AI พูด
        if (ws.readyState !== WebSocket.OPEN) return;

        const float32 = e.inputBuffer.getChannelData(0);
        const int16 = new Int16Array(float32.length);
        for (let i = 0; i < float32.length; i++) {
          const s = Math.max(-1, Math.min(1, float32[i]));
          int16[i] = s < 0 ? s * 32768 : s * 32767;
        }
        ws.send(int16.buffer); // ส่งเป็น binary frame (PCM 16-bit LE 16kHz)
      };

      // ── รับข้อมูลจาก backend ─────────────────────────────────────
      let transcriptBuffer = '';

      ws.onopen = () => {
        console.log('✅ Live Audio WebSocket connected');
      };

      ws.onmessage = async (event) => {
        try {
          // binary frame = PCM audio จาก Gemini
          if (event.data instanceof ArrayBuffer) {
            scheduleAudioChunk(new Uint8Array(event.data));
            return;
          }

          const message = JSON.parse(event.data);

          if (message.type === 'connected') {
            console.log('✅ Live session ready:', message.message);

          } else if (message.type === 'audio') {
            // base64 PCM fallback
            const raw = atob(message.data);
            const bytes = new Uint8Array(raw.length);
            for (let i = 0; i < raw.length; i++) bytes[i] = raw.charCodeAt(i);
            scheduleAudioChunk(bytes);

          } else if (message.type === 'text') {
            // สะสม transcript แล้วแสดงใน chat bubble
            transcriptBuffer += message.data;

          } else if (message.type === 'turn_complete') {
            // AI พูดจบ 1 ประโยค → เพิ่มข้อความใน chat
            if (transcriptBuffer.trim()) {
              const botMsg = {
                id: `voice_bot_${Date.now()}`,
                type: 'bot',
                text: transcriptBuffer.trim(),
                timestamp: nowISO(),
              };
              const targetId = activeChat?.chatId || activeChat?.tripId;
              if (targetId) {
                setTrips(prev => {
                  const idx = prev.findIndex(t => (t.chatId || t.tripId) === targetId);
                  if (idx === -1) return prev;
                  const updated = [...prev];
                  updated[idx] = { ...updated[idx], messages: [...(updated[idx].messages || []), botMsg] };
                  return updated;
                });
              }
              transcriptBuffer = '';
            }

          } else if (message.type === 'interruption') {
            // ผู้ใช้ขัดจังหวะ → หยุดเสียง AI ทันที
            nextPlayTime = 0;
            isAgentSpeaking = false;
            isMicMutedRef.current = false;
            setIsRecording(true);
            transcriptBuffer = '';

          } else if (message.type === 'error') {
            console.error('Live Audio error:', message.message);
            if (!fallbackDone.current) doFallbackToSimpleMode('โหมดเรียลไทม์ไม่พร้อม ใช้โหมดพูดแล้วพิมพ์แทน');
          }
        } catch (e) {
          console.error('Error processing WebSocket message:', e);
        }
      };

      ws.onerror = () => {
        console.error('WebSocket error');
        if (!fallbackDone.current) doFallbackToSimpleMode();
      };

      ws.onclose = () => {
        console.log('Live Audio WebSocket closed');
        if (liveConnectedRef.current) {
          if (isVoiceModeRef.current) stopLiveVoiceMode();
        } else if (!fallbackDone.current) {
          doFallbackToSimpleMode();
        }
      };

    } catch (error) {
      console.error('Error starting live voice mode:', error);
      if (!navigator.mediaDevices?.getUserMedia) {
        stopLiveVoiceMode();
        return;
      }
      doFallbackToSimpleMode('ไม่สามารถเริ่มโหมดเรียลไทม์ได้ ใช้โหมดพูดแล้วพิมพ์แทน');
    }
  };

  // ✅ โหมดเสียงแบบง่าย: พูด → แปลเป็นข้อความ → ส่งแชท → ได้คำตอบ → อ่านด้วย TTS (ใช้เมื่อ Live WebSocket ใช้ไม่ได้)
  const startSimpleVoiceMode = () => {
    const SpeechRecognitionAPI = window.SpeechRecognition || window.webkitSpeechRecognition;
    if (!SpeechRecognitionAPI) {
      alert('เบราว์เซอร์ไม่รองรับการรับเสียง (Speech Recognition) กรุณาใช้ Chrome หรือ Edge');
      if (isMountedRef.current) {
        setIsVoiceMode(false);
        setIsRecording(false);
      }
      isVoiceModeRef.current = false;
      return;
    }

    if (recognitionRef.current) {
      try { recognitionRef.current.stop(); } catch (_) {}
      recognitionRef.current = null;
    }

    setIsVoiceMode(true);
    setIsRecording(true);
    isVoiceModeRef.current = true;

    const recognition = new SpeechRecognitionAPI();
    recognition.continuous = true;
    recognition.interimResults = false;
    recognition.lang = 'th-TH';

    recognition.onresult = (event) => {
      if (!isVoiceModeRef.current) return;
      const last = event.results.length - 1;
      const transcript = event.results[last][0].transcript?.trim();
      if (transcript) sendMessage(transcript);
    };

    recognition.onend = () => {
      if (!isVoiceModeRef.current || !recognitionRef.current) return;
      try {
        recognitionRef.current.start();
      } catch (e) {
        if (isVoiceModeRef.current && isMountedRef.current) setIsRecording(true);
      }
    };

    recognition.onerror = (event) => {
      if (event.error === 'no-speech') return;
      if (event.error === 'aborted') return;
      console.warn('Speech recognition error:', event.error);
    };

    recognitionRef.current = recognition;
    try {
      recognition.start();
    } catch (e) {
      console.error('Recognition start error:', e);
      isVoiceModeRef.current = false;
      if (isMountedRef.current) {
        setIsVoiceMode(false);
        setIsRecording(false);
      }
      recognitionRef.current = null;
    }
  };

  // ✅ หยุดโหมด Live Voice Conversation
  const stopLiveVoiceMode = () => {
    isVoiceModeRef.current = false;
    if (isMountedRef.current) {
      setIsVoiceMode(false);
      setIsRecording(false);
    }

    // ✅ ปิด ScriptProcessor + MediaStream (แทน MediaRecorder เดิม)
    if (mediaRecorderRef.current) {
      try {
        const { stream, scriptNode, sourceNode } = mediaRecorderRef.current;
        if (scriptNode) {
          scriptNode.onaudioprocess = null;
          scriptNode.disconnect();
        }
        if (sourceNode) sourceNode.disconnect();
        if (stream) stream.getTracks().forEach(track => track.stop());
      } catch (e) {
        console.error('Error stopping audio nodes:', e);
      }
      mediaRecorderRef.current = null;
    }

    // ✅ ปิด AudioContext
    if (audioContextRef.current) {
      audioContextRef.current.close().catch(e => console.error('Error closing AudioContext:', e));
      audioContextRef.current = null;
    }
    
    // ✅ ปิด WebSocket
    if (liveAudioWebSocketRef.current) {
      try {
        liveAudioWebSocketRef.current.close();
      } catch (e) {
        console.error('Error closing WebSocket:', e);
      }
      liveAudioWebSocketRef.current = null;
    }
    
    // ✅ หยุด Speech Recognition (ถ้ามี)
    if (recognitionRef.current) {
      try {
        recognitionRef.current.stop();
      } catch (e) {
        console.error('Error stopping recognition:', e);
      }
      recognitionRef.current = null;
    }

    // ✅ หยุดการพูดถ้ากำลังพูดอยู่
    if (synthesisRef.current) {
      if (synthesisRef.current.pause) {
        synthesisRef.current.pause();
      } else {
        window.speechSynthesis.cancel();
      }
      synthesisRef.current = null;
    }
  };

  // ✅ ฟังก์ชันให้ Agent พูดด้วย Gemini TTS
  const speakText = async (text) => {
    if (!isVoiceModeRef.current) return; // ถ้าไม่อยู่ในโหมดเสียง ไม่ต้องพูด
    
    // หยุดการพูดก่อนหน้า
    if (synthesisRef.current) {
      synthesisRef.current.pause();
      synthesisRef.current = null;
    }
    
    try {
      // ✅ เรียก Gemini TTS API
      const response = await fetch(`${API_BASE_URL}/api/chat/tts`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          text: text,
          voice_name: 'Kore', // ใช้เสียง Kore จาก Gemini
          audio_format: 'MP3'
        })
      });
      
      if (!response.ok) {
        throw new Error(`TTS API error: ${response.status}`);
      }
      
      // ✅ รับ audio data และเล่น
      const audioBlob = await response.blob();
      const audioUrl = URL.createObjectURL(audioBlob);
      const audio = new Audio(audioUrl);
      
      synthesisRef.current = audio;
      
      audio.onended = () => {
        URL.revokeObjectURL(audioUrl);
        synthesisRef.current = null;
        // หลังจากพูดเสร็จ ให้เริ่มฟังต่อ
        if (isVoiceModeRef.current && recognitionRef.current) {
          setIsRecording(true);
          try {
            recognitionRef.current.start();
          } catch (e) {
            console.log('Recognition already running or error:', e);
          }
        }
      };
      
      audio.onerror = (e) => {
        console.error('Audio playback error:', e);
        URL.revokeObjectURL(audioUrl);
        synthesisRef.current = null;
        // ถ้าเกิด error ก็ให้เริ่มฟังต่อ
        if (isVoiceModeRef.current && recognitionRef.current) {
          setIsRecording(true);
          try {
            recognitionRef.current.start();
          } catch (e) {
            console.log('Recognition start error:', e);
          }
        }
      };
      
      // ระหว่างที่ Agent กำลังพูด ให้หยุดฟัง
      setIsRecording(false);
      
      // ✅ เล่นเสียง
      await audio.play();
      
    } catch (error) {
      console.error('Error generating or playing TTS:', error);
      // ✅ Fallback: ใช้ browser TTS ถ้า Gemini TTS ล้มเหลว
      const utterance = new SpeechSynthesisUtterance(text);
      utterance.lang = 'th-TH';
      utterance.rate = 1.0;
      utterance.pitch = 1.0;
      utterance.volume = 1.0;
      
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
        if (isVoiceModeRef.current && recognitionRef.current) {
          setIsRecording(true);
          try {
            recognitionRef.current.start();
          } catch (e) {
            console.log('Recognition start error:', e);
          }
        }
      };
      
      utterance.onerror = (e) => {
        console.error('Speech synthesis error:', e);
        synthesisRef.current = null;
        if (isVoiceModeRef.current && recognitionRef.current) {
          setIsRecording(true);
          try {
            recognitionRef.current.start();
          } catch (e) {
            console.log('Recognition start error:', e);
          }
        }
      };
      
      window.speechSynthesis.speak(utterance);
      setIsRecording(false);
    }
  };

  // ===== Select slot choice (for flight/hotel slots) =====
  const handleSelectSlotChoice = async (choiceId, slotType, slotChoice, message) => {
    // ✅ บันทึกว่าผู้ใช้เลือกหมวดนี้แล้ว เพื่อแสดงหมวดถัดไป (ที่พักหลังเลือกเที่ยวบิน, การเดินทางหลังเลือกที่พัก)
    if (message?.id != null) {
      if (slotType === 'flight') {
        setMessageIdsWithFlightSelected(prev => new Set([...prev, message.id]));
        const isOutbound = slotChoice?.flight_direction === 'outbound' || (slotChoice?.flight?.segments?.[0]?.direction && String(slotChoice.flight.segments[0].direction).includes('ขาไป'));
        if (isOutbound) setMessageIdsWithOutboundSelected(prev => new Set([...prev, message.id]));
      }
      if (slotType === 'hotel') setMessageIdsWithHotelSelected(prev => new Set([...prev, message.id]));
    }

    // Only show alert if we're sure backend is disconnected (false), not if unknown (null)
    if (isConnected === false) {
      alert('ไม่สามารถเชื่อมต่อกับเซิร์ฟเวอร์ กรุณากด "ลองใหม่" ที่แถบแจ้งเตือนหรือตรวจสอบว่า Backend รันอยู่');
      return;
    }
    
    // If status is unknown (null), try to send anyway - let the actual request fail gracefully

    const tripId = activeTrip?.tripId;
    const targetId = activeTrip?.chatId || activeTrip?.tripId;
    if (!tripId || !targetId) return;

    // ✅ เพิ่มข้อความฝั่งผู้ใช้ว่าเลือก slot X
    const slotName = slotType === 'flight' ? 'เที่ยวบิน' : slotType === 'hotel' ? 'ที่พัก' : slotType === 'car' ? 'รถ' : 'การเดินทาง';
    const userMessage = {
      id: Date.now(),
      type: 'user',
      text: `เลือกช้อยส์ ${choiceId}` // ใช้คำว่า "เลือกช้อยส์" แทน "เลือก..."
    };
    appendMessageToTrip(targetId, userMessage);

    setProcessingTripId(targetId);
    
    try {
      const currentPlan = selectedPlan;
      
      // ✅ ถ้าไม่มี currentPlan → ใช้ /api/chat/select_choice เพื่อเลือก slot (slot workflow)
      if (!currentPlan) {
        const chatId = activeTrip?.chatId || tripId; // ✅ ใช้ chatId ถ้ามี
        // ✅ ส่งข้อมูล choice ทั้งหมดไปยัง backend เพื่อให้ AI รู้ว่าผู้ใช้เลือกข้อมูลอะไร
        const res = await fetch(`${API_BASE_URL}/api/chat/select_choice`, {
          method: 'POST',
          headers: { 
            'Content-Type': 'application/json',
            'X-Conversation-ID': chatId, // ✅ ส่ง chat_id ใน header
          },
          credentials: 'include',
          body: JSON.stringify({
            user_id: userId,
            choice_id: choiceId,
            trip_id: tripId, // ✅ trip_id: สำหรับ 1 ทริป
            chat_id: chatId, // ✅ chat_id: สำหรับแต่ละแชท
            client_trip_id: tripId, // ✅ เก็บไว้สำหรับ backward compatibility
            choice_data: slotChoice || null, // ✅ ส่งข้อมูล choice ทั้งหมด
            slot_type: slotType || null // ✅ ส่ง slot type ด้วย
          })
        });

        if (!res.ok) {
          // Fallback: ส่งข้อความแทน
          await sendMessage(`เลือกช้อยส์ ${choiceId}`);
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
          text: toMessageText(data.response),
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

        appendMessageToTrip(targetId, botMessage);

        // ✅ Update state
        if (data.plan_choices) setLatestPlanChoices(data.plan_choices);
        // ✅ ตั้ง selectedPlan เมื่อมี current_plan (แสดง Summary ได้เลยถ้าข้อมูลใกล้ครบ)
        const hasOnlyTransferPending = data.slot_intent === 'transfer' || data.slot_intent === 'transport';
        const shouldShowSummary = isSlotWorkflowComplete || hasOnlyTransferPending;
        
        if (data.current_plan && shouldShowSummary) {
          setSelectedPlan(data.current_plan);
          setSelectedTravelSlots(data.travel_slots || null);
        } else if (data.current_plan) {
          // ✅ ถ้ามี current_plan แต่ยังมี slot อื่นๆ ต้องเลือก ก็ยังแสดง Summary ควบคู่กับ Choices
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
        
        const fp = updatedPlan.flight && (updatedPlan.flight.total_price != null || updatedPlan.flight.price_total != null) ? Number(updatedPlan.flight.total_price ?? updatedPlan.flight.price_total) : 0;
        const tp = updatedPlan.transport && (updatedPlan.transport.price != null || updatedPlan.transport.price_amount != null) ? Number(updatedPlan.transport.price ?? updatedPlan.transport.price_amount) : 0;
        updatedPlan.total_price = fp + newPrice + tp;
        
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
        
        const hp = updatedPlan.hotel && (updatedPlan.hotel.total_price != null || updatedPlan.hotel.price_total != null) ? Number(updatedPlan.hotel.total_price ?? updatedPlan.hotel.price_total) : 0;
        const tp = updatedPlan.transport && (updatedPlan.transport.price != null || updatedPlan.transport.price_amount != null) ? Number(updatedPlan.transport.price ?? updatedPlan.transport.price_amount) : 0;
        updatedPlan.total_price = newPrice + hp + tp;
        
        setSelectedPlan(updatedPlan);
        
        // ✅ Send to backend
        const segmentNums = targetSegments.map(i => i + 1).join(', ');
        await sendMessage(`เลือกช้อยส์ ${choiceId} สำหรับ segment ${segmentNums}`);
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
      
      // Recalculate total price (catalog-style: sum of each chosen item)
      const flightPrice = updatedPlan.flight && (updatedPlan.flight.total_price != null || updatedPlan.flight.price_total != null)
        ? Number(updatedPlan.flight.total_price ?? updatedPlan.flight.price_total) : 0;
      const hotelPrice = updatedPlan.hotel && (updatedPlan.hotel.total_price != null || updatedPlan.hotel.price_total != null)
        ? Number(updatedPlan.hotel.total_price ?? updatedPlan.hotel.price_total) : 0;
      const transportPrice = updatedPlan.transport && (updatedPlan.transport.price != null || updatedPlan.transport.price_amount != null)
        ? Number(updatedPlan.transport.price ?? updatedPlan.transport.price_amount) : 0;
      updatedPlan.total_price = flightPrice + hotelPrice + transportPrice;
      
      setSelectedPlan(updatedPlan);
      
      // Send message to backend to update
      await sendMessage(`เลือกช้อยส์ ${choiceId}`);
    } catch (error) {
      console.error('Error selecting slot choice:', error);
    } finally {
      setProcessingTripId(null);
    }
  };

  // ===== Select plan choice (click card -> select immediately) =====
  const handleSelectPlanChoice = async (choiceId, choice = null) => {
    // Only show alert if we're sure backend is disconnected (false), not if unknown (null)
    if (isConnected === false) {
      alert('Backend is not connected. Please start the backend server first.');
      return;
    }
    
    // If status is unknown (null), try to send anyway - let the actual request fail gracefully

    const tripId = activeTrip?.tripId;
    const targetId = activeTrip?.chatId || activeTrip?.tripId;
    if (!tripId || !targetId) return;

    // ✅ หา choice object ถ้ายังไม่มี (จาก latest message ที่มี planChoices)
    let choiceData = choice;
    if (!choiceData) {
      const latestBotMessage = [...(activeTrip?.messages || [])]
        .slice()
        .reverse()
        .find(m => m.type === 'bot' && m.planChoices && m.planChoices.length > 0);
      
      if (latestBotMessage?.planChoices) {
        choiceData = latestBotMessage.planChoices.find(c => {
          const cId = typeof c.id === 'number' ? c.id : (typeof c.get === 'function' ? c.get('id') : c.id);
          return parseInt(cId) === parseInt(choiceId);
        });
      }
    }

    // ✅ เพิ่มข้อความฝั่งผู้ใช้ว่าเลือกช้อยส์ X
    const userMessage = {
      id: Date.now(),
      type: 'user',
      text: `เลือกช้อยส์ ${choiceId}`
    };
    appendMessageToTrip(targetId, userMessage);

    setProcessingTripId(targetId);

    try {
      // ✅ ถ้า backend มี /api/chat/select_choice จะเลือกได้ทันทีแบบไม่ต้องส่งข้อความ
      // ✅ ส่งข้อมูล choice ทั้งหมดไปยัง backend เพื่อให้ AI รู้ว่าผู้ใช้เลือกข้อมูลอะไร
      const res = await fetch(`${API_BASE_URL}/api/chat/select_choice`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        credentials: 'include',
        body: JSON.stringify({
          user_id: userId,
          choice_id: choiceId,
          trip_id: tripId,
          choice_data: choiceData || null // ✅ ส่งข้อมูล choice ทั้งหมด
        })
      });

      // fallback ถ้า endpoint ไม่มี
      if (!res.ok) {
        setProcessingTripId(null);
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
        text: toMessageText(data.response),
        debug: data.debug || null,
        travelSlots: data.travel_slots || null,
        searchResults: data.search_results || {},
        planChoices: data.plan_choices || [],
        agentState: data.agent_state || null,
        suggestions: data.suggestions || [],
        currentPlan: data.current_plan || null,
        tripTitle: data.trip_title || null
      };

      appendMessageToTrip(targetId, botMessage);

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
      
      // ✅ ตั้ง selectedPlan เมื่อมี current_plan (แสดง Summary ได้เลยถ้าข้อมูลใกล้ครบ)
      const hasOnlyTransferPending = data.slot_intent === 'transfer' || data.slot_intent === 'transport';
      const shouldShowSummary = isSlotWorkflowComplete || hasOnlyTransferPending;
      
      // ✅ Agent Mode: ถ้ามี current_plan → แสดงทันที
      const isAgentMode = data.agent_state?.agent_mode || chatMode === 'agent';
      
      if (data.current_plan) {
        // Agent Mode หรือ workflow เสร็จ → แสดง plan
        if (isAgentMode || shouldShowSummary) {
          setSelectedPlan(data.current_plan);
          setSelectedTravelSlots(data.travel_slots || null);
          // ✅ Update latestBotMessage with agentState
          if (data.agent_state) {
            setLatestBotMessage(prev => prev ? { ...prev, agentState: data.agent_state } : { agentState: data.agent_state });
          }
          console.log('✅ Plan selected (Agent Mode or core ready):', {
            choiceId,
            isAgentMode,
            hasCurrentPlan: !!data.current_plan,
            agentState: data.agent_state,
            travelSlots: !!data.travel_slots
          });
        } else {
          // โหมดถาม: แสดง plan แม้ workflow ยังไม่เสร็จ (เพื่อให้เห็น progress)
          setSelectedPlan(data.current_plan);
          setSelectedTravelSlots(data.travel_slots || null);
          // ✅ Update latestBotMessage with agentState
          if (data.agent_state) {
            setLatestBotMessage(prev => prev ? { ...prev, agentState: data.agent_state } : { agentState: data.agent_state });
          }
          console.log('✅ Plan set (workflow in progress):', {
            choiceId,
            currentSlot,
            slotIntent: data.slot_intent
          });
        }
      } else {
        // ✅ Clear old selectedPlan if no current_plan
        setSelectedPlan(null);
        setSelectedTravelSlots(null);
        console.warn('⚠️ No current_plan:', {
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
      setProcessingTripId(null);
    }
  };

  // ===== Quick suggestions จากบอท =====
  const handleSuggestionClick = (suggestionText) => {
    sendMessage(suggestionText);
  };

  // ===== Slot-based editing - พิมพ์ในแชทได้เลย ไม่ต้องมี popup =====

  /** แสดง SweetAlert คุณพึงพอใจแค่ไหน (ให้ดาว 1–5) แล้วส่ง feedback ไป backend */
  const showAgentEvaluationSwal = (accuracyScore, chatId) => {
    const uid = Date.now();
    const starContainerId = `agent-star-rating-${uid}`;
    const starValueId = `agent-star-value-${uid}`;
    return Swal.fire({
      icon: 'info',
      title: 'คุณพึงพอใจแค่ไหน',
      html: `
        <div style="text-align: left;">
          <p style="margin-bottom: 8px;">ให้คะแนน AI (ดาว):</p>
          <div id="${starContainerId}" style="font-size: 32px; letter-spacing: 6px; margin: 12px 0; cursor: pointer; user-select: none;">
            <span class="agent-star" data-rating="1" style="color:#ddd">★</span>
            <span class="agent-star" data-rating="2" style="color:#ddd">★</span>
            <span class="agent-star" data-rating="3" style="color:#ddd">★</span>
            <span class="agent-star" data-rating="4" style="color:#ddd">★</span>
            <span class="agent-star" data-rating="5" style="color:#ddd">★</span>
          </div>
          <input type="hidden" id="${starValueId}" value="0" />
        </div>
      `,
      confirmButtonText: 'ส่งคะแนน',
      showCancelButton: true,
      cancelButtonText: 'ข้าม',
      confirmButtonColor: '#2563eb',
      cancelButtonColor: '#6b7280',
      allowOutsideClick: true,
      didOpen: () => {
        const container = document.getElementById(starContainerId);
        const input = document.getElementById(starValueId);
        if (!container || !input) return;
        const stars = container.querySelectorAll('.agent-star');
        const setStars = (n) => {
          input.value = n;
          stars.forEach((el) => {
            const r = parseInt(el.getAttribute('data-rating'), 10);
            el.style.color = r <= n ? '#f59e0b' : '#ddd';
          });
        };
        stars.forEach((el) => {
          el.addEventListener('click', () => setStars(parseInt(el.getAttribute('data-rating'), 10)));
        });
      },
      preConfirm: () => {
        const v = parseInt(document.getElementById(starValueId)?.value || '0', 10);
        if (v < 1 || v > 5) {
          Swal.showValidationMessage('กรุณาให้ดาว 1–5 ก่อนส่งคะแนน');
          return false;
        }
        return v;
      }
    }).then((evalResult) => {
      if (evalResult?.value && typeof evalResult.value === 'number' && evalResult.value >= 1 && evalResult.value <= 5) {
        const stars = evalResult.value;
        const mode = chatMode === 'agent' ? 'agent' : 'ask';
        return fetch(`${API_BASE_URL}/api/chat/agent-feedback`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          credentials: 'include',
          body: JSON.stringify({ chat_id: chatId, stars, mode })
        }).then((res) => res.json()).then((data) => {
          if (data?.ok) Swal.fire({ icon: 'success', title: 'ขอบคุณค่ะ', text: 'คะแนนของท่านจะถูกนำไปปรับปรุงความแม่นยำ', timer: 2000, showConfirmButton: false });
          return evalResult;
        }).catch(() => evalResult);
      }
      return evalResult;
    });
  };

  const handleConfirmBooking = async () => {
    const tripId = activeTrip?.tripId;
    const chatId = activeTrip?.chatId || tripId;
    const targetId = activeTrip?.chatId || activeTrip?.tripId;
    if (!tripId) return;

    // ✅ ตรวจสอบว่ามี plan และ travel_slots หรือไม่
    if (!selectedPlan) {
      alert('⚠️ ยังไม่มีข้อมูลทริป กรุณารอให้ Agent สร้างแผนการเดินทางให้เสร็จก่อน');
      return;
    }

    setIsBooking(true);
    setBookingResult(null);
    setProcessingTripId(targetId);
    
    try {
      // ✅ ดึงข้อมูล plan และ travel_slots จาก selectedPlan และ selectedTravelSlots
      const plan = selectedPlan || {};
      const travelSlots = selectedTravelSlots || {};
      
      // ✅ คำนวณ total_price
      let totalPrice = 0.0;
      let currency = 'THB';
      
      if (plan.total_price) {
        totalPrice = parseFloat(plan.total_price) || 0;
        currency = plan.currency || 'THB';
      } else {
        // คำนวณจาก flight, hotel, transport
        if (plan.flight?.total_price) {
          totalPrice += parseFloat(plan.flight.total_price) || 0;
          currency = plan.flight.currency || currency;
        }
        if (plan.hotel && (plan.hotel.total_price != null || plan.hotel.price_total != null)) {
          totalPrice += parseFloat(plan.hotel.total_price ?? plan.hotel.price_total) || 0;
          currency = plan.hotel.currency || currency;
        }
        if (plan.transport && (plan.transport.price != null || plan.transport.price_amount != null)) {
          totalPrice += parseFloat(plan.transport.price ?? plan.transport.price_amount) || 0;
          currency = plan.transport.currency || currency;
        }
      }
      
      // ✅ สร้าง travel_slots จาก plan และ travelSlots
      // ✅ ใช้ข้อมูลจาก travelSlots ที่ backend ส่งมา (มี segments ที่ถูกต้อง)
      const bookingTravelSlots = {
        // ✅ ใช้ segments จาก travelSlots ถ้ามี (backend format)
        flights: travelSlots.flights || plan.flight?.segments || plan.flight?.outbound || [],
        accommodations: travelSlots.accommodations || plan.hotel?.segments || [],
        ground_transport: travelSlots.ground_transport || plan.transport?.segments || [],
        // ✅ เพิ่มข้อมูลพื้นฐาน
        origin_city: travelSlots.origin_city || travelSlots.origin || plan.flight?.outbound?.[0]?.from || plan.flight?.segments?.[0]?.from,
        destination_city: travelSlots.destination_city || travelSlots.destination || plan.flight?.inbound?.[0]?.to || plan.flight?.segments?.[plan.flight?.segments?.length - 1]?.to,
        departure_date: travelSlots.departure_date || travelSlots.start_date,
        return_date: travelSlots.return_date || travelSlots.end_date,
        adults: travelSlots.adults || travelSlots.guests || 1,
        children: travelSlots.children ?? travelSlots.children_2_11 ?? 0,
        infants: travelSlots.infants ?? (travelSlots.infants_with_seat ?? 0) + (travelSlots.infants_on_lap ?? 0),
        children_2_11: travelSlots.children_2_11 ?? travelSlots.children ?? 0,
        infants_with_seat: travelSlots.infants_with_seat ?? 0,
        infants_on_lap: travelSlots.infants_on_lap ?? 0,
        nights: travelSlots.nights
      };
      
      // ✅ Validate data before sending
      if (!plan || typeof plan !== 'object' || Object.keys(plan).length === 0) {
        alert('⚠️ ข้อมูลทริปไม่ครบถ้วน กรุณารอให้ Agent สร้างแผนการเดินทางให้เสร็จก่อน');
        setIsBooking(false);
        return;
      }
      
      if (!userId) {
        alert('⚠️ ไม่พบข้อมูลผู้ใช้ กรุณาเข้าสู่ระบบใหม่');
        setIsBooking(false);
        return;
      }
      
      // ✅ Ensure total_price is a valid number
      if (isNaN(totalPrice) || totalPrice < 0) {
        console.warn('⚠️ Invalid total_price, using 0:', totalPrice);
        totalPrice = 0;
      }
      
      const bookingPayload = {
        trip_id: tripId,
        chat_id: chatId,
        user_id: userId,
        plan: plan,
        travel_slots: bookingTravelSlots,
        total_price: totalPrice,
        currency: currency || 'THB',
        mode: chatMode || 'normal',
        auto_booked: false
      };
      // ✅ โหมดแก้ไขทริป: ส่ง ID การจองเดิม เพื่อให้ backend ยกเลิกอันเดิมแล้วจองอันใหม่ใน trip id เดิม
      if (editReplaceBookingId) {
        bookingPayload.replace_booking_id = editReplaceBookingId;
      }
      
      // ✅ Log payload for debugging
      console.log('📤 Sending booking request:', {
        trip_id: bookingPayload.trip_id,
        chat_id: bookingPayload.chat_id,
        user_id: bookingPayload.user_id,
        has_plan: !!bookingPayload.plan,
        plan_keys: bookingPayload.plan ? Object.keys(bookingPayload.plan) : [],
        has_travel_slots: !!bookingPayload.travel_slots,
        travel_slots_keys: bookingPayload.travel_slots ? Object.keys(bookingPayload.travel_slots) : [],
        total_price: bookingPayload.total_price,
        currency: bookingPayload.currency,
        mode: bookingPayload.mode
      });
      
      // Step 1: Create booking (pending payment)
      // ✅ ส่ง X-User-ID ให้ตรงกับ My Bookings เพื่อให้จองแล้วแสดงในรายการ
      const headers = { 'Content-Type': 'application/json' };
      const uid = user?.user_id || user?.id;
      if (uid) headers['X-User-ID'] = uid;
      const res = await fetch(`${API_BASE_URL}/api/booking/create`, {
        method: 'POST',
        headers,
        credentials: 'include',
        body: JSON.stringify(bookingPayload),
      });
      
      const data = await res.json().catch(() => null);
      
      if (!res.ok) {
        // ✅ Better error handling for validation errors
        let errorMsg = 'Booking failed';
        if (data) {
          if (data.detail) {
            if (Array.isArray(data.detail)) {
              // Pydantic validation errors
              errorMsg = data.detail.map(err => `${err.loc?.join('.')}: ${err.msg}`).join(', ');
            } else if (typeof data.detail === 'string') {
              errorMsg = data.detail;
            } else if (data.detail.message) {
              errorMsg = data.detail.message;
            } else {
              errorMsg = JSON.stringify(data.detail);
            }
          } else if (data.message) {
            errorMsg = data.message;
          }
        }
        
        console.error('❌ Booking error:', {
          status: res.status,
          statusText: res.statusText,
          data: data
        });
        
        const isAlreadyBooked = typeof errorMsg === 'string' && /already exists|booking for this trip already/i.test(errorMsg);
        const result = isAlreadyBooked
          ? {
              ok: false,
              already_booked: true,
              message: 'ทริปนี้จองไปแล้ว กรุณาแก้ไขการจองเดิมที่ "My Bookings"',
              detail: errorMsg,
            }
          : {
              ok: false,
              message: `❌ สร้างการจองไม่สำเร็จ: ${errorMsg}`,
              detail: data?.detail || errorMsg,
            };
        setBookingResult(result);
        appendMessageToTrip(targetId, {
          id: Date.now() + 1,
          type: 'bot',
          text: toMessageText(result.message),
        });
        if (isAlreadyBooked) {
          Swal.fire({
            icon: 'info',
            title: 'จองไปแล้ว',
            html: '<p>ทริปนี้มีการจองอยู่แล้ว กรุณาแก้ไขการจองเดิมที่ <strong>My Bookings</strong></p>',
            confirmButtonText: 'ไปที่ My Bookings',
            showCancelButton: true,
            cancelButtonText: 'ปิด',
            confirmButtonColor: '#2563eb',
            cancelButtonColor: '#6b7280',
          }).then((r) => {
            if (r.isConfirmed && onNavigateToBookings) onNavigateToBookings();
          });
        }
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
      const messageText = toMessageText(result.message);
      appendMessageToTrip(targetId, {
        id: Date.now() + 1,
        type: 'bot',
        text: messageText + '\nกรุณาชำระเงินเพื่อยืนยันการจอง\n\n📋 คุณสามารถดูรายการจองได้ที่ "My Bookings"',
        agentState: { intent: 'booking', step: 'pending_payment', steps: [] },
      });
      
      // ✅ โหมดแก้ไขทริป: หลังจองสำเร็จ เคลียร์สถานะแก้ไข
      if (editReplaceBookingId) {
        setEditReplaceBookingId(null);
        setIsEditMode(false);
      }
      
      // ✅ อัปเดต notification count หลังจากสร้าง booking สำเร็จ
      if (onRefreshNotifications) {
        onRefreshNotifications();
      }
      
      // ✅ Trigger event to refresh My Bookings (เมื่อเปิดอยู่จะโหลดใหม่)
      window.dispatchEvent(new Event('bookingCreated'));
      
      // ✅ โหมดถาม: แสดง SweetAlert คะแนนวัดผล AI (แบบเดียวกับโหมด Agent) หลังกดจอง
      showAgentEvaluationSwal(null, chatId).then(() => {
        if (onNavigateToBookings) onNavigateToBookings();
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
      setProcessingTripId(null);
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
      
      // ✅ Handle Redirect to Payment Gateway
      if (data && data.payment_url) {
        window.location.href = data.payment_url;
        return;
      }
      
      // Success - payment and booking confirmed (Mock or Direct)
      const result = {
        ok: true,
        message: data?.message || '✅ ชำระเงินและจองสำเร็จ',
        booking_reference: data?.booking_reference || null,
        status: data?.status || 'confirmed',
        needs_payment: false,
      };
      setBookingResult(result);
      
      // Show success message in chat — เก็บ currentPlan/travelSlots เพื่อให้ TripSummaryUI ยังแสดงหลังจอง
      const targetId = activeTrip?.chatId || activeTrip?.tripId;
      if (targetId) {
        const messageText = toMessageText(result.message);
        appendMessageToTrip(targetId, {
          id: Date.now() + 1,
          type: 'bot',
          text: messageText + 
                (result.booking_reference ? `\n📋 หมายเลขการจอง: ${result.booking_reference}` : '') +
                '\n\n📋 คุณสามารถดูรายการจองได้ที่ "My Bookings"',
          agentState: { intent: 'booking', step: 'completed', steps: [] },
          currentPlan: selectedPlan || null,
          travelSlots: selectedTravelSlots || null,
          workflowValidation: { current_step: 'completed', is_complete: true },
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
    // If we have selectedPlan in state, แนบกับข้อความบอทจริงเสมอ (ใช้ id ของ message จริง) เพื่อให้ isLatestWithPlan ตรงและ Trip Summary แสดงได้
    if (selectedPlan) {
      // หาข้อความบอทล่าสุดที่มี currentPlan (ไม่กรอง step เพื่อให้เจอแม้ backend ไม่ส่ง step)
      const lastBotWithPlan = [...messages]
        .slice()
        .reverse()
        .find(m => m.type === 'bot' && m.currentPlan && !m.text?.includes('ยังไม่มีช้อยส์'));
      
      if (lastBotWithPlan) {
        return {
          ...lastBotWithPlan,
          currentPlan: selectedPlan,
          travelSlots: selectedTravelSlots || lastBotWithPlan.travelSlots,
          agentState: lastBotWithPlan.agentState || { intent: 'edit', step: 'choice_selected', steps: [] },
        };
      }
      
      // ถ้าไม่มีข้อความที่มี currentPlan แต่มี selectedPlan (เช่นเพิ่งได้จาก stream) → ใช้ข้อความบอทล่าสุดเป็นตัวแนบ plan
      const lastBotMsg = [...messages].slice().reverse().find(m => m.type === 'bot');
      if (lastBotMsg) {
        return {
          ...lastBotMsg,
          currentPlan: selectedPlan,
          travelSlots: selectedTravelSlots || lastBotMsg.travelSlots,
          agentState: lastBotMsg.agentState || { intent: 'edit', step: 'choice_selected', steps: [] },
        };
      }
    }
    
    // Otherwise, find from messages (excluding error messages)
    const choiceSelectedMsg = [...messages]
      .slice()
      .reverse()
      .find(m => 
        m.type === 'bot' && 
        m.currentPlan &&
        m.agentState?.step === 'choice_selected' &&
        !m.text?.includes('ยังไม่มีช้อยส์')
      );
    
    if (choiceSelectedMsg) return choiceSelectedMsg;
    
    return [...messages]
      .slice()
      .reverse()
      .find(m => m.type === 'bot' && m.currentPlan && !m.text?.includes('ยังไม่มีช้อยส์'));
  }, [messages, selectedPlan, selectedTravelSlots]);

  const effectiveSelectedPlan = selectedPlan || latestBotWithPlan?.currentPlan || null;
  const effectiveSelectedTravelSlots = selectedTravelSlots || latestBotWithPlan?.travelSlots || null;

  // ✅ ข้อความบอท "ล่าสุด" ที่มี planChoices หรือ slotChoices — แสดงการ์ดเฉพาะข้อความนี้ข้อความเดียว (แก้บั๊กแชทซ้อนหลายครั้ง)
  const latestBotWithChoices = useMemo(() => {
    const msgs = activeTrip?.messages || [];
    return [...msgs].reverse().find(m =>
      m.type === 'bot' &&
      ((Array.isArray(m.planChoices) && m.planChoices.length > 0) || (Array.isArray(m.slotChoices) && m.slotChoices.length > 0))
    ) || null;
  }, [activeTrip?.messages]);

  const userProfile = useMemo(() => {
    if (!user) return null;
    // ดึงชื่อจาก user: ใช้ first_name/last_name (โปรไฟล์) ก่อน ไม่มีค่อยใช้ given_name/family_name (Google) หรือแบ่งจาก name
    const fullName = (user.name || '').trim();
    const parts = fullName.split(/\s+/).filter(Boolean);
    const first_name = (user.first_name || user.given_name || parts[0] || '').trim();
    const last_name = (user.last_name || user.family_name || parts.slice(1).join(' ') || '').trim();
    return {
      first_name,
      last_name,
      first_name_th: user.first_name_th || '',
      last_name_th: user.last_name_th || '',
      national_id: user.national_id || '',
      email: user.email || '',
      phone: user.phone || '',
      dob: user.dob || '',
      gender: user.gender || '',
      passport_no: user.passport_no || '',
      passport_expiry: user.passport_expiry || '',
      passport_issue_date: user.passport_issue_date || '',
      passport_issuing_country: user.passport_issuing_country || '',
      passport_given_names: user.passport_given_names || '',
      passport_surname: user.passport_surname || '',
      nationality: user.nationality || '',
      place_of_birth: user.place_of_birth || '',
      // ข้อมูลวีซ่า / โรงแรม / อื่นๆ จากโปรไฟล์
      ...(user.visa_type && { visa_type: user.visa_type }),
      ...(user.visa_number && { visa_number: user.visa_number }),
      ...(user.visa_issue_date && { visa_issue_date: user.visa_issue_date }),
      ...(user.visa_expiry_date && { visa_expiry_date: user.visa_expiry_date }),
      ...(user.visa_issuing_country && { visa_issuing_country: user.visa_issuing_country }),
      ...(user.visa_entry_type && { visa_entry_type: user.visa_entry_type }),
      ...(user.visa_purpose && { visa_purpose: user.visa_purpose }),
    };
  }, [user]);

  const getTypingText = () => {
    // ✅ แสดงสถานะการทำงานแบบ realtime จาก SSE
    if (agentStatus && agentStatus.message) {
      return agentStatus.message;
    }
    
    // Fallback: ใช้ agent_state ถ้าไม่มี realtime status
    if (!currentAgentState) return 'กำลังเริ่มต้น...';

    // ✅ ใช้ step จาก agent_state (backend ส่งมาเป็น step ไม่ใช่ intent)
    const step = currentAgentState.step;
    const intent = currentAgentState.intent; // สำหรับ backward compatibility
    
    // ตรวจสอบ step ก่อน (ใหม่)
    if (step) {
      switch (step) {
        case 'start':
          return 'กำลังเริ่มต้น...';
        case 'planning':
          return 'กำลังวางแผนทริป...';
        case 'trip_summary':
          return 'กำลังสรุปทริปให้คุณ...';
        case 'choice_selected':
          return 'กำลังอัปเดตแพลน...';
        case 'no_previous_choices':
          return 'กำลังค้นหาตัวเลือก...';
        default:
          // ถ้ามี slot_workflow ให้แสดงข้อมูลเพิ่มเติม
          if (currentAgentState.slot_workflow?.current_slot) {
            const slot = currentAgentState.slot_workflow.current_slot;
            if (slot === 'summary') return 'กำลังสรุปทริปให้คุณ...';
            if (slot === 'flight') return 'กำลังจัดการเที่ยวบิน...';
            if (slot === 'hotel') return 'กำลังจัดการที่พัก...';
            if (slot === 'transfer' || slot === 'transport') return 'กำลังจัดการการเดินทาง...';
          }
          return 'กำลังคิดคำตอบให้คุณ...';
      }
    }
    
    // Fallback: ใช้ intent (สำหรับ backward compatibility)
    if (intent) {
      switch (intent) {
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
    }
    
    return 'กำลังคิดคำตอบให้คุณ...';
  };

  // ✅ Tool info mapping based on step
  const getToolInfo = (step) => {
    const toolMap = {
      'search_flights': '🔍 กำลังค้นหาเที่ยวบิน...',
      'search_hotels': '🏨 กำลังค้นหาที่พัก...',
      'search_transfers': '🚗 กำลังค้นหาการเดินทาง...',
      'search_activities': '🎯 กำลังค้นหากิจกรรม...',
      'geocode_location': '📍 กำลังค้นหาตำแหน่ง...',
      'find_nearest_airport': '✈️ กำลังค้นหาสนามบินใกล้เคียง...',
      'get_place_details': '📋 กำลังดึงข้อมูลสถานที่...',
      'thinking': '🤔 กำลังคิด...',
      'recall': '🧠 กำลังระลึกความจำ...',
      'processing': '⚙️ กำลังประมวลผล...',
    };
    // ไม่แสดง heartbeat (เอาออกตามที่ผู้ใช้ขอ)
    if (step === 'heartbeat') return null;
    return toolMap[step] || null;
  };

  const theme = useTheme();
  const { t } = useLanguage();
  const fontSize = useFontSize();

  // ===== UI =====
  return (
    <ChatErrorBoundary>
    <div className="chat-container" data-theme={theme} data-font-size={fontSize}>
      {/* Header */}
      <AppHeader
        activeTab="ai"
        user={user}
        onNavigateToHome={onNavigateToHome}
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
        isConnected={isConnected}
        notificationCount={notificationCount}
        notifications={notifications}
        onNavigateToProfile={onNavigateToProfile}
        onNavigateToSettings={onNavigateToSettings}
        onMarkNotificationAsRead={onMarkNotificationAsRead}
      />

      {/* Main: Sidebar + Chat */}
      <main 
        className={`chat-main chat-main-split ${isSidebarOpen ? 'sidebar-open' : 'sidebar-closed'}`}
        data-theme={theme}
        data-font-size={fontSize}
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
            <div className="trip-sidebar-title">{t('chat.tripHistory')}</div>
            <div className="trip-sidebar-header-actions">
              <button 
                className="trip-new-btn" 
                onClick={handleNewTrip}
                title={isSidebarOpen ? t('chat.newTrip') : t('chat.newTrip')}
              >
                {isSidebarOpen ? t('chat.newTrip') : '+'}
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
                {isLoadingSessions && (
                  <div className="trip-list-loading">
                    {[1, 2, 3].map(i => (
                      <div key={i} className="trip-item-skeleton">
                        <div className="skeleton-title" />
                        <div className="skeleton-sub" />
                      </div>
                    ))}
                  </div>
                )}
                {!isLoadingSessions && sortedTrips.map((t, idx) => {
                  // ✅ ตรวจสอบว่าเป็น active chat (ใช้ chatId)
                  const isActive = (t.chatId || t.tripId) === (activeChat?.chatId || activeChat?.tripId || activeTripId);
                  const isEditing = editingTripId === t.tripId;
                  const isProcessing = processingTripId === t.tripId;
                  const baseId = t.chatId ?? t.tripId;
                  const uniqueKey = baseId != null ? `trip-${baseId}-${idx}` : `trip-idx-${idx}`;
                  return (
                    <div
                      key={uniqueKey}
                      className={`trip-item ${isActive ? 'trip-item-active' : ''} ${t.pinned ? 'trip-item-pinned' : ''}`}
                      onClick={() => {
                        if (!isEditing) {
                          const id = t.chatId || t.tripId;
                          setActiveTripId(id);
                          // โหลดประวัติแชททันทีเมื่อคลิก — ไม่รอ useEffect
                          loadHistoryForChat(id);
                        } else {
                          console.log('⚠️ Cannot switch while editing this trip');
                        }
                      }}
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
                            {isProcessing && <div className="trip-spinner" title="กำลังประมวลผล..."></div>}
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
                        <div className="trip-item-sub">อัปเดต: {shortDate(t.updatedAt)}</div>
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
              </div>
            </div>
            
            <div className="chatbox-header-right">
              {/* ✅ Chat Mode Toggle - โหมดแก้ไขบังคับใช้ Normal เท่านั้น */}
              <div className="chat-mode-toggle" style={{
                display: 'flex',
                alignItems: 'center',
                gap: '8px',
                marginRight: '12px',
                padding: '4px',
                background: 'rgba(255, 255, 255, 0.1)',
                borderRadius: '8px',
                fontSize: '13px'
              }}>
                {isEditMode && (
                  <>
                    <span style={{ fontSize: '11px', color: 'rgba(255,255,255,0.7)', marginRight: '4px' }} title="โหมดแก้ไขใช้ได้เฉพาะ Normal">
                      ✏️ แก้ไข
                    </span>
                    {editModeMessageForRerun && (
                      <button
                        type="button"
                        onClick={() => {
                          if (editModeMessageForRerun && !isTyping) sendMessage(editModeMessageForRerun);
                        }}
                        disabled={isTyping}
                        title="ส่งข้อความแก้ไขทริปอีกครั้ง เพื่อรัน Flow ใหม่"
                        style={{
                          padding: '4px 10px',
                          borderRadius: '6px',
                          border: '1px solid rgba(255,255,255,0.3)',
                          background: 'rgba(59, 130, 246, 0.25)',
                          color: '#fff',
                          cursor: isTyping ? 'not-allowed' : 'pointer',
                          fontSize: '12px',
                          opacity: isTyping ? 0.7 : 1
                        }}
                      >
                        🔄 รัน Flow ใหม่
                      </button>
                    )}
                  </>
                )}
                {/* Desktop: Show both buttons (Agent ปิดเมื่อโหมดแก้ไข) */}
                <div className="chat-mode-toggle-desktop">
                  <button
                    onClick={() => {
                      if (isEditMode) return;
                      setChatMode('normal');
                      localStorage.setItem('chat_mode', 'normal');
                    }}
                    style={{
                      padding: '6px 12px',
                      borderRadius: '6px',
                      border: 'none',
                      background: chatMode === 'normal' ? 'rgba(59, 130, 246, 0.3)' : 'transparent',
                      color: chatMode === 'normal' ? '#fff' : 'rgba(255, 255, 255, 0.7)',
                      cursor: isEditMode ? 'default' : 'pointer',
                      fontWeight: chatMode === 'normal' ? '600' : '400',
                      transition: 'all 0.2s'
                    }}
                    title={isEditMode ? 'โหมดแก้ไขใช้ได้เฉพาะโหมดถาม' : 'โหมดถาม - คุณเลือกช้อยส์เอง'}
                  >
                    📋 โหมดถาม
                  </button>
                  <button
                    onClick={() => {
                      if (isEditMode) return; // โหมดแก้ไขห้ามสลับไป Agent
                      setChatMode('agent');
                      localStorage.setItem('chat_mode', 'agent');
                    }}
                    disabled={isEditMode}
                    style={{
                      padding: '6px 12px',
                      borderRadius: '6px',
                      border: 'none',
                      background: chatMode === 'agent' ? 'rgba(139, 92, 246, 0.3)' : 'transparent',
                      color: isEditMode ? 'rgba(255,255,255,0.4)' : (chatMode === 'agent' ? '#fff' : 'rgba(255, 255, 255, 0.7)'),
                      cursor: isEditMode ? 'not-allowed' : 'pointer',
                      fontWeight: chatMode === 'agent' ? '600' : '400',
                      transition: 'all 0.2s',
                      opacity: isEditMode ? 0.6 : 1
                    }}
                    title={isEditMode ? 'โหมดแก้ไขใช้ได้เฉพาะโหมดถาม' : 'โหมด Agent - AI ดำเนินการเองทั้งหมด'}
                  >
                    🤖 โหมด Agent
                  </button>
                </div>
                
                {/* Mobile: Dropdown (โหมดแก้ไข = แสดงเฉพาะ Normal, ไม่ให้เลือก Agent) */}
                <div className="chat-mode-toggle-mobile" ref={chatModeDropdownRef}>
                  <button
                    className="chat-mode-dropdown-button"
                    onClick={() => !isEditMode && setIsChatModeDropdownOpen(!isChatModeDropdownOpen)}
                    title={isEditMode ? 'โหมดแก้ไขใช้ได้เฉพาะโหมดถาม' : (chatMode === 'normal' ? 'โหมดถาม' : 'โหมด Agent')}
                    style={isEditMode ? { cursor: 'default' } : {}}
                  >
                    <span>{chatMode === 'normal' ? '📋 โหมดถาม' : '🤖 โหมด Agent'}</span>
                    {!isEditMode && (
                      <svg className="chat-mode-dropdown-icon" fill="currentColor" viewBox="0 0 24 24">
                        <path d="M7 10l5 5 5-5z"/>
                      </svg>
                    )}
                  </button>
                  
                  {isChatModeDropdownOpen && !isEditMode && (
                    <div className="chat-mode-dropdown-menu">
                      <button
                        className={`chat-mode-dropdown-item ${chatMode === 'normal' ? 'active' : ''}`}
                        onClick={() => {
                          setChatMode('normal');
                          localStorage.setItem('chat_mode', 'normal');
                          setIsChatModeDropdownOpen(false);
                        }}
                      >
                        <span>📋 โหมดถาม</span>
                        {chatMode === 'normal' && <span className="chat-mode-check">✓</span>}
                      </button>
                      <button
                        className={`chat-mode-dropdown-item ${chatMode === 'agent' ? 'active' : ''}`}
                        onClick={() => {
                          setChatMode('agent');
                          localStorage.setItem('chat_mode', 'agent');
                          setIsChatModeDropdownOpen(false);
                        }}
                      >
                        <span>🤖 โหมด Agent</span>
                        {chatMode === 'agent' && <span className="chat-mode-check">✓</span>}
                      </button>
                    </div>
                  )}
                </div>
              </div>
            </div>
          </div>

          {/* Connection error banner — แสดงเมื่อเชื่อมต่อ backend ไม่ได้ พร้อมปุ่มลองใหม่ */}
          {connectionError && (
            <div
              className="connection-error-banner"
              style={{
                padding: '10px 14px',
                margin: '0 12px 10px',
                background: 'rgba(239, 68, 68, 0.15)',
                border: '1px solid rgba(239, 68, 68, 0.4)',
                borderRadius: '8px',
                color: '#fef2f2',
                fontSize: '13px',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'space-between',
                flexWrap: 'wrap',
                gap: '8px'
              }}
            >
              <span style={{ flex: 1, minWidth: 0 }}>⚠️ {connectionError}</span>
              <button
                type="button"
                onClick={() => {
                  setConnectionError(null);
                  checkApiConnection();
                }}
                style={{
                  padding: '6px 12px',
                  borderRadius: '6px',
                  border: '1px solid rgba(255,255,255,0.3)',
                  background: 'rgba(255,255,255,0.15)',
                  color: '#fff',
                  cursor: 'pointer',
                  fontWeight: 600,
                  fontSize: '12px'
                }}
              >
                ลองใหม่
              </button>
            </div>
          )}

          {/* Booking Progress Bar — shown in โหมดถาม when funnel is active */}
          {chatMode !== 'agent' && (
            <BookingProgressBar
              funnelState={latestBotMessage?.agentState?.booking_funnel_state || 'idle'}
            />
          )}

          {/* Messages Area */}
          <div className="messages-area">
            <div className="messages-list">
              {/* ✅ แสดง loading indicator เมื่อกำลังโหลด history */}
              {isLoadingHistory && (
                <div className="message-wrapper message-left">
                  <div className="message-content-wrapper">
                    <div className="typing-bubble" style={{ padding: '1rem 1.5rem' }}>
                      <span className="typing-text">กำลังโหลดประวัติการสนทนา</span>
                      <div className="typing-dots">
                        <div className="typing-dot"></div>
                        <div className="typing-dot"></div>
                        <div className="typing-dot"></div>
                      </div>
                    </div>
                  </div>
                </div>
              )}
              {!isLoadingHistory && activeTrip?._loadError && (
                <div className="message-wrapper message-left">
                  <div className="message-content-wrapper">
                    <div className="message-bubble message-bot message-error" style={{ maxWidth: '85%' }}>
                      <p className="message-text">โหลดประวัติแชทไม่สำเร็จ (เซิร์ฟเวอร์หรือการเชื่อมต่อขัดข้อง) กรุณาลองใหม่หรือเริ่มแชทใหม่</p>
                    </div>
                  </div>
                </div>
              )}
              {!isLoadingHistory && !activeTrip?._loadError && messages
                .filter(message => {
                  // ซ่อน tool role messages และ assistant JSON tool call messages
                  if (message.type === 'tool') return false;
                  if (isToolCallText(message.text || '')) return false;
                  return true;
                })
                .map((message, msgIdx) => (
                <div
                  key={message.id != null && message.id !== '' ? `msg-${message.id}-${msgIdx}` : `msg-idx-${msgIdx}`}
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
                      {/* ข้อความหลัก — แสดงช่องว่างเมื่อข้อความว่างเพื่อไม่ให้บับเบิลแบน */}
                      <p className="message-text">{formatMessageText(message.text) || '\u00A0'}</p>

                      {/* ✅ Retry Button for Error Messages */}
                      {message.error && message.retryAvailable && message.onRetry && (
                        <div style={{
                          marginTop: '12px',
                          padding: '12px',
                          background: 'rgba(220, 38, 38, 0.1)',
                          borderRadius: '8px',
                          border: '1px solid rgba(220, 38, 38, 0.3)'
                        }}>
                          <p style={{ marginBottom: '8px', fontSize: '13px', opacity: 0.9 }}>
                            ไม่สามารถเชื่อมต่อกับเซิร์ฟเวอร์ได้
                          </p>
                          <button
                            onClick={() => {
                              if (message.onRetry) {
                                message.onRetry();
                              }
                            }}
                            style={{
                              padding: '6px 16px',
                              background: '#2563eb',
                              color: '#fff',
                              border: 'none',
                              borderRadius: '6px',
                              cursor: 'pointer',
                              fontSize: '13px',
                              fontWeight: '500'
                            }}
                          >
                            🔄 ลองอีกครั้ง
                          </button>
                        </div>
                      )}

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
                                {formatPriceInThb(message.currentPlan.summary.total_price, message.currentPlan.summary.currency)}
                              </div>
                            )}
                          </div>
                        </div>
                      )}

                          {(() => {
                            // ✅ Seamless workflow: หลังเลือกช้อยส์ ให้แสดง Trip Summary + Edit + User + Confirm ต่อเนื่อง
                            // ใช้ plan เดียว (selectedPlan หลัก) เพื่อไม่ให้การ์ดกระพริบเมื่อ message.currentPlan เป็น null ชั่วคราว
                            const plan = selectedPlan || message.currentPlan;
                            const hasPlan = !!plan;
                            
                            // Helper to check if CORE segments (Flight OR Hotel) are ready
                            const checkCoreSegmentsReady = (p) => {
                              if (!p) {
                                // ✅ Debug only - not an error, just means plan hasn't been created yet
                                console.debug('checkCoreSegmentsReady: No plan provided (this is normal for new chats)');
                                return false;
                              }
                              
                              // ✅ Flatten all segments — รองรับทั้ง structure เก่าและใหม่
                              const flights = p.travel?.flights
                                ? [...(p.travel.flights.outbound || []), ...(p.travel.flights.inbound || [])]
                                : p.flight?.segments?.length > 0
                                  ? p.flight.segments
                                  : p.flight?.outbound?.length > 0 || p.flight?.inbound?.length > 0
                                    ? [...(p.flight.outbound || []), ...(p.flight.inbound || [])]
                                    : Array.isArray(p.flights) ? p.flights : [];
                                
                              const accommodations = p.accommodation?.segments || p.hotel?.segments || p.accommodations || [];
                              const ground = p.travel?.ground_transport || p.ground_transport || [];
                              
                              // ✅ Debug: log structure (only in debug mode)
                              if (process.env.NODE_ENV === 'development') {
                                console.debug('checkCoreSegmentsReady:', {
                                  hasTravelFlights: !!p.travel?.flights,
                                  flightsCount: flights.length,
                                  accommodationsCount: accommodations.length,
                                  flights: flights.map(f => ({ status: f.status, id: f.selected_option?.id })),
                                  accommodations: accommodations.map(a => ({ status: a.status, id: a.selected_option?.id }))
                                });
                              }
                              
                              // ✅ ตรวจสอบ Core Segments (Flight OR Hotel)
                              // รองรับทั้ง status เป็น string ('confirmed') และ enum value
                              // และรองรับกรณีที่ไม่มี status แต่มีข้อมูลจริง (เช่น plan จาก agent)
                              const isSegmentReady = (seg) => {
                                const status = seg?.status || seg?.selected_option?.status;
                                if (status) return status === 'confirmed' || status === 'CONFIRMED' || status === 'selected' || status === 'SELECTED';
                                // ถ้าไม่มี status แต่มีข้อมูล segment จริง ถือว่า ready
                                return !!(seg?.from || seg?.carrier || seg?.hotelName || seg?.hotelId || seg?.selected_option);
                              };
                              const hasConfirmedFlights = flights.length > 0 && flights.some(isSegmentReady);
                              const hasConfirmedHotels = accommodations.length > 0 && accommodations.some(isSegmentReady);
                              
                              // ✅ ถ้า plan มี flight/hotel data โดยตรง (flat structure) ให้ถือว่า ready
                              const hasFlatFlight = !!(p.flight?.segments?.length > 0 || p.flight?.outbound?.length > 0 || p.flight?.carrier || (p.flight && (p.flight.departure || p.flight.arrival)));
                              const hasFlatHotel = !!(p.hotel?.segments?.length > 0 || p.hotel?.hotelName || p.accommodation?.segments?.length > 0);
                              // ✅ รองรับ plan จาก backend ที่มี total_price / summary (แสดง Summary ได้แม้ structure ไม่ตรงทุกแบบ)
                              const hasSummaryOrPrice = !!((p.total_price != null && p.total_price > 0) || (p.summary?.total_price > 0) || (p.flight && (p.flight.total_price || p.flight.price)));
                              
                              if (process.env.NODE_ENV === 'development') {
                                console.debug('Core segments ready:', { hasConfirmedFlights, hasConfirmedHotels, hasFlatFlight, hasFlatHotel, hasSummaryOrPrice });
                              }
                              
                              return hasConfirmedFlights || hasConfirmedHotels || hasFlatFlight || hasFlatHotel || hasSummaryOrPrice;
                            };

                            const isCoreReady = checkCoreSegmentsReady(plan);
                            
                            // ✅ แสดง TripSummaryCard เมื่อ: เป็น bot, มี plan, Core segments พร้อม, workflow ถึง summary
                            const workflowValidation = message.workflowValidation || message.agentState?.workflow_validation || {};
                            const currentWorkflowStep = workflowValidation.current_step || message.agentState?.step || "planning";
                            const isWorkflowComplete = workflowValidation.is_complete || false;
                            const isAgentModeMsg = chatMode === 'agent';
                            const canShowSummary = currentWorkflowStep === "trip_summary" ||
                                                  currentWorkflowStep === "summary" ||
                                                  currentWorkflowStep === "completed" ||
                                                  currentWorkflowStep === "confirmed" ||
                                                  currentWorkflowStep === "booking" ||
                                                  (isCoreReady && isWorkflowComplete) ||
                                                  // ✅ Agent mode: แสดงเมื่อ core ready แม้ workflow step ไม่ตรง
                                                  (isAgentModeMsg && isCoreReady) ||
                                                  // ✅ แสดงเมื่อมี plan + core ready (เที่ยวบิน/ที่พักยืนยันแล้ว) แม้ workflow ยัง selecting (เช่นรอแค่ transfer)
                                                  (isCoreReady && hasPlan);
                            
                            // ✅ แสดงเฉพาะข้อความล่าสุดที่มี plan (รวมจองสำเร็จ) — ป้องกันซ้อน
                            const isLatestWithPlan = latestBotWithPlan && message.id === latestBotWithPlan.id;
                            // ✅ แสดง Trip Summary ก็ต่อเมื่อมีคำว่า "จองเลย" (ในข้อความบอทหรือผู้ใช้เคยพิมพ์จองเลย หรือกำลังแก้ไขและพิมพ์จองเลย) นอกนั้นห้ามแสดง
                            const messageText = formatMessageText(message.text || '');
                            const inputSaysBookNow = /จอง\s*เลย/.test(String(inputText || '').trim());
                            const hasBookNowKeyword = messageText.includes('จองเลย') || showTripSummary || (editingMessageId && inputSaysBookNow);
                            const shouldShow = message.type === 'bot' &&
                                   hasPlan &&
                                   isCoreReady &&
                                   canShowSummary &&
                                   !message.text?.includes('❌') &&
                                   isLatestWithPlan &&
                                   hasBookNowKeyword;
                            
                            return shouldShow;
                          })() && (
                            <div className="plan-choices-block full-width-block">
                              <TripSummaryCard 
                                plan={selectedPlan || message.currentPlan} 
                                travelSlots={selectedTravelSlots || message.travelSlots} 
                                cachedOptions={message.cachedOptions || finalData?.cached_options}
                                cacheValidation={message.cacheValidation || finalData?.cache_validation}
                                workflowValidation={message.workflowValidation || message.agentState?.workflow_validation}
                              />
                              {/* Slot-based editing cards */}
                              <div className="slots-container">
                                <FlightSlotCard 
                                  flight={
                                    selectedPlan?.flight || 
                                    message.currentPlan?.flight ||
                                    (selectedTravelSlots?.flight || message.travelSlots?.flight)
                                  } 
                                />
                                <TransportSlotCard 
                                  transport={
                                    selectedPlan?.transport || 
                                    message.currentPlan?.transport ||
                                    (selectedTravelSlots?.transport || message.travelSlots?.transport)
                                  } 
                                />
                                <HotelSlotCard 
                                  hotel={
                                    selectedPlan?.hotel || 
                                    message.currentPlan?.hotel ||
                                    (selectedTravelSlots?.hotel || message.travelSlots?.hotel)
                                  }
                                  travelSlots={selectedTravelSlots || message.travelSlots}
                                />
                              </div>
                              {/* ✅ Final Trip Summary - แสดงก่อนจอง */}
                              <FinalTripSummary
                                plan={selectedPlan || message.currentPlan}
                                travelSlots={selectedTravelSlots || message.travelSlots}
                                userProfile={userProfile}
                                cachedOptions={message.cachedOptions || finalData?.cached_options}
                                cacheValidation={message.cacheValidation || finalData?.cache_validation}
                                workflowValidation={message.workflowValidation || message.agentState?.workflow_validation}
                              />
                              <UserInfoCard 
                                userProfile={userProfile} 
                                onEdit={handleEditUserProfile}
                                isDomesticTravel={(() => {
                                  const slots = selectedTravelSlots || message.travelSlots;
                                  if (!slots) return false;
                                  const origin = slots.origin_city || slots.origin || '';
                                  const dest = slots.destination_city || slots.destination || '';
                                  return isLocationInThailand(origin) && isLocationInThailand(dest);
                                })()}
                              />
                              <ConfirmBookingCard
                                canBook={!!selectedPlan && !!userProfile}
                                onConfirm={handleConfirmBooking}
                                onPayment={handlePayment}
                                onNavigateToBookings={onNavigateToBookings}
                                note="ระบบจะจองเฉพาะ Amadeus Sandbox (test) เท่านั้น"
                                isBooking={isBooking}
                                bookingResult={bookingResult}
                                chatMode={chatMode}
                                agentState={latestBotMessage?.agentState || null}
                              />
                            </div>
                          )}

                      {/* ✅ ซ่อน suggestion chips ตามที่ผู้ใช้ขอ */}
                      
                      {/* ✅ Header/Summary ย้ายกลับเข้ามาใน Bubble เพื่อให้เป็นส่วนหนึ่งของบทสนทนา */}
                      {message.type === 'bot' && (
                        <>
                          {/* 1. Slot Choices Summary - Agent Mode ไม่แสดง (ซ่อน "ตัวเลือกเที่ยวบิน X รายการ") */}
                          {chatMode !== 'agent' && message.slotChoices && message.slotChoices.length > 0 && message.slotIntent && (() => {
                            const isMulti = message.slotIntent === 'multi';
                            const filteredCount = isMulti
                              ? message.slotChoices.length
                              : message.slotChoices.filter(choice => {
                                  if (message.slotIntent === 'transport' || message.slotIntent === 'transfer') {
                                    return choice.category === 'transport' || choice.category === 'transfer';
                                  }
                                  return choice.category === message.slotIntent;
                                }).length;
                            
                            if (filteredCount === 0) return null;
                            
                            return (
                              <div className="plan-choices-summary-in-bubble">
                                <span className="summary-icon">📝</span>
                                <span className="summary-text">
                                  {message.slotIntent === 'flight' && 'ตัวเลือกเที่ยวบิน'}
                                  {message.slotIntent === 'hotel' && 'ตัวเลือกที่พัก'}
                                  {(message.slotIntent === 'transport' || message.slotIntent === 'transfer') && 'ตัวเลือกการเดินทาง'}
                                  {(message.slotIntent === 'multi' || !['flight', 'hotel', 'transport', 'transfer'].includes(message.slotIntent)) && 'ตัวเลือก'}
                                  {' '}({filteredCount} รายการ)
                                </span>
                              </div>
                            );
                          })()}

                          {/* 2. Plan Choices Summary - Agent Mode ไม่แสดง (การ์ดถูกซ่อนแล้ว) */}
                          {(() => {
                            if (chatMode === 'agent') return null;
                            const hasPlanChoices = message.planChoices && 
                              Array.isArray(message.planChoices) && 
                              message.planChoices.length > 0;
                            const hasSlotChoices = message.slotChoices && message.slotChoices.length > 0;
                            const shouldShowPlanChoices = hasPlanChoices && 
                                   (!hasSlotChoices || !message.slotIntent);
                            return shouldShowPlanChoices ? (
                              <div className="plan-choices-summary-in-bubble">
                                <span className="summary-icon">✈️</span>
                                <span className="summary-text">
                                  แผนเที่ยวที่จัดให้ทั้งหมด {message.planChoices.length} ช้อยส์
                                </span>
                              </div>
                            ) : null;
                          })()}
                        </>
                      )}
                    </div>
                    {/* ✅ End of Message Content Wrapper (Bubble ends here) */}

                    {/* ✅ ส่วนของการ์ด (Grid) อยู่นอก Bubble แบบ Full Width */}
                    {message.type === 'bot' && (
                      <>
                        {/* Debug: Log slotChoices for Admin Mode */}
                        {isAdmin && (() => {
                          console.log('🛠️ Admin Debug - Message slotChoices:', {
                            hasSlotChoices: !!message.slotChoices,
                            slotChoicesLength: message.slotChoices?.length || 0,
                            slotIntent: message.slotIntent,
                            slotChoices: message.slotChoices
                          });
                          return null;
                        })()}
                        
                        {/* 1. Slot Choices Grid - Agent Mode: ไม่แสดงการ์ดและไม่แสดงข้อความกลางขั้น (จบแล้วแจ้งทีเดียว) */}
                        {message.slotChoices && message.slotChoices.length > 0 && (() => {
                          if (chatMode === 'agent') return null;
                          const isLatestWithChoices = latestBotWithChoices && message.id === latestBotWithChoices.id;
                          const effectiveIntent = message.slotIntent || null;
                          const flightSelected = message.id != null && messageIdsWithFlightSelected.has(message.id);
                          const hotelSelected = message.id != null && messageIdsWithHotelSelected.has(message.id);
                          const getCat = (c) => {
                            if (c.category === 'flight') return 'flight';
                            if (c.category === 'hotel') return 'hotel';
                            if (c.category === 'transport' || c.category === 'transfer') return 'transport';
                            if (c.flight && (c.flight.segments?.length > 0 || c.flight.outbound?.length || c.flight.inbound?.length)) return 'flight';
                            if (c.hotel) return 'hotel';
                            if (c.transport || c.car || c.ground_transport) return 'transport';
                            return null;
                          };
                          const flightChoices = message.slotChoices.filter(c => getCat(c) === 'flight');
                          const hotelChoices = message.slotChoices.filter(c => getCat(c) === 'hotel');
                          const transportChoices = message.slotChoices.filter(c => getCat(c) === 'transport');
                          const hasMulti = effectiveIntent === 'multi' || (flightChoices.length > 0 && hotelChoices.length > 0) || (flightChoices.length > 0 && transportChoices.length > 0) || (hotelChoices.length > 0 && transportChoices.length > 0);
                          const showHotel = hotelChoices.length > 0 && (flightChoices.length === 0 || flightSelected);
                          const showTransport = transportChoices.length > 0 && (hotelChoices.length === 0 || hotelSelected);
                          const filteredChoices = hasMulti
                            ? [
                                ...flightChoices,
                                ...(showHotel ? hotelChoices : []),
                                ...(showTransport ? transportChoices : []),
                              ]
                            : message.slotChoices.filter(choice => {
                                if (!effectiveIntent || effectiveIntent === 'multi') return true;
                                if (effectiveIntent === 'transport' || effectiveIntent === 'transfer') return choice.category === 'transport' || choice.category === 'transfer';
                                return choice.category === effectiveIntent;
                              });
                          if (!isLatestWithChoices) {
                            return (
                              <div className="plan-choices-summary-compact" key="slot-summary-old">
                                <span className="summary-text">✈️ มี {message.slotChoices.length} ตัวเลือกให้เลือก (ดูตัวเลือกล่าสุดด้านล่าง)</span>
                              </div>
                            );
                          }
                          const getSlotCardComponent = (intent, choice) => {
                            if (!choice || typeof choice !== 'object') return PlanChoiceCard;
                            const cat = intent || getCat(choice);
                            if (cat === 'flight') return (choice.flight && (choice.flight.segments?.length > 0 || choice.flight.outbound?.length || choice.flight.inbound?.length)) ? PlanChoiceCardFlights : PlanChoiceCard;
                            if (cat === 'hotel') return choice.hotel ? PlanChoiceCardHotels : PlanChoiceCard;
                            if (cat === 'transport' || cat === 'transfer') return (choice.transport || choice.car || choice.ground_transport) ? PlanChoiceCardTransfer : PlanChoiceCard;
                            return PlanChoiceCard;
                          };
                          if (filteredChoices.length === 0) return null;
                          const outboundAlreadySelected = message.id != null && messageIdsWithOutboundSelected.has(message.id);
                          const isInboundFlightChoice = (c) => c?.flight_direction === 'inbound' || (c?.flight?.segments?.[0]?.direction && String(c.flight.segments[0].direction).includes('ขากลับ'));
                          const sortedChoices = effectiveIntent === 'flight' && flightChoices.length > 0
                            ? [...filteredChoices].sort((a, b) => (isInboundFlightChoice(a) ? 1 : 0) - (isInboundFlightChoice(b) ? 1 : 0))
                            : filteredChoices;
                          return (
                            <div className="plan-choices-block full-width-block" key="slot-choices-block">
                              {isAdmin && console.log('🛠️ Admin Debug - Rendering PlanChoiceCard grid:', sortedChoices.length, 'slotIntent:', effectiveIntent)}
                              <div className="plan-choices-grid">
                                {sortedChoices.map((choice, idx) => {
                                  const intent = effectiveIntent || getCat(choice);
                                  const SlotCard = getSlotCardComponent(intent, choice);
                                  const stableKey = `slot-${String(message.id ?? '')}-${idx}-${choice.id ?? choice._original_id ?? idx}`;
                                  const isFlightInbound = intent === 'flight' && isInboundFlightChoice(choice);
                                  const disableSelect = isFlightInbound && !outboundAlreadySelected;
                                  return (
                                    <SlotCard
                                      key={stableKey}
                                      choice={choice}
                                      onSelect={disableSelect ? undefined : (id) => handleSelectSlotChoice(id, intent || getCat(choice), choice, message)}
                                      disableSelect={disableSelect}
                                    />
                                  );
                                })}
                              </div>
                            </div>
                          );
                        })()}
                        
                        {/* Debug: slotChoices/slotIntent mismatch */}
                        {isAdmin && message.slotChoices && message.slotChoices.length > 0 && !message.slotIntent && (
                          console.log('⚠️ Admin Debug - slotChoices shown with inferred category (no slotIntent):', message.slotChoices.length)
                        )}
                        {isAdmin && message.slotIntent && (!message.slotChoices || message.slotChoices.length === 0) && (
                          console.log('⚠️ Admin Debug - slotIntent exists but no slotChoices:', message.slotIntent)
                        )}

                        {/* 2. Plan Choices Grid - Agent Mode: ไม่แสดง (จบแล้วแจ้งทีเดียว) */}
                        {(() => {
                          if (chatMode === 'agent') return null;
                          const hasPlanChoices = message.planChoices && 
                            Array.isArray(message.planChoices) && 
                            message.planChoices.length > 0;
                          const hasSlotChoices = message.slotChoices && message.slotChoices.length > 0;
                          const shouldShowPlanChoices = hasPlanChoices && 
                                 (!hasSlotChoices || !message.slotIntent);
                          const isLatestWithChoices = latestBotWithChoices && message.id === latestBotWithChoices.id;
                          
                          if (!shouldShowPlanChoices) return null;
                          if (!isLatestWithChoices) {
                            return (
                              <div className="plan-choices-summary-compact" key="plan-summary-old">
                                <span className="summary-text">✈️ แผนเที่ยวที่จัดให้ {message.planChoices.length} ช้อยส์ (ดูตัวเลือกล่าสุดด้านล่าง)</span>
                              </div>
                            );
                          }
                          const getPlanCardComponent = (choice) => {
                            if (!choice || typeof choice !== 'object') return PlanChoiceCard;
                            const cat = choice.category || (choice.flight ? 'flight' : choice.hotel ? 'hotel' : (choice.transport || choice.car) ? 'transport' : null);
                            if (cat === 'flight') return (choice.flight && (choice.flight.segments?.length > 0 || choice.flight.outbound?.length || choice.flight.inbound?.length)) ? PlanChoiceCardFlights : PlanChoiceCard;
                            if (cat === 'hotel') return choice.hotel ? PlanChoiceCardHotels : PlanChoiceCard;
                            if (cat === 'transport' || cat === 'transfer') return (choice.transport || choice.car || choice.ground_transport) ? PlanChoiceCardTransfer : PlanChoiceCard;
                            return PlanChoiceCard;
                          };
                          return (
                            <div className="plan-choices-block full-width-block">
                              <div className="plan-choices-grid">
                                {message.planChoices.map((choice, idx) => {
                                  const PlanCard = getPlanCardComponent(choice);
                                  return (
                                    <PlanCard
                                      key={choice.id || `choice-${choice.title || ''}-${idx}`}
                                      choice={choice}
                                      onSelect={(id) => handleSelectPlanChoice(id, choice)}
                                    />
                                  );
                                })}
                              </div>
                            </div>
                          );
                        })()}
                      </>
                    )}

                    {/* Action buttons under messages (ChatGPT style) — แสดงปุ่มรีเฟรชที่ข้อความล่าสุด */}
                    {message.type === 'user' && message.id === lastUserMessageId && (
                      <div className="message-actions message-actions-user">
                        <button
                          className="btn-action btn-refresh"
                          onClick={() => regenerateFromUserText(message.id, message.text)}
                          disabled={isTyping}
                          title="รีเฟรช"
                        >
                          🔄 รีเฟรช
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
                    
                    {/* Action buttons under bot messages — รีเฟรชได้ทุกข้อความ */}
                    {message.type === 'bot' && (
                      <div className="message-actions message-actions-bot">
                        <button
                          className="btn-action btn-refresh"
                          onClick={() => {
                            const tripMessages = activeTrip?.messages || [];
                            const botIdx = tripMessages.findIndex(m => m.id === message.id);
                            const before = tripMessages.slice(0, botIdx);
                            const userMsg = [...before].reverse().find(m => m.type === 'user');
                            if (userMsg) {
                              handleRefreshBot(userMsg.id, userMsg.text);
                            }
                          }}
                          disabled={isTyping || (() => {
                            const tripMessages = activeTrip?.messages || [];
                            const botIdx = tripMessages.findIndex(m => m.id === message.id);
                            const before = tripMessages.slice(0, botIdx);
                            const userMsg = [...before].reverse().find(m => m.type === 'user');
                            return !userMsg;
                          })()}
                          title="รีเฟรช"
                        >
                          🔄 รีเฟรช
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

              {/* Typing Indicator with Agent Activity (Cursor-style) */}
              {isTyping && (
                <div className="typing-indicator">
                  <div className="typing-bubble">
                    <div className="agent-activity-container">
                      <div className="agent-activity-icon">
                        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                          <circle cx="12" cy="12" r="10" opacity="0.3"/>
                          <circle cx="12" cy="12" r="2" className="agent-cursor-pulse"/>
                        </svg>
                      </div>
                      <div className="agent-activity-content">
                        <div className="typing-text">{getTypingText()}</div>
                        {/* ✅ Enhanced Loading State: Show tool info based on agentStatus.step */}
                        {agentStatus?.step && agentStatus.step !== 'heartbeat' && getToolInfo(agentStatus.step) && (
                          <div className="tool-info" style={{
                            fontSize: '12px',
                            color: 'rgba(255, 255, 255, 0.7)',
                            marginTop: '8px',
                            marginBottom: '8px',
                            fontStyle: 'italic'
                          }}>
                            {getToolInfo(agentStatus.step)}
                          </div>
                        )}
                        {agentStatus && (() => {
                          // ✅ แผนที่ขั้นตอนที่ละเอียดขึ้น - แสดงกระบวนการทำงานของ Agent
                          const stepMap = {
                            // Thinking & Planning
                            'thinking': '🤔 กำลังคิด...',
                            'recall_start': '🧠 กำลังระลึกความจำ...',
                            'controller_start': '🔄 กำลังเริ่มต้นประมวลผล...',
                            'controller_iter_1': '🔄 กำลังประมวลผล (รอบที่ 1/2)...',
                            'controller_iter_2': '🔄 กำลังประมวลผล (รอบที่ 2/2)...',
                            'controller_iter_3': '🔄 กำลังประมวลผล (รอบที่ 2/2)...',
                            
                            // Actions
                            'create_itinerary': '📋 กำลังสร้างแผนการเดินทาง...',
                            'update_req': '📝 กำลังอัปเดตข้อมูลทริป...',
                            'call_search': '🔍 กำลังค้นหา...',
                            'select_option': '✅ กำลังบันทึกตัวเลือก...',
                            
                            // Broker-style searching messages
                            'searching': '🔍 นายหน้ากำลังตรวจสอบตัวเลือกให้คุณ...',
                            'searching_flights': '✈️ นายหน้ากำลังตรวจสอบเที่ยวบินที่เหมาะสม...',
                            'searching_hotels': '🏨 นายหน้ากำลังคัดเลือกที่พักที่เหมาะกับคุณ...',
                            'call_search_done': '✅ ค้นหาเสร็จแล้ว กำลังคัดตัวเลือกที่ดีที่สุด...',
                            
                            // Agent Mode - Auto Selection & Booking
                            'agent_auto_select': '🤖 กำลังเลือกช้อยส์ที่ดีที่สุด...',
                            'agent_auto_select_immediate': '🤖 กำลังเลือกช้อยส์ทันที...',
                            'agent_auto_select_final': '🤖 กำลังเลือกช้อยส์ (รอบสุดท้าย)...',
                            'agent_analyze_flights_outbound': '📊 กำลังวิเคราะห์เที่ยวบินขาไป...',
                            'agent_analyze_flights_inbound': '📊 กำลังวิเคราะห์เที่ยวบินขากลับ...',
                            'agent_analyze_accommodation': '📊 กำลังวิเคราะห์ที่พัก...',
                            'agent_select_flights_outbound': '✅ เลือกเที่ยวบินขาไปแล้ว',
                            'agent_select_flights_inbound': '✅ เลือกเที่ยวบินขากลับแล้ว',
                            'agent_select_accommodation': '✅ เลือกที่พักแล้ว',
                            'agent_auto_book': '💳 กำลังจองทริปทันที...',
                            
                            // Analyzing
                            'analyzing': '📊 กำลังวิเคราะห์ข้อมูล...',
                            'planning': '📋 กำลังวางแผนทริป...',
                            'selecting': '🎯 กำลังเลือกตัวเลือกที่ดีที่สุด...',
                            'confirming': '✅ กำลังยืนยันข้อมูล...',
                            'booking': '💳 กำลังจองทริป...',
                            
                            // Broker-specific steps
                            'confirming_search': '📋 นายหน้ากำลังยืนยันรายละเอียดทริปก่อนค้นหา...',
                            'agent_auto_book_success': '🎉 จองสำเร็จแล้ว! ดูรายละเอียดใน My Bookings',

                            // Responding
                            'acting': '⚙️ กำลังดำเนินการ...',
                            'speaking': '💬 นายหน้ากำลังสรุปคำแนะนำ...',
                            'responder_start': '💬 นายหน้ากำลังสรุปคำแนะนำ...',
                          };
                          const statusMap = {
                            'thinking': '🤔 กำลังคิด...',
                            'recall': '🧠 กำลังระลึกความจำ...',
                            'searching': '🔍 กำลังค้นหา...',
                            'processing': '⚙️ กำลังประมวลผล...',
                            'analyzing': '📊 กำลังวิเคราะห์...',
                            'planning': '📋 กำลังวางแผน...',
                            'acting': '⚙️ กำลังดำเนินการ...',
                            'selecting': '🎯 กำลังเลือก...',
                            'confirming': '✅ กำลังยืนยัน...',
                            'booking': '💳 กำลังจอง...',
                            'speaking': '💬 กำลังตอบ...',
                          };
                          
                          return (
                            <>
                              {/* ✅ Step Title - แสดงขั้นตอนหลักที่ Agent กำลังทำ (ไม่แสดง heartbeat) */}
                              {agentStatus.step && agentStatus.step !== 'heartbeat' && (
                                <div className="agent-activity-step">
                                  {stepMap[agentStatus.step] || `⚙️ ${agentStatus.step}`}
                                </div>
                              )}
                              {/* ✅ Detailed Message - แสดงรายละเอียดเพิ่มเติมของกระบวนการทำงาน */}
                              {agentStatus.message && agentStatus.message !== getTypingText() && (() => {
                                const message = agentStatus.message || '';
                                const stepText = agentStatus.step ? 
                                  (stepMap[agentStatus.step] || agentStatus.step) : '';
                                
                                // ถ้า message มีรายละเอียดเพิ่มเติม และไม่เหมือนกับ step หรือ typing text
                                if (message && message !== stepText && message !== getTypingText()) {
                                  // ลบ stepText ออกจาก message ถ้ามี
                                  let detailMessage = message;
                                  if (stepText && detailMessage.includes(stepText)) {
                                    detailMessage = detailMessage.replace(stepText, '').trim();
                                  }
                                  // ลบ emoji ที่ซ้ำกับ step ออก (แต่เก็บรายละเอียดอื่นๆ)
                                  const stepEmoji = stepText.match(/^([🤔🧠🔄📋📝🔍✈️🏨📊🎯✅💳⚙️💬])\s*/)?.[1];
                                  if (stepEmoji && detailMessage.startsWith(stepEmoji)) {
                                    detailMessage = detailMessage.replace(/^[🤔🧠🔄📋📝🔍✈️🏨📊🎯✅💳⚙️💬]\s*/, '').trim();
                                  }
                                  
                                  // ✅ แสดงรายละเอียดถ้ามีข้อมูลเพิ่มเติม
                                  if (detailMessage && detailMessage.length > 0 && detailMessage !== stepText) {
                                    return (
                                      <div className="agent-activity-detail">
                                        {detailMessage}
                                      </div>
                                    );
                                  }
                                }
                                return null;
                              })()}
                              {/* ✅ Status Indicator - แสดงสถานะทั่วไป (ไม่แสดง heartbeat, ไม่ซ้ำกับ step) */}
                              {agentStatus.status && 
                               agentStatus.status !== 'heartbeat' &&
                               agentStatus.status !== 'thinking' && 
                               agentStatus.status !== agentStatus.step && 
                               !agentStatus.message?.includes(statusMap[agentStatus.status] || agentStatus.status) && (
                                <div className="agent-activity-status">
                                  {statusMap[agentStatus.status] || `📌 ${agentStatus.status}`}
                                </div>
                              )}
                            </>
                          );
                        })()}
                      </div>
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

          {/* Trip Summary UI จะถูกแสดงแบบ seamless อยู่ใน bubble ของบอท "ข้อความล่าสุดที่มี currentPlan" */}


          {/* Input Area */}
          <div className="input-area">
            {/* ✅ Edit mode banner — แสดงเมื่อกำลังแก้ไขข้อความ */}
            {editingMessageId && (
              <div className="edit-mode-banner">
                <span className="edit-mode-banner-icon">✏️</span>
                <span className="edit-mode-banner-text">กำลังแก้ไขข้อความ — แก้ไขแล้วกด Send หรือ Enter</span>
                <button
                  className="edit-mode-cancel-btn"
                  onClick={() => {
                    setEditingMessageId(null);
                    setInputText('');
                  }}
                  title="ยกเลิกการแก้ไข"
                >
                  ✕ ยกเลิก
                </button>
              </div>
            )}
            <div className={`input-wrapper${editingMessageId ? ' input-wrapper-editing' : ''}`}>
              <textarea
                ref={inputRef}
                value={inputText}
                onChange={(e) => setInputText(e.target.value)}
                onKeyPress={handleKeyPress}
                placeholder={editingMessageId ? 'แก้ไขข้อความแล้วกด Enter หรือ Send...' : t('chat.inputPlaceholder')}
                rows="1"
                className={`input-field${editingMessageId ? ' input-field-editing' : ''}`}
              />
              <button
                onClick={handleVoiceInput}
                className={`btn-mic ${isVoiceMode ? 'btn-mic-active' : ''}`}
                title={isVoiceMode ? 'กดเพื่อหยุดการสนทนาด้วยเสียง' : 'กดเพื่อเริ่มสนทนากับ Agent ด้วยเสียง'}
              >
                {isVoiceMode ? (
                  /* กำลังใช้งาน → แสดง stop square สีแดง */
                  <svg className="mic-icon" fill="currentColor" viewBox="0 0 24 24">
                    <rect x="5" y="5" width="14" height="14" rx="2"/>
                  </svg>
                ) : (
                  /* ปกติ → แสดงไมค์ */
                  <svg className="mic-icon" fill="currentColor" viewBox="0 0 24 24">
                    <path d="M12 14c1.66 0 3-1.34 3-3V5c0-1.66-1.34-3-3-3S9 3.34 9 5v6c0 1.66 1.34 3 3 3z" />
                    <path d="M17 11c0 2.76-2.24 5-5 5s-5-2.24-5-5H5c0 3.53 2.61 6.43 6 6.92V21h2v-3.08c3.39-.49 6-3.39 6-6.92h-2z" />
                  </svg>
                )}
              </button>
              {isTyping ? (
                <button onClick={handleStop} className="btn-send btn-send-stop" title="หยุดการทำงาน">
                  <svg fill="currentColor" viewBox="0 0 24 24" width="18" height="18">
                    <rect x="4" y="4" width="16" height="16" rx="2"/>
                  </svg>
                </button>
              ) : (
                <button onClick={handleSend} disabled={!inputText.trim()} className="btn-send">
                  Send
                </button>
              )}
            </div>

            {isVoiceMode && (
              <div className="voice-conversation-status">
                <div className="voice-status-indicator">
                  {isRecording ? (
                    <>
                      <span className="voice-pulse">🎤</span>
                      <span>กำลังฟัง... พูดได้เลย</span>
                    </>
                  ) : (
                    <>
                      <span>💬</span>
                      <span>รอ Agent ตอบกลับด้วยเสียง...</span>
                    </>
                  )}
                </div>
              </div>
            )}
            <div className="powered-by">{t('chat.poweredBy')}</div>
          </div>
        </div>

      </main>
    </div>
    </ChatErrorBoundary>
  );
}