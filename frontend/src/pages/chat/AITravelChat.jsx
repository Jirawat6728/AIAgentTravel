import React, { useState, useRef, useEffect, useMemo } from 'react';
import Swal from 'sweetalert2';
import './AITravelChat.css';
import AppHeader from '../../components/common/AppHeader';

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

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000';

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

function makeId(prefix = 'trip') {
  // Generate random 8 digit number
  return Math.floor(10000000 + Math.random() * 90000000).toString();
}

// ✅ Helper function for silent telemetry (optional service - fail silently)
function sendTelemetry(data) {
  // Silently ignore if telemetry service is unavailable (no console errors)
  try {
    // Use AbortController with very short timeout to fail quickly
    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), 50); // Very quick timeout (50ms)
    
    // Use fetch with signal to allow cancellation
    fetch('http://127.0.0.1:7243/ingest/40f320da-1b3b-4d52-a48b-ec2dd1dbba89', {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify(data),
      signal: controller.signal,
      mode: 'no-cors' // Prevent CORS errors from showing in console
    })
      .then(() => clearTimeout(timeoutId))
      .catch(() => {
        clearTimeout(timeoutId);
        // Silently ignore - this is an optional telemetry service
      });
  } catch (e) {
    // Silently ignore all errors - telemetry is optional
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
  
  // ✅ SECURITY: Fetch sessions from backend on mount (filtered by user_id)
  useEffect(() => {
    if (!user?.id) {
      console.warn('⚠️ No user.id found, skipping session fetch');
      return;
    }
    
    const fetchSessions = async () => {
      try {
        const headers = {
          'Content-Type': 'application/json'
        };
        // ✅ Use user.user_id (from backend) or user.id (fallback)
        const userIdToSend = user?.user_id || user?.id;
        if (userIdToSend) {
          headers['X-User-ID'] = userIdToSend;
        }
        
        console.log(`🔍 Fetching sessions for user: ${user.id} (${user.email || 'no email'})`);
        
        const res = await fetch(`${API_BASE_URL}/api/chat/sessions`, {
          headers,
          credentials: 'include',
        });
        
        if (res.ok) {
          const data = await res.json();
          const backendSessions = data.sessions || [];
          
          console.log(`✅ Fetched ${backendSessions.length} sessions from backend for user: ${user.id} (${user.email || 'no email'})`);
          
          // ✅ Convert backend sessions to trips format
          const backendTrips = backendSessions.map(session => {
            // ✅ SECURITY: Validate session user_id matches current user
            const sessionUserId = session.user_id;
            if (sessionUserId && sessionUserId !== user.id) {
              console.error(`🚨 SECURITY ALERT: Backend returned session for wrong user! session=${sessionUserId}, current=${user.id}`);
            }
            
            return {
              tripId: session.trip_id || session.chat_id,
              chatId: session.chat_id || session.session_id?.split('::')?.[1] || session.session_id,
              title: session.title || 'แชทใหม่',
              updatedAt: session.last_updated || session.created_at,
              messages: [], // Messages will be loaded separately
              userId: user.id, // ✅ Set userId from current user (not session)
              pinned: false
            };
          });
          
          // ✅ SECURITY: Validate that backend sessions belong to current user
          const validBackendTrips = backendTrips.filter(trip => {
            if (!trip.userId || trip.userId === user.id) {
              return true;
            }
            console.error(`🚨 SECURITY ALERT: Backend returned session for different user! session user=${trip.userId}, current user=${user.id}`);
            return false;
          });
          
          // ✅ Update trips state with backend data
          if (validBackendTrips.length > 0) {
            setTrips(prev => {
              // ✅ Filter existing trips by current user
              const userTrips = prev.filter(t => {
                const tripUserId = t.userId || t.user_id;
                const isMatch = !tripUserId || tripUserId === user.id;
                if (!isMatch) {
                  console.warn(`⚠️ Filtering out trip from different user: ${t.tripId || t.chatId} (user: ${tripUserId}, current: ${user.id})`);
                }
                return isMatch;
              });
              
              // ✅ Merge: backend sessions + existing user trips (avoid duplicates)
              // ✅ Prioritize backend data (backend is source of truth)
              const existingChatIds = new Set(validBackendTrips.map(t => t.chatId));
              const uniqueExistingTrips = userTrips.filter(t => {
                const chatId = t.chatId || t.tripId;
                return !existingChatIds.has(chatId);
              });
              
              // ✅ Combine: backend trips first (with messages from localStorage if available), then unique existing trips
              const mergedTrips = validBackendTrips.map(backendTrip => {
                // ✅ Try to find existing trip with same chatId to preserve messages
                const existingTrip = userTrips.find(t => {
                  const chatId = t.chatId || t.tripId;
                  return chatId === backendTrip.chatId;
                });
                
                if (existingTrip && existingTrip.messages && existingTrip.messages.length > 0) {
                  // ✅ Keep messages from localStorage (will be refreshed when chat is opened)
                  return {
                    ...backendTrip,
                    messages: existingTrip.messages, // Preserve messages temporarily
                    title: existingTrip.title || backendTrip.title, // Keep user's custom title
                    pinned: existingTrip.pinned || false
                  };
                }
                return backendTrip;
              });
              
              const finalTrips = [...mergedTrips, ...uniqueExistingTrips];
              console.log(`✅ Merged ${finalTrips.length} trips for user ${user.id} (${validBackendTrips.length} from backend, ${uniqueExistingTrips.length} from localStorage)`);
              
              // ✅ Save merged trips to localStorage
              try {
                localStorage.setItem(LS_TRIPS_KEY, JSON.stringify(finalTrips));
                console.log(`💾 Saved merged trips to localStorage`);
              } catch (e) {
                console.error('❌ Failed to save merged trips to localStorage:', e);
              }
              
              return finalTrips;
            });
          } else {
            console.log(`ℹ️ No sessions found in backend for user: ${user.id}, keeping localStorage trips`);
          }
        }
      } catch (error) {
        console.error('❌ Error fetching sessions from backend:', error);
      }
    };
    
    fetchSessions();
  }, [user?.id]); // ✅ Re-fetch when user changes

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

  // Admin check for Amadeus Viewer access
  const isAdmin = user?.is_admin || user?.email === 'admin@example.com';

  // ✅ Loading state สำหรับการโหลด chat history
  const [isLoadingHistory, setIsLoadingHistory] = useState(false);
  // ✅ Loading state สำหรับการ refresh history
  const [isRefreshingHistory, setIsRefreshingHistory] = useState(false);
  // ✅ Use ref to track refresh status without triggering re-renders
  const isRefreshingRef = useRef(false);
  // ✅ Track ว่าโหลด history แล้วหรือยัง เพื่อป้องกันการโหลดซ้ำ
  // ✅ Persist loaded trips across navigation by storing in sessionStorage
  const getInitialLoadedTrips = () => {
    try {
      const saved = sessionStorage.getItem('ai_travel_loaded_trips');
      if (saved) {
        return new Set(JSON.parse(saved));
      }
    } catch (e) {
      console.warn('Failed to restore loaded trips from sessionStorage:', e);
    }
    return new Set();
  };
  const loadedTripsRef = useRef(getInitialLoadedTrips());
  // ✅ Abort controller สำหรับยกเลิก fetch ที่เก่า
  const historyAbortControllerRef = useRef(null);
  // ✅ ป้องกัน StrictMode เรียก useEffect สองครั้ง → ยิง history fetch ซ้ำ
  const isFetchingHistoryRef = useRef(false);
  
  // ✅ Persist loaded trips to sessionStorage whenever it changes
  // Note: We can't use loadedTripsRef.current.size as dependency, so we'll save on key events
  // Instead, we'll save whenever a trip is marked as loaded (in the fetchHistory function)

  // ✅ Fetch history when activeTripId changes
  useEffect(() => {
    if (!activeTripId) {
      console.log('⚠️ No activeTripId, skipping history fetch');
      return;
    }
    
    // ✅ ยกเลิก fetch ที่เก่า (ถ้ามี)
    if (historyAbortControllerRef.current) {
      console.log('🛑 Aborting previous history fetch');
      historyAbortControllerRef.current.abort();
    }
    
    // ✅ ใช้ chatId สำหรับตรวจสอบ loaded (แต่ละ chat มี history ของตัวเอง)
    const chatId = activeChat?.chatId || activeTripId; // ✅ ใช้ chatId จาก activeChat
    
    // ✅ ถ้าโหลดไปแล้ว skip (ใช้ chatId เป็น key)
    if (loadedTripsRef.current.has(chatId)) {
      console.log(`⏭️ Already loaded history for chat: ${chatId}, skipping`);
      return;
    }
    // ✅ ป้องกัน StrictMode: ถ้ากำลัง fetch อยู่แล้ว ไม่ยิงซ้ำ
    if (isFetchingHistoryRef.current) {
      console.log(`⏭️ History fetch already in progress (StrictMode guard), skipping`);
      return;
    }
    isFetchingHistoryRef.current = true;
    
    // ✅ สร้าง abort controller ใหม่
    historyAbortControllerRef.current = new AbortController();
    
    const fetchHistory = async () => {
        try {
            setIsLoadingHistory(true);
            // ✅ ใช้ chatId สำหรับ fetch history (แต่ละ chat มี history ของตัวเอง)
            const tripId = activeChat?.tripId || activeTripId; // ✅ ใช้ tripId จาก activeChat
            console.log(`🔄 Fetching history for trip: ${tripId}, chat: ${chatId}`);
            const res = await fetch(`${API_BASE_URL}/api/chat/history/${chatId}`, {
                headers: {
                    'Content-Type': 'application/json',
                    'X-Trip-ID': tripId || activeTripId, // ✅ ส่ง trip_id ใน header เพื่อให้ backend รู้ว่าเป็น trip ไหน
                },
                credentials: 'include',
                signal: historyAbortControllerRef.current.signal, // ✅ เพื่อให้สามารถยกเลิกได้
            });
            
            if (res.ok) {
                const data = await res.json();
                console.log(`📦 Backend response:`, data);
                
                // ✅ ALWAYS process backend response, even if empty
                // ✅ CRITICAL: Restore ALL message data including planChoices, tripSummary, currentPlan, travelSlots, etc.
                const restoredMessages = (data.history && data.history.length > 0) 
                    ? data.history.map((m, idx) => {
                        // ✅ Extract all metadata fields from message
                        const messageData = {
                            ...m,
                            id: m.id || `restored_${idx}_${Date.now()}`,
                            // Ensure type is correct
                            type: m.role === 'assistant' ? 'bot' : (m.role || m.type),
                            // ✅ Restore all rich data from metadata
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
                        };
                        return messageData;
                      })
                    : null;
                
                if (restoredMessages) {
                    console.log(`✅ Fetched ${restoredMessages.length} messages from backend for chat: ${chatId}`);
                } else {
                    console.log(`ℹ️ No history found for chat: ${chatId} (keeping current messages from localStorage)`);
                }
                
                // ✅ Mark as loaded BEFORE updating state (ใช้ chatId)
                loadedTripsRef.current.add(chatId);
                // ✅ Persist to sessionStorage
                try {
                  sessionStorage.setItem('ai_travel_loaded_trips', JSON.stringify(Array.from(loadedTripsRef.current)));
                } catch (e) {
                  console.warn('Failed to save loaded trips to sessionStorage:', e);
                }
                
                // ✅ Compute latest bot message once; apply to state after setTrips (avoid setState inside setState callback)
                const latestBotMessageFromRestored = restoredMessages && restoredMessages.length > 0
                  ? restoredMessages.slice().reverse().find(m => m.type === 'bot' && (m.planChoices || m.currentPlan || m.travelSlots))
                  : null;
                
                setTrips(prev => {
                    // ✅ SECURITY: Filter trips by current user_id first
                    const currentUserId = user?.id || userId;
                    const userTrips = prev.filter(t => {
                        const tripUserId = t.userId || t.user_id;
                        return !tripUserId || tripUserId === currentUserId;
                    });
                    
                    // ✅ หา trip object จาก chatId (รองรับหลายแชทในทริปเดียวกัน)
                    const existingTripIndex = userTrips.findIndex(t => t.chatId === chatId);
                    
                    if (existingTripIndex !== -1) {
                        const newTrips = [...userTrips];
                        const currentTrip = newTrips[existingTripIndex];
                        
                        // ✅ Ensure userId is set
                        if (!currentTrip.userId && !currentTrip.user_id) {
                            currentTrip.userId = currentUserId;
                        }
                        
                        // ✅ Only update if we have backend messages
                        if (restoredMessages !== null && restoredMessages.length > 0) {
                            // ✅ Remove duplicates based on message ID or text+timestamp
                            const uniqueMessages = [];
                            const seen = new Set();
                            
                            for (const msg of restoredMessages) {
                                const key = msg.id || `${msg.type}_${msg.text}_${msg.timestamp || ''}`;
                                if (!seen.has(key)) {
                                    seen.add(key);
                                    uniqueMessages.push(msg);
                                } else {
                                    console.log(`⚠️ Skipping duplicate message: ${key.substring(0, 50)}...`);
                                }
                            }
                            
                            console.log(`📊 Unique messages: ${uniqueMessages.length}/${restoredMessages.length} for chat: ${chatId}`);
                            
                            newTrips[existingTripIndex] = {
                                ...currentTrip,
                                messages: uniqueMessages,
                                updatedAt: nowISO(),
                            };
                            
                            // ✅ Save to localStorage
                            try {
                                localStorage.setItem(LS_TRIPS_KEY, JSON.stringify(newTrips));
                                console.log(`💾 Saved ${uniqueMessages.length} messages to localStorage for chat: ${chatId}`);
                            } catch (e) {
                                console.error('❌ Failed to save to localStorage:', e);
                            }
                            return newTrips;
                        }
                    } else if (restoredMessages !== null && restoredMessages.length > 0) {
                        // ✅ SECURITY: Filter by user_id before adding new trip
                        const currentUserId = user?.id || userId;
                        const userTrips = prev.filter(t => {
                            const tripUserId = t.userId || t.user_id;
                            return !tripUserId || tripUserId === currentUserId;
                        });
                        
                        // Create new chat with backend history (ใช้ chatId และ tripId)
                        const newTrip = {
                            tripId: tripId, // ✅ ใช้ tripId จาก activeChat
                            chatId: chatId, // ✅ ใช้ chatId
                            title: 'ทริปที่กู้คืนมา',
                            createdAt: nowISO(),
                            updatedAt: nowISO(),
                            messages: restoredMessages,
                            pinned: false,
                            userId: currentUserId // ✅ Set userId
                        };
                        const newTrips = [newTrip, ...userTrips];
                        
                        try {
                            localStorage.setItem(LS_TRIPS_KEY, JSON.stringify(newTrips));
                            console.log(`💾 Created and saved new chat with ${restoredMessages.length} messages: chat=${chatId}, trip=${tripId}`);
                        } catch (e) {
                            console.error('❌ Failed to save to localStorage:', e);
                        }
                        return newTrips;
                    }
                    return prev;
                });
                
                // ✅ Apply restored plan/slots state after setTrips (not inside callback)
                if (latestBotMessageFromRestored) {
                  if (latestBotMessageFromRestored.planChoices?.length) {
                    setLatestPlanChoices(latestBotMessageFromRestored.planChoices);
                  }
                  if (latestBotMessageFromRestored.currentPlan) setSelectedPlan(latestBotMessageFromRestored.currentPlan);
                  if (latestBotMessageFromRestored.travelSlots) setSelectedTravelSlots(latestBotMessageFromRestored.travelSlots);
                  setLatestBotMessage(latestBotMessageFromRestored);
                }
            } else {
                console.error(`❌ Failed to fetch history: ${res.status} ${res.statusText}`);
            }
        } catch (err) {
            // ✅ ถ้า abort ไม่ต้อง log error
            if (err.name === 'AbortError') {
                console.log('⚠️ History fetch aborted (switching trip)');
            } else {
                console.error("❌ Failed to fetch chat history:", err);
            }
        } finally {
            setIsLoadingHistory(false);
            isFetchingHistoryRef.current = false; // ✅ Allow next fetch (e.g. after StrictMode remount)
            console.log(`🏁 Finished loading history for trip: ${activeTripId}`);
        }
    };
    
    fetchHistory();
    
    // ✅ Cleanup: ยกเลิก fetch เมื่อ component unmount หรือ activeTripId/activeChat เปลี่ยน
    return () => {
      if (historyAbortControllerRef.current) {
        historyAbortControllerRef.current.abort();
      }
    };
  }, [activeTripId, activeChat?.chatId]);

  const [inputText, setInputText] = useState('');
  const [processingTripId, setProcessingTripId] = useState(null);
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
  const [isConnected, setIsConnected] = useState(null); // null = unknown, true = connected, false = disconnected
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
  // ✅ Chat Mode: 'normal' = ผู้ใช้เลือกช้อยส์เอง, 'agent' = AI ดำเนินการเอง
  const [chatMode, setChatMode] = useState(() => {
    try {
      const saved = localStorage.getItem('chat_mode');
      return saved === 'agent' ? 'agent' : 'normal';
    } catch (_) {
      return 'normal';
    }
  });
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
  }, [activeTrip?.messages, activeTripId]);

  // ===== Persist trips + activeTripId =====
  useEffect(() => {
    try {
      // ✅ SECURITY: Only persist trips that belong to current user
      const currentUserId = user?.id || userId;
      const userTrips = trips.map(trip => ({
        ...trip,
        userId: currentUserId // ✅ Ensure userId is set
      }));
      localStorage.setItem(LS_TRIPS_KEY, JSON.stringify(userTrips));
    } catch (_) {}
  }, [trips, user?.id, userId]);

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
  const checkApiConnection = React.useCallback(async () => {
    console.log('🔍 Checking API connection...', API_BASE_URL);
    // Create abort controller for timeout
    // Increased timeout to 8 seconds to account for slow MongoDB/Redis checks
    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), 8000); // 8 second timeout
    
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
        console.warn(`❌ Health check failed: HTTP ${response.status}`);
        // Try fallback: check if root endpoint works
        const fallbackController = new AbortController();
        const fallbackTimeoutId = setTimeout(() => fallbackController.abort(), 3000);
        try {
          const fallbackResponse = await fetch(`${API_BASE_URL}/`, { 
            cache: 'no-cache',
            signal: fallbackController.signal
          });
          clearTimeout(fallbackTimeoutId);
          if (fallbackResponse.ok) {
            console.log('✅ Fallback check: Backend is reachable');
            setIsConnected(true);
            return;
          }
        } catch (fallbackError) {
          clearTimeout(fallbackTimeoutId);
          console.error('❌ Fallback check also failed:', fallbackError);
        }
        setIsConnected(false);
        return;
      }
      
      const data = await response.json();
      console.log('✅ Health check response:', data);
      
      // Backend returns 'healthy' or 'degraded', but 'ok' is also possible from older versions
      // Also accept any status that indicates the server is running (not 'unhealthy')
      // 'degraded' means some services are slow but server is still operational
      const isHealthy = data.status === 'healthy' || 
                       data.status === 'ok' || 
                       data.status === 'degraded' ||
                       (data.status && data.status !== 'unhealthy');
      
      console.log(`📊 Connection status: ${isHealthy ? '✅ CONNECTED' : '❌ DISCONNECTED'} (status: ${data.status})`);
      setIsConnected(isHealthy);
      
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
        console.warn('⏱️ Health check timed out (8s), backend may be slow but assuming reachable');
        // Don't set to false immediately, might just be slow
        // Health check endpoint may be checking MongoDB/Redis which can be slow
        return;
      }
      console.error('❌ API connection error:', error);
      // Only set to false if it's a real network error (not timeout)
      if (error.message && !error.message.includes('timeout') && !error.message.includes('aborted')) {
        console.error('❌ Setting connection status to DISCONNECTED');
        setIsConnected(false);
      }
    }
  }, [API_BASE_URL]);
  
  useEffect(() => {
    console.log('🚀 Initializing health check...');
    // Check immediately on mount
    checkApiConnection();
    // ตั้งเวลาตรวจสอบการเชื่อมต่อทุก 10 วินาที เพื่อ Reconnect อัตโนมัติ
    const interval = setInterval(() => {
      console.log('🔄 Periodic health check...');
      checkApiConnection();
    }, 10000);
    return () => {
      console.log('🛑 Cleaning up health check interval');
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

  // ===== Trips update helpers =====
  const appendMessageToTrip = (tripId, msg) => {
    if (!tripId || !msg) {
      console.warn('⚠️ appendMessageToTrip: tripId or msg is missing', { tripId, msg });
      return;
    }
    setTrips(prev => {
      // ✅ SECURITY: Filter by user_id and update
      const currentUserId = user?.id || userId;
      return prev.map(t => {
        const tripUserId = t.userId || t.user_id;
        if (tripUserId && tripUserId !== currentUserId) return t;
        // ✅ Match by tripId or chatId (activeTripId may be either)
        if (t.tripId !== tripId && t.chatId !== tripId) return t;
        const currentMessages = Array.isArray(t.messages) ? t.messages : [];
        // ✅ แก้บั๊กแชทซ้อน: ถ้า msg เป็น bot และข้อความล่าสุดก็เป็น bot ที่มี planChoices/slotChoices เหมือนกัน → แทนที่ข้อความล่าสุดแทนการเพิ่ม
        if (msg.type === 'bot' && currentMessages.length > 0) {
          const last = currentMessages[currentMessages.length - 1];
          if (last.type === 'bot') {
            const lastChoicesLen = (Array.isArray(last.planChoices) ? last.planChoices.length : 0) + (Array.isArray(last.slotChoices) ? last.slotChoices.length : 0);
            const msgChoicesLen = (Array.isArray(msg.planChoices) ? msg.planChoices.length : 0) + (Array.isArray(msg.slotChoices) ? msg.slotChoices.length : 0);
            const sameText = (last.text || '') === (msg.text || '');
            const sameChoicesCount = lastChoicesLen > 0 && lastChoicesLen === msgChoicesLen;
            if (sameText && sameChoicesCount) {
              const nextMessages = [...currentMessages.slice(0, -1), msg];
              return { ...t, messages: nextMessages, updatedAt: nowISO() };
            }
          }
        }
        const nextMessages = [...currentMessages, msg];
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

  // ===== Force refresh history =====
  const handleRefreshHistory = async () => {
    // ✅ Use ref to check status without triggering re-render
    if (isRefreshingRef.current) {
      console.log('⏳ Refresh already in progress, skipping...');
      return;
    }
    
    console.log(`🔄 Force refreshing sessions and history from backend...`);
    isRefreshingRef.current = true;
    setIsRefreshingHistory(true);
    
    try {
      // ✅ Clear all loaded trips cache to force reload
      loadedTripsRef.current.clear();
      sessionStorage.removeItem('ai_travel_loaded_trips');
      console.log('🗑️ Cleared loaded trips cache');
      
      // ✅ SECURITY: Fetch sessions from backend (filtered by user_id)
      const headers = {
        'Content-Type': 'application/json'
      };
      if (user?.id) {
        headers['X-User-ID'] = user.id;
      }
      
      const res = await fetch(`${API_BASE_URL}/api/chat/sessions`, {
        headers,
        credentials: 'include',
      });
      
      if (res.ok) {
        const data = await res.json();
        const backendSessions = data.sessions || [];
        
        console.log(`✅ Fetched ${backendSessions.length} sessions from backend`);
        
        // ✅ Convert backend sessions to trips format
        const currentUserId = user?.id || userId;
        const backendTrips = backendSessions.map(session => ({
          tripId: session.trip_id || session.chat_id,
          chatId: session.chat_id || session.session_id?.split('::')?.[1] || session.session_id,
          title: session.title || 'แชทใหม่',
          updatedAt: session.last_updated || session.created_at,
          messages: [], // Messages will be loaded separately when chat is opened
          userId: currentUserId, // ✅ Set userId
          pinned: false
        }));
        
        // ✅ Replace trips with backend data (backend is source of truth)
        setTrips(prev => {
          // ✅ Filter existing trips by current user
          const userTrips = prev.filter(t => {
            const tripUserId = t.userId || t.user_id;
            return !tripUserId || tripUserId === currentUserId;
          });
          
          // ✅ Merge: backend sessions + existing user trips (avoid duplicates)
          // ✅ Prioritize backend data but keep messages from localStorage temporarily
          const existingChatIds = new Set(backendTrips.map(t => t.chatId));
          const uniqueExistingTrips = userTrips.filter(t => {
            const chatId = t.chatId || t.tripId;
            return !existingChatIds.has(chatId);
          });
          
          // ✅ Merge backend trips with existing trips (preserve messages temporarily)
          const mergedTrips = backendTrips.map(backendTrip => {
            // ✅ Try to find existing trip with same chatId to preserve messages temporarily
            const existingTrip = userTrips.find(t => {
              const chatId = t.chatId || t.tripId;
              return chatId === backendTrip.chatId;
            });
            
            if (existingTrip && existingTrip.messages && existingTrip.messages.length > 0) {
              // ✅ Keep messages temporarily (will be refreshed when chat is opened)
              return {
                ...backendTrip,
                messages: existingTrip.messages,
                title: existingTrip.title || backendTrip.title,
                pinned: existingTrip.pinned || false
              };
            }
            return backendTrip;
          });
          
          const finalTrips = [...mergedTrips, ...uniqueExistingTrips];
          console.log(`✅ Merged ${finalTrips.length} trips (${backendTrips.length} from backend, ${uniqueExistingTrips.length} from localStorage)`);
          
          // ✅ Save to localStorage
          try {
            localStorage.setItem(LS_TRIPS_KEY, JSON.stringify(finalTrips));
            console.log(`💾 Saved refreshed trips to localStorage`);
          } catch (e) {
            console.error('❌ Failed to save trips to localStorage:', e);
          }
          
          return finalTrips;
        });
        
        // ✅ Force reload current chat history if active
        if (activeTripId) {
          const chatId = activeChat?.chatId || activeTripId;
          if (chatId) {
            console.log(`🔄 Force reloading history for active chat: ${chatId}`);
            // Clear from loaded cache
            loadedTripsRef.current.delete(chatId);
            
            // ✅ Also clear from sessionStorage
            try {
              const saved = sessionStorage.getItem('ai_travel_loaded_trips');
              if (saved) {
                const loadedSet = new Set(JSON.parse(saved));
                loadedSet.delete(chatId);
                sessionStorage.setItem('ai_travel_loaded_trips', JSON.stringify(Array.from(loadedSet)));
              }
            } catch (e) {
              console.warn('Failed to update sessionStorage:', e);
            }
            
            // ✅ Force reload by fetching history directly
            const tripId = activeChat?.tripId || activeTripId;
            const fetchHistoryDirectly = async () => {
              try {
                setIsLoadingHistory(true);
                console.log(`🔄 Directly fetching history for chat: ${chatId}, trip: ${tripId}`);
                
                const historyRes = await fetch(`${API_BASE_URL}/api/chat/history/${chatId}`, {
                  headers: {
                    'Content-Type': 'application/json',
                    'X-Trip-ID': tripId || activeTripId,
                  },
                  credentials: 'include',
                });
                
                if (historyRes.ok) {
                  const historyData = await historyRes.json();
                  // ✅ CRITICAL: Restore ALL message data including planChoices, tripSummary, currentPlan, travelSlots, etc.
                  const restoredMessages = (historyData.history && historyData.history.length > 0) 
                    ? historyData.history.map((m, idx) => {
                        // ✅ Extract all metadata fields from message
                        const messageData = {
                          ...m,
                          id: m.id || `restored_${idx}_${Date.now()}`,
                          type: m.role === 'assistant' ? 'bot' : (m.role || m.type),
                          // ✅ Restore all rich data from metadata
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
                        };
                        return messageData;
                      })
                    : [];
                  
                  if (restoredMessages.length > 0) {
                    console.log(`✅ Fetched ${restoredMessages.length} messages for chat: ${chatId}`);
                    
                    // ✅ Update trips with new messages
                    setTrips(prev => {
                      const currentUserId = user?.id || userId;
                      const userTrips = prev.filter(t => {
                        const tripUserId = t.userId || t.user_id;
                        return !tripUserId || tripUserId === currentUserId;
                      });
                      
                      const tripIndex = userTrips.findIndex(t => t.chatId === chatId);
                      if (tripIndex !== -1) {
                        const newTrips = [...userTrips];
                        newTrips[tripIndex] = {
                          ...newTrips[tripIndex],
                          messages: restoredMessages,
                          updatedAt: nowISO(),
                        };
                        
                        // ✅ Save to localStorage
                        try {
                          localStorage.setItem(LS_TRIPS_KEY, JSON.stringify(newTrips));
                          console.log(`💾 Saved refreshed messages to localStorage`);
                        } catch (e) {
                          console.error('❌ Failed to save to localStorage:', e);
                        }
                        
                        return newTrips;
                      }
                      return prev;
                    });
                    
                    // ✅ Mark as loaded
                    loadedTripsRef.current.add(chatId);
                    try {
                      sessionStorage.setItem('ai_travel_loaded_trips', JSON.stringify(Array.from(loadedTripsRef.current)));
                    } catch (e) {
                      console.warn('Failed to save loaded trips to sessionStorage:', e);
                    }
                  } else {
                    console.log(`ℹ️ No history found for chat: ${chatId}`);
                  }
                } else {
                  console.warn(`⚠️ Failed to fetch history: ${historyRes.status}`);
                }
              } catch (error) {
                console.error('❌ Error fetching history directly:', error);
              } finally {
                setIsLoadingHistory(false);
              }
            };
            
            // ✅ Fetch history directly
            fetchHistoryDirectly();
          }
        }
        
        console.log('✅ Refresh completed');
      } else {
        console.warn('⚠️ Failed to fetch sessions from backend:', res.status);
      }
    } catch (error) {
      console.error('❌ Error refreshing sessions:', error);
    } finally {
      isRefreshingRef.current = false;
      setIsRefreshingHistory(false);
    }
  };

  // ===== Auto-sync conversations =====
  // ✅ Auto-refresh conversations every 30 seconds + on page visibility change
  useEffect(() => {
    if (!user?.id) {
      return; // Don't sync if user is not logged in
    }

    // ✅ Initial sync on mount (immediate sync after page load/refresh)
    const initialSync = setTimeout(() => {
      if (!isRefreshingRef.current) {
        console.log('🔄 Initial sync after page load/refresh...');
        handleRefreshHistory();
      }
    }, 500); // Wait 500ms after mount to avoid conflicts

    // ✅ Set up interval for auto-sync (every 30 seconds)
    const syncInterval = setInterval(() => {
      if (!isRefreshingRef.current) {
        console.log('🔄 Auto-syncing conversations...');
        handleRefreshHistory();
      } else {
        console.log('⏳ Sync already in progress, skipping auto-sync');
      }
    }, 30000); // 30 seconds

    // ✅ Sync when page becomes visible (user returns to tab/window)
    const handleVisibilityChange = () => {
      if (document.visibilityState === 'visible' && !isRefreshingRef.current) {
        console.log('🔄 Page became visible, syncing conversations...');
        handleRefreshHistory();
      }
    };

    // ✅ Sync when page is about to reload (beforeunload)
    const handleBeforeUnload = () => {
      // Save current state before reload
      if (activeTripId) {
        try {
          sessionStorage.setItem('ai_travel_last_active_trip', activeTripId);
        } catch (e) {
          console.warn('Failed to save active trip before reload:', e);
        }
      }
    };

    document.addEventListener('visibilitychange', handleVisibilityChange);
    window.addEventListener('beforeunload', handleBeforeUnload);

    return () => {
      clearTimeout(initialSync);
      clearInterval(syncInterval);
      document.removeEventListener('visibilitychange', handleVisibilityChange);
      window.removeEventListener('beforeunload', handleBeforeUnload);
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [user?.id]); // Re-run only when user changes (not when refresh state changes)

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
      
      setTrips(prev => {
        // ✅ SECURITY: Filter out trips from other users before adding new trip
        const userTrips = prev.filter(t => {
          const tripUserId = t.userId || t.user_id;
          return !tripUserId || tripUserId === currentUserId;
        });
        const newTrips = [nt, ...userTrips];
        // ✅ Save to localStorage
        try {
          localStorage.setItem(LS_TRIPS_KEY, JSON.stringify(newTrips));
          console.log('💾 Saved new trip to localStorage');
        } catch (lsError) {
          console.error('❌ localStorage save failed:', lsError);
        }
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
      // ✅ SECURITY: Filter by user_id before deleting
      const currentUserId = user?.id || userId;
      const userTrips = prev.filter(t => {
        const tripUserId = t.userId || t.user_id;
        return (!tripUserId || tripUserId === currentUserId) && t.tripId !== tripId;
      });
      const next = userTrips;
      // ✅ Create new trip with userId if empty
      if (next.length === 0) {
        const displayName = user?.first_name || user?.name || "คุณ";
        const newTrip = createNewTrip('ทริปใหม่', displayName);
        newTrip.userId = currentUserId;
        return [newTrip];
      }
      return next;
    });

    // ✅ SECURITY: Filter by user_id before deleting
    const currentUserId = user?.id || userId;
    const userTrips = trips.filter(t => {
      const tripUserId = t.userId || t.user_id;
      return !tripUserId || tripUserId === currentUserId;
    });
    
    // ✅ ตรวจสอบทั้ง tripId และ chatId (รองรับทั้งสองกรณี)
    const isActiveTrip = userTrips.some(t => (t.tripId === tripId && activeTripId === t.tripId) || (t.chatId === activeTripId));
    if (isActiveTrip) {
      const remaining = userTrips.filter(t => t.tripId !== tripId && t.chatId !== activeTripId);
      // ✅ ใช้ chatId แทน tripId เพื่อให้แชทแยกกันถูกต้อง
      setActiveTripId(remaining[0]?.chatId || remaining[0]?.tripId || null);
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
  }, [trips]);

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
      alert('Backend is not connected. Please start the backend server first.');
      return;
    }
    
    // If status is unknown (null), try to send anyway - let the actual request fail gracefully

    const tripId = activeTrip?.tripId;
    if (!tripId) {
      sendInProgressRef.current = false;
      return;
    }

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
    setProcessingTripId(tripId);
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
              
              // ✅ Telemetry service (optional - fail silently)
              sendTelemetry({
                location: 'AITravelChat.jsx:1043',
                message: 'Received SSE data',
                data: {status: data.status, has_data: !!data.data},
                timestamp: Date.now(),
                sessionId: 'debug-session',
                runId: 'run1',
                hypothesisId: 'A'
              });
              
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
              
              // ✅ อัปเดตสถานะการทำงานแบบ realtime
              if (data.status && data.message) {
                setAgentStatus({
                  status: data.status,
                  message: data.message,
                  step: data.step
                });
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
                if (typeof finalData?.response === 'string' && finalData.response.trim()) {
                  responseText = finalData.response.trim();
                } else if (finalData?.message && typeof finalData.message === 'string') {
                  responseText = finalData.message.trim();
                } else if (finalData?.text && typeof finalData.text === 'string') {
                  responseText = finalData.text.trim();
                } else if (finalData?.response) {
                  responseText = String(finalData.response).trim();
                }
                
                // ✅ If still empty, use default message
                if (!responseText) {
                  responseText = 'ได้รับข้อมูลตอบกลับแล้ว แต่ไม่มีข้อความ กรุณาลองใหม่อีกครั้ง';
                  console.warn('⚠️ No response text found in finalData:', finalData);
                }

                // ✅ Safe null checks for all fields
                const botMessage = {
                  id: Date.now() + 1,
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

                appendMessageToTrip(tripId, botMessage);
                
                // ✅ Store latest bot message for agentState access
                setLatestBotMessage(botMessage);

                // ✅ ตรวจสอบว่า Agent Mode auto-book สำเร็จหรือไม่
                const responseTextLower = botMessage.text?.toLowerCase() || '';
                const isAgentModeBooking = (
                  chatMode === 'agent' && 
                  (responseTextLower.includes('จองสำเร็จ') || 
                   responseTextLower.includes('จองเสร็จ') ||
                   responseTextLower.includes('สร้างการจองสำเร็จ') ||
                   responseTextLower.includes('auto-booked') ||
                   responseTextLower.includes('my bookings'))
                );
                
                if (isAgentModeBooking) {
                  // แสดง notification แจ้งเตือนให้ไปชำระเงิน
                  Swal.fire({
                    icon: 'info',
                    title: '💳 ต้องชำระเงิน',
                    html: `
                      <div style="text-align: left;">
                        <p style="margin-bottom: 12px;">✅ Agent Mode สร้างการจองสำเร็จแล้ว!</p>
                        <p style="margin-bottom: 12px; color: #dc2626; font-weight: 600;">
                          ⚠️ กรุณาชำระเงินเพื่อยืนยันการจองกับ Amadeus
                        </p>
                        <p style="margin-bottom: 0; color: #6b7280; font-size: 14px;">
                          📋 ดูรายการจองได้ที่ "My Bookings"
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
                  setSelectedTravelSlots(finalData?.travel_slots || null);
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
        // ✅ Connection error - set disconnected and offer retry
        setIsConnected(false);
        
        const errorMessage = {
          id: Date.now() + 1,
          type: 'bot',
          text: `❌ เกิดข้อผิดพลาดในการเชื่อมต่อ\n\n${error.message}\n\nโปรดตรวจสอบ:\n1. Backend กำลังทำงานอยู่\n2. API Keys ถูกต้อง\n3. การเชื่อมต่ออินเทอร์เน็ต`,
          error: true,
          retryAvailable: true,
          onRetry: () => {
            setShouldRetry(true);
            setConnectionRetryCount(prev => prev + 1);
            // Retry sending the message
            setTimeout(() => {
              sendMessage(trimmed);
            }, 1000 * Math.min(connectionRetryCount + 1, 5)); // Exponential backoff, max 5 seconds
          }
        };

        appendMessageToTrip(tripId, errorMessage);
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
    if (!tripId) return;
    const trimmed = String(userText || '').trim();
    if (!trimmed) return;

    const now = Date.now();
    const lastAt = lastRefreshAtRef.current[messageId] || 0;
    if (now - lastAt < REFRESH_COOLDOWN_MS) return;
    lastRefreshAtRef.current[messageId] = now;

    setProcessingTripId(tripId);
    
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
                  cachedOptions: finalData.cached_options || null,
                  cacheValidation: finalData.cache_validation || null,
                  workflowValidation: finalData.workflow_validation || null,
      };

      appendMessageToTrip(tripId, botMessage);

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
                    console.log('✅ Agent Mode: Auto-set selectedPlan from current_plan');
                  } else {
                    // Normal Mode: แสดง plan แม้ workflow ยังไม่เสร็จ (เพื่อให้เห็น progress)
                    setSelectedPlan(finalData.current_plan);
                    setSelectedTravelSlots(finalData.travel_slots || null);
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
        
        const formattedPrice = new Intl.NumberFormat('th-TH', {
          style: 'currency',
          currency: currency,
          minimumFractionDigits: 0,
        }).format(totalPrice);
        
        // ✅ สร้างข้อความที่บอก AI ว่าเรามาแก้ไขทริป พร้อมข้อมูล booking
        const editMessage = `ฉันต้องการแก้ไขทริปที่จองไว้\n\n📋 ข้อมูลการจองปัจจุบัน:\n- เส้นทาง: ${route}\n${departureDate ? `- วันเดินทาง: ${departureDate}` : ''}${returnDate ? `\n- วันกลับ: ${returnDate}` : ''}\n- ราคารวม: ${formattedPrice}\n- Booking ID: ${editContext.bookingId}\n\nกรุณาช่วยฉันแก้ไขทริปนี้ด้วยค่ะ`;
        
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
  // ✅ โหมดสนทนาด้วยเสียงแบบ Real-Time: ใช้ Gemini Live API สำหรับการสนทนาที่เป็นธรรมชาติเหมือนมนุษย์
  const handleVoiceInput = () => {
    if (!isVoiceMode) {
      // เริ่มโหมดสนทนาด้วยเสียงแบบ Real-Time
      startLiveVoiceMode();
    } else {
      // หยุดโหมดสนทนาด้วยเสียง
      stopLiveVoiceMode();
    }
  };

  // ✅ เริ่มโหมด Live Voice Conversation (ใช้ Gemini Live API)
  const startLiveVoiceMode = async () => {
    try {
      // ตรวจสอบว่าเบราว์เซอร์รองรับ MediaRecorder และ WebSocket
      if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
        alert('เบราว์เซอร์ของคุณไม่รองรับการบันทึกเสียง กรุณาใช้ Chrome หรือ Edge');
        return;
      }

      setIsVoiceMode(true);
      setIsRecording(true);
      isVoiceModeRef.current = true;

      // ✅ สร้าง AudioContext สำหรับ real-time audio processing
      const AudioContext = window.AudioContext || window.webkitAudioContext;
      audioContextRef.current = new AudioContext({ sampleRate: 16000 });

      // ✅ ขออนุญาตใช้ไมโครโฟน
      const stream = await navigator.mediaDevices.getUserMedia({
        audio: {
          channelCount: 1, // Mono
          sampleRate: 16000, // 16kHz for Gemini Live API
          echoCancellation: true,
          noiseSuppression: true,
          autoGainControl: true
        }
      });

      // ✅ สร้าง MediaRecorder สำหรับ capture audio
      const options = {
        mimeType: 'audio/webm;codecs=opus',
        audioBitsPerSecond: 16000
      };
      
      let mediaRecorder;
      try {
        mediaRecorder = new MediaRecorder(stream, options);
      } catch (e) {
        // Fallback to default
        mediaRecorder = new MediaRecorder(stream);
      }
      
      mediaRecorderRef.current = mediaRecorder;

      // ✅ เชื่อมต่อ WebSocket กับ Live Audio API
      const wsProtocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
      // Extract host and port from API_BASE_URL
      const apiUrl = new URL(API_BASE_URL);
      const wsUrl = `${wsProtocol}//${apiUrl.host}/api/chat/live-audio?user_id=${encodeURIComponent(userId || 'anonymous')}&chat_id=${encodeURIComponent(activeTripId || 'default')}`;
      
      const ws = new WebSocket(wsUrl);
      liveAudioWebSocketRef.current = ws;

      ws.onopen = () => {
        console.log('✅ Live Audio WebSocket connected');
        setIsRecording(true);
        
        // เริ่มบันทึกเสียง
        mediaRecorder.start(100); // Send chunks every 100ms
        
        // ส่ง audio chunks ไปยัง WebSocket
        mediaRecorder.ondataavailable = async (event) => {
          if (event.data.size > 0 && ws.readyState === WebSocket.OPEN) {
            try {
              // Convert WebM to PCM (simplified - in production, use proper audio processing)
              const arrayBuffer = await event.data.arrayBuffer();
              
              // Send as base64 encoded audio
              const base64Audio = btoa(String.fromCharCode(...new Uint8Array(arrayBuffer)));
              ws.send(JSON.stringify({
                type: 'audio',
                data: base64Audio,
                format: 'webm'
              }));
            } catch (e) {
              console.error('Error sending audio chunk:', e);
            }
          }
        };
      };

      ws.onmessage = async (event) => {
        try {
          const message = JSON.parse(event.data);
          
          if (message.type === 'connected') {
            console.log('✅ Live Audio session connected:', message.message);
          } else if (message.type === 'audio') {
            // ✅ รับ audio จาก Gemini Live API และเล่น
            try {
              const audioData = atob(message.data);
              const audioArray = new Uint8Array(audioData.length);
              for (let i = 0; i < audioData.length; i++) {
                audioArray[i] = audioData.charCodeAt(i);
              }
              
              // ✅ Gemini Live API ส่ง PCM audio (16-bit, 24kHz, little-endian, mono)
              // Convert PCM bytes to AudioBuffer
              const sampleRate = 24000; // Gemini Live API output sample rate
              const numChannels = 1; // Mono
              const length = audioArray.length / 2; // 16-bit = 2 bytes per sample
              
              const audioBuffer = audioContextRef.current.createBuffer(numChannels, length, sampleRate);
              const channelData = audioBuffer.getChannelData(0);
              
              // Convert 16-bit PCM to float32 (-1.0 to 1.0)
              for (let i = 0; i < length; i++) {
                const sample = (audioArray[i * 2] | (audioArray[i * 2 + 1] << 8));
                // Handle signed 16-bit
                const signedSample = sample > 32767 ? sample - 65536 : sample;
                channelData[i] = signedSample / 32768.0;
              }
              
              // Play audio
              const source = audioContextRef.current.createBufferSource();
              source.buffer = audioBuffer;
              source.connect(audioContextRef.current.destination);
              source.start();
              
              // Update UI
              setIsRecording(false); // Agent กำลังพูด
              
              // Resume listening after audio ends
              source.onended = () => {
                if (isVoiceModeRef.current && mediaRecorderRef.current && mediaRecorderRef.current.state === 'inactive') {
                  setIsRecording(true);
                  try {
                    mediaRecorderRef.current.start(100);
                  } catch (e) {
                    console.log('MediaRecorder already running');
                  }
                }
              };
            } catch (e) {
              console.error('Error playing audio:', e);
            }
            
          } else if (message.type === 'text') {
            // ✅ รับ text transcript จาก Gemini
            console.log('Agent said:', message.data);
            // สามารถแสดง text ใน UI ได้ถ้าต้องการ
            
          } else if (message.type === 'error') {
            console.error('Live Audio error:', message.message);
            alert(`เกิดข้อผิดพลาด: ${message.message}`);
            stopLiveVoiceMode();
          }
        } catch (e) {
          console.error('Error processing WebSocket message:', e);
        }
      };

      ws.onerror = (error) => {
        console.error('WebSocket error:', error);
        alert('เกิดข้อผิดพลาดในการเชื่อมต่อ กรุณาลองใหม่อีกครั้ง');
        stopLiveVoiceMode();
      };

      ws.onclose = () => {
        console.log('Live Audio WebSocket closed');
        stopLiveVoiceMode();
      };

    } catch (error) {
      console.error('Error starting live voice mode:', error);
      alert(`ไม่สามารถเริ่มโหมดเสียงได้: ${error.message}`);
      stopLiveVoiceMode();
    }
  };

  // ✅ หยุดโหมด Live Voice Conversation
  const stopLiveVoiceMode = () => {
    isVoiceModeRef.current = false;
    if (isMountedRef.current) {
      setIsVoiceMode(false);
      setIsRecording(false);
    }
    
    // ✅ ปิด MediaRecorder
    if (mediaRecorderRef.current && mediaRecorderRef.current.state !== 'inactive') {
      try {
        mediaRecorderRef.current.stop();
        mediaRecorderRef.current.stream.getTracks().forEach(track => track.stop());
      } catch (e) {
        console.error('Error stopping MediaRecorder:', e);
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
    // Only show alert if we're sure backend is disconnected (false), not if unknown (null)
    if (isConnected === false) {
      alert('Backend is not connected. Please start the backend server first.');
      return;
    }
    
    // If status is unknown (null), try to send anyway - let the actual request fail gracefully

    const tripId = activeTrip?.tripId;
    if (!tripId) return;

    // ✅ เพิ่มข้อความฝั่งผู้ใช้ว่าเลือก slot X
    const slotName = slotType === 'flight' ? 'เที่ยวบิน' : slotType === 'hotel' ? 'ที่พัก' : slotType === 'car' ? 'รถ' : 'การเดินทาง';
    const userMessage = {
      id: Date.now(),
      type: 'user',
      text: `เลือกช้อยส์ ${choiceId}` // ใช้คำว่า "เลือกช้อยส์" แทน "เลือก..."
    };
    appendMessageToTrip(tripId, userMessage);

    setProcessingTripId(tripId);
    
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
    if (!tripId) return;

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
    appendMessageToTrip(tripId, userMessage);

    setProcessingTripId(tripId);

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
          // Normal Mode: แสดง plan แม้ workflow ยังไม่เสร็จ (เพื่อให้เห็น progress)
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

  const handleConfirmBooking = async () => {
    const tripId = activeTrip?.tripId;
    const chatId = activeTrip?.chatId || tripId;
    if (!tripId) return;

    // ✅ ตรวจสอบว่ามี plan และ travel_slots หรือไม่
    if (!selectedPlan) {
      alert('⚠️ ยังไม่มีข้อมูลทริป กรุณารอให้ Agent สร้างแผนการเดินทางให้เสร็จก่อน');
      return;
    }

    setIsBooking(true);
    setBookingResult(null);
    setProcessingTripId(tripId);
    
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
        children: travelSlots.children || 0,
        infants: travelSlots.infants || 0,
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
      const res = await fetch(`${API_BASE_URL}/api/booking/create`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
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
      
      // ✅ อัปเดต notification count หลังจากสร้าง booking สำเร็จ
      if (onRefreshNotifications) {
        onRefreshNotifications();
      }
      
      // ✅ Trigger event to refresh MyBookingsPage if it's open
      window.dispatchEvent(new Event('bookingCreated'));
      // ✅ Also use localStorage event for cross-tab communication
      localStorage.setItem('booking_created', Date.now().toString());
      localStorage.removeItem('booking_created'); // Clear immediately
      
      // ✅ Navigate to My Bookings to show the new booking
      if (onNavigateToBookings) {
        // Small delay to ensure booking is saved
        setTimeout(() => {
          onNavigateToBookings();
        }, 500);
      }
      
      // ✅ ไม่แสดง popup แล้ว - ให้ LLM บอกในแชทแทน
      // Notification จะแสดงใน My Bookings แทน
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
      'heartbeat': '💓 กำลังประมวลผล...',
    };
    return toolMap[step] || null;
  };

  // ===== UI =====
  return (
    <ChatErrorBoundary>
    <div className="chat-container">
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
              <button 
                className="trip-new-btn" 
                onClick={handleNewTrip}
                title={isSidebarOpen ? "สร้างทริปใหม่" : "ทริปใหม่"}
              >
                {isSidebarOpen ? '+ ทริปใหม่' : '+'}
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
                  // ✅ ตรวจสอบว่าเป็น active chat (ใช้ chatId)
                  const isActive = (t.chatId || t.tripId) === (activeChat?.chatId || activeChat?.tripId || activeTripId);
                  const isEditing = editingTripId === t.tripId;
                  const isProcessing = processingTripId === t.tripId;
                  return (
                    <div
                      key={`${t.tripId}_${t.chatId}`} // ✅ ใช้ทั้ง tripId และ chatId เป็น key (รองรับหลายแชทในทริปเดียวกัน)
                      className={`trip-item ${isActive ? 'trip-item-active' : ''} ${t.pinned ? 'trip-item-pinned' : ''}`}
                      onClick={() => {
                        console.log('👆 Clicked trip:', t.chatId || t.tripId);
                        if (!isEditing) {
                          setActiveTripId(t.chatId || t.tripId);
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
              </div>
            </div>
            
            <div className="chatbox-header-right">
              {/* ✅ Chat Mode Toggle - Desktop: Buttons, Mobile: Dropdown */}
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
                {/* Desktop: Show both buttons */}
                <div className="chat-mode-toggle-desktop">
                  <button
                    onClick={() => {
                      setChatMode('normal');
                      localStorage.setItem('chat_mode', 'normal');
                    }}
                    style={{
                      padding: '6px 12px',
                      borderRadius: '6px',
                      border: 'none',
                      background: chatMode === 'normal' ? 'rgba(59, 130, 246, 0.3)' : 'transparent',
                      color: chatMode === 'normal' ? '#fff' : 'rgba(255, 255, 255, 0.7)',
                      cursor: 'pointer',
                      fontWeight: chatMode === 'normal' ? '600' : '400',
                      transition: 'all 0.2s'
                    }}
                    title="โหมดปกติ - คุณเลือกช้อยส์เอง"
                  >
                    📋 Normal
                  </button>
                  <button
                    onClick={() => {
                      setChatMode('agent');
                      localStorage.setItem('chat_mode', 'agent');
                    }}
                    style={{
                      padding: '6px 12px',
                      borderRadius: '6px',
                      border: 'none',
                      background: chatMode === 'agent' ? 'rgba(139, 92, 246, 0.3)' : 'transparent',
                      color: chatMode === 'agent' ? '#fff' : 'rgba(255, 255, 255, 0.7)',
                      cursor: 'pointer',
                      fontWeight: chatMode === 'agent' ? '600' : '400',
                      transition: 'all 0.2s'
                    }}
                    title="โหมด Agent - AI ดำเนินการเองทั้งหมด"
                  >
                    🤖 Agent
                  </button>
                </div>
                
                {/* Mobile: Dropdown */}
                <div className="chat-mode-toggle-mobile" ref={chatModeDropdownRef}>
                  <button
                    className="chat-mode-dropdown-button"
                    onClick={() => setIsChatModeDropdownOpen(!isChatModeDropdownOpen)}
                    title={chatMode === 'normal' ? 'โหมดปกติ' : 'โหมด Agent'}
                  >
                    <span>{chatMode === 'normal' ? '📋 Normal' : '🤖 Agent'}</span>
                    <svg className="chat-mode-dropdown-icon" fill="currentColor" viewBox="0 0 24 24">
                      <path d="M7 10l5 5 5-5z"/>
                    </svg>
                  </button>
                  
                  {isChatModeDropdownOpen && (
                    <div className="chat-mode-dropdown-menu">
                      <button
                        className={`chat-mode-dropdown-item ${chatMode === 'normal' ? 'active' : ''}`}
                        onClick={() => {
                          setChatMode('normal');
                          localStorage.setItem('chat_mode', 'normal');
                          setIsChatModeDropdownOpen(false);
                        }}
                      >
                        <span>📋 Normal</span>
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
                        <span>🤖 Agent</span>
                        {chatMode === 'agent' && <span className="chat-mode-check">✓</span>}
                      </button>
                    </div>
                  )}
                </div>
              </div>
            </div>
          </div>

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
              {!isLoadingHistory && messages.map((message) => (
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
                                {message.currentPlan.summary.currency || 'THB'}{' '}
                                {message.currentPlan.summary.total_price?.toLocaleString('th-TH')}
                              </div>
                            )}
                          </div>
                        </div>
                      )}

                          {(() => {
                            // ✅ Seamless workflow: หลังเลือกช้อยส์ ให้แสดง Trip Summary + Edit + User + Confirm ต่อเนื่อง
                            // Show TripSummaryCard เมื่อมี Core Segments (Flight OR Hotel) ที่ Confirmed แล้ว
                            const hasCurrentPlan = message.currentPlan;
                            const hasSelectedPlan = selectedPlan;
                            
                            // Check for completeness - ผ่อนปรนกว่าเดิม
                            const plan = selectedPlan || message.currentPlan;
                            
                            // Helper to check if CORE segments (Flight OR Hotel) are ready
                            const checkCoreSegmentsReady = (p) => {
                              if (!p) {
                                // ✅ Debug only - not an error, just means plan hasn't been created yet
                                console.debug('checkCoreSegmentsReady: No plan provided (this is normal for new chats)');
                                return false;
                              }
                              
                              // Flatten all segments from the new structure
                              const flights = p.travel?.flights ? 
                                [...(p.travel.flights.outbound || []), ...(p.travel.flights.inbound || [])] : 
                                (Array.isArray(p.flights) ? p.flights : []); // Fallback for old structure
                                
                              const accommodations = p.accommodation?.segments || p.accommodations || [];
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
                              const hasConfirmedFlights = flights.some(seg => {
                                const status = seg.status || seg?.selected_option?.status;
                                return status === 'confirmed' || status === 'CONFIRMED';
                              });
                              const hasConfirmedHotels = accommodations.some(seg => {
                                const status = seg.status || seg?.selected_option?.status;
                                return status === 'confirmed' || status === 'CONFIRMED';
                              });
                              
                              // ✅ Only log in debug mode
                              if (process.env.NODE_ENV === 'development') {
                                console.debug('Core segments ready:', { hasConfirmedFlights, hasConfirmedHotels });
                              }
                              
                              // ถ้ามี Flight หรือ Hotel confirmed แล้ว → พร้อมแสดง Summary
                              // Transfer เป็น Optional (ไม่จำเป็นต้อง confirmed)
                              return hasConfirmedFlights || hasConfirmedHotels;
                            };

                            const isCoreReady = checkCoreSegmentsReady(plan);
                            
                            // ✅ แสดง TripSummaryCard เมื่อ:
                            // 1. เป็น bot message
                            // 2. มี Plan
                            // 3. มี Core Segments (Flight OR Hotel) ที่ Confirmed แล้ว (หรือมี selected_option)
                            // 4. ไม่ใช่ข้อความ error
                            // 5. ✅ ตรวจสอบ workflow step - ต้องถึงขั้น trip_summary ก่อน
                            const workflowValidation = message.workflowValidation || message.agentState?.workflow_validation || {};
                            const currentWorkflowStep = workflowValidation.current_step || message.agentState?.step || "planning";
                            const isWorkflowComplete = workflowValidation.is_complete || false;
                            
                            // ✅ ห้ามข้ามขั้นตอน - ต้องถึง trip_summary ก่อน
                            const canShowSummary = currentWorkflowStep === "trip_summary" || 
                                                  (currentWorkflowStep === "confirmed" && isWorkflowComplete) ||
                                                  (isCoreReady && isWorkflowComplete);
                            
                            const shouldShow = message.type === 'bot' && 
                                   (hasCurrentPlan || hasSelectedPlan) &&
                                   isCoreReady &&
                                   canShowSummary &&  // ✅ เพิ่มเงื่อนไข workflow step
                                   !message.text?.includes('❌');
                            
                            // ✅ Debug: log decision
                            if (hasCurrentPlan || hasSelectedPlan) {
                              console.log('🔍 TripSummaryCard display decision:', {
                                hasCurrentPlan,
                                hasSelectedPlan,
                                isCoreReady,
                                hasError: message.text?.includes('❌'),
                                shouldShow
                              });
                            }
                            
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
                          {/* 1. Slot Choices Summary - แสดงผลรวมตามหมวดหมู่ที่กรองแล้ว */}
                          {message.slotChoices && message.slotChoices.length > 0 && message.slotIntent && (() => {
                            const filteredCount = message.slotChoices.filter(choice => {
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
                                  {!['flight', 'hotel', 'transport', 'transfer'].includes(message.slotIntent) && 'ตัวเลือก'}
                                  {' '}({filteredCount} รายการ)
                                </span>
                              </div>
                            );
                          })()}

                          {/* 2. Plan Choices Summary */}
                          {(() => {
                            const hasPlanChoices = message.planChoices && 
                              Array.isArray(message.planChoices) && 
                              message.planChoices.length > 0;
                            const hasSlotChoices = message.slotChoices && message.slotChoices.length > 0;
                            const hasCurrentPlan = message.currentPlan && 
                              typeof message.currentPlan === 'object' && 
                              Object.keys(message.currentPlan).length > 0;
                            
                            const shouldShowPlanChoices = hasPlanChoices && 
                                   (!hasSlotChoices || !message.slotIntent) && 
                                   !hasCurrentPlan;
                            
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
                        
                        {/* 1. Slot Choices Grid - แสดงเฉพาะข้อความล่าสุดที่มี slotChoices (แก้บั๊กแชทซ้อนหลายครั้ง) */}
                        {message.slotChoices && message.slotChoices.length > 0 && (() => {
                          const isLatestWithChoices = latestBotWithChoices && message.id === latestBotWithChoices.id;
                          const effectiveIntent = message.slotIntent || null;
                          const filteredChoices = message.slotChoices.filter(choice => {
                            if (!effectiveIntent) return true;
                            if (effectiveIntent === 'transport' || effectiveIntent === 'transfer') {
                              return choice.category === 'transport' || choice.category === 'transfer';
                            }
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
                            const cat = intent || choice.category;
                            if (cat === 'flight') return (choice.flight && (choice.flight.segments?.length > 0 || choice.flight.outbound?.length || choice.flight.inbound?.length)) ? PlanChoiceCardFlights : PlanChoiceCard;
                            if (cat === 'hotel') return choice.hotel ? PlanChoiceCardHotels : PlanChoiceCard;
                            if (cat === 'transport' || cat === 'transfer') return (choice.transport || choice.car || choice.ground_transport) ? PlanChoiceCardTransfer : PlanChoiceCard;
                            return PlanChoiceCard;
                          };
                          if (filteredChoices.length === 0) return null;
                          return (
                            <div className="plan-choices-block full-width-block" key="slot-choices-block">
                              {isAdmin && console.log('🛠️ Admin Debug - Rendering PlanChoiceCard grid:', filteredChoices.length, 'slotIntent:', effectiveIntent)}
                              <div className="plan-choices-grid">
                                {filteredChoices.map((choice, idx) => {
                                  const intent = effectiveIntent || choice.category;
                                  const SlotCard = getSlotCardComponent(intent, choice);
                                  const stableKey = `slot-${String(message.id ?? '')}-${idx}-${choice.id ?? choice._original_id ?? idx}`;
                                  return (
                                    <SlotCard
                                      key={stableKey}
                                      choice={choice}
                                      onSelect={(id) => handleSelectSlotChoice(id, intent || choice.category, choice, message)}
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

                        {/* 2. Plan Choices Grid - แสดงเฉพาะข้อความล่าสุดที่มี planChoices (แก้บั๊กแชทซ้อนหลายครั้ง) */}
                        {(() => {
                          const hasPlanChoices = message.planChoices && 
                            Array.isArray(message.planChoices) && 
                            message.planChoices.length > 0;
                          const hasSlotChoices = message.slotChoices && message.slotChoices.length > 0;
                          const hasCurrentPlan = message.currentPlan && 
                            typeof message.currentPlan === 'object' && 
                            Object.keys(message.currentPlan).length > 0;
                          const shouldShowPlanChoices = hasPlanChoices && 
                                 (!hasSlotChoices || !message.slotIntent) && 
                                 !hasCurrentPlan;
                          const isLatestWithChoices = latestBotWithChoices && message.id === latestBotWithChoices.id;
                          
                          if (!shouldShowPlanChoices) return null;
                          if (!isLatestWithChoices) {
                            return (
                              <div className="plan-choices-summary-compact" key="plan-summary-old">
                                <span className="summary-text">✈️ แผนเที่ยวที่จัดให้ {message.planChoices.length} ช้อยส์ (ดูตัวเลือกล่าสุดด้านล่าง)</span>
                              </div>
                            );
                          }
                          return (
                            <div className="plan-choices-block full-width-block">
                              <div className="plan-choices-grid">
                                {message.planChoices.map((choice) => (
                                  <PlanChoiceCard
                                    key={choice.id || `choice-${choice.title || ''}-${choice.id ?? ''}`}
                                    choice={choice}
                                    onSelect={(id) => handleSelectPlanChoice(id, choice)}
                                  />
                                ))}
                              </div>
                            </div>
                          );
                        })()}
                      </>
                    )}

                    {/* Action buttons under messages (ChatGPT style) */}
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
                        {agentStatus?.step && getToolInfo(agentStatus.step) && (
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
                            'controller_iter_1': '🔄 กำลังประมวลผล (รอบที่ 1/3)...',
                            'controller_iter_2': '🔄 กำลังประมวลผล (รอบที่ 2/3)...',
                            'controller_iter_3': '🔄 กำลังประมวลผล (รอบที่ 3/3)...',
                            
                            // Actions
                            'create_itinerary': '📋 กำลังสร้างแผนการเดินทาง...',
                            'update_req': '📝 กำลังอัปเดตข้อมูลทริป...',
                            'call_search': '🔍 กำลังค้นหา...',
                            'select_option': '✅ กำลังบันทึกตัวเลือก...',
                            
                            // Searching
                            'searching': '🔍 กำลังค้นหาเที่ยวบินและที่พัก...',
                            'searching_flights': '✈️ กำลังค้นหาเที่ยวบิน...',
                            'searching_hotels': '🏨 กำลังค้นหาที่พัก...',
                            
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
                            
                            // Responding
                            'acting': '⚙️ กำลังดำเนินการ...',
                            'speaking': '💬 กำลังสรุปคำตอบ...',
                            'responder_start': '💬 กำลังสรุปคำตอบ...',
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
                              {/* ✅ Step Title - แสดงขั้นตอนหลักที่ Agent กำลังทำ */}
                              {agentStatus.step && (
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
                              {/* ✅ Status Indicator - แสดงสถานะทั่วไป (ถ้าไม่ซ้ำกับ step) */}
                              {agentStatus.status && 
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
                className={`btn-mic ${isVoiceMode ? 'btn-mic-conversation' : ''}`}
                title={isVoiceMode ? 'กดเพื่อหยุดการสนทนาด้วยเสียง' : 'กดเพื่อเริ่มสนทนากับ Agent ด้วยเสียง'}
              >
                {isVoiceMode ? (
                  <svg className="mic-icon" fill="currentColor" viewBox="0 0 24 24">
                    <path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm-2 14.5v-9l6 4.5-6 4.5z"/>
                  </svg>
                ) : (
                  <svg className="mic-icon" fill="currentColor" viewBox="0 0 24 24">
                    <path d="M12 14c1.66 0 3-1.34 3-3V5c0-1.66-1.34-3-3-3S9 3.34 9 5v6c0 1.66 1.34 3 3 3z" />
                    <path d="M17 11c0 2.76-2.24 5-5 5s-5-2.24-5-5H5c0 3.53 2.61 6.43 6 6.92V21h2v-3.08c3.39-.49 6-3.39 6-6.92h-2z" />
                  </svg>
                )}
              </button>
              <button onClick={handleSend} disabled={!inputText.trim()} className="btn-send">
                Send
              </button>
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
            <div className="powered-by">Powered by Gemini + Amadeus อาจมีข้อผิดพลาด ควรตรวจสอบข้อมูลสำคัญ</div>
          </div>
        </div>

      </main>
    </div>
    </ChatErrorBoundary>
  );
}