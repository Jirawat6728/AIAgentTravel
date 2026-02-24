import React, { useEffect, useState, useCallback, useRef, Suspense, lazy, useMemo } from "react";
import LoginPage from "./pages/auth/LoginPage.jsx";
import RegisterPage from "./pages/auth/RegisterPage.jsx";
import ResetPasswordPage from "./pages/auth/ResetPasswordPage.jsx";
import VerifyEmailChangePage from "./pages/auth/VerifyEmailChangePage.jsx";
import HomePage from "./pages/home/HomePage.jsx";
const AITravelChat = lazy(() => import("./pages/chat/AITravelChat.jsx"));
import UserProfileEditPage from "./pages/profile/UserProfileEditPage.jsx";
import SettingsPage from "./pages/settings/SettingsPage.jsx";
import MyBookingsPage from "./pages/bookings/MyBookingsPage.jsx";
import PaymentPage from "./pages/bookings/PaymentPage.jsx";
import FlightsPage from "./pages/search/FlightsPage.jsx";
import HotelsPage from "./pages/search/HotelsPage.jsx";
import CarRentalsPage from "./pages/search/CarRentalsPage.jsx";
import Lottie from "lottie-react";
import loadingAnimation from "./assets/loading.json";
import { clearAllUserData, checkAndClearIfUserChanged } from "./utils/userDataManager.js";
import { sha256Password } from "./utils/passwordHash.js";
import { ThemeProvider } from "./context/ThemeContext.jsx";
import { LanguageProvider } from "./context/LanguageContext.jsx";
import { FontSizeProvider } from "./context/FontSizeContext.jsx";
import Swal from "sweetalert2";

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || "http://localhost:8000";
const GOOGLE_CLIENT_ID = import.meta.env.VITE_GOOGLE_CLIENT_ID || "";
const FIREBASE_ENABLED = true; // ใช้ Firebase Email Verification เสมอ

// URL path mapping
const VIEW_PATHS = {
  'home': '/',
  'login': '/login',
  'register': '/register',
  'reset-password': '/reset-password',
  'verify-email-change': '/verify-email-change',
  'chat': '/chat',
  'profile': '/profile',
  'bookings': '/bookings',
  'payment': '/payment',
  'flights': '/flights',
  'hotels': '/hotels',
  'car-rentals': '/car-rentals',
  'settings': '/settings',
  'amadeus-viewer': '/amadeus-viewer'
};

const PATH_VIEWS = Object.fromEntries(
  Object.entries(VIEW_PATHS).map(([view, path]) => [path, view])
);

// Get view from URL path (หน้า explore ถูกลบออก — /explore ไปแชท)
function getViewFromPath() {
  const path = window.location.pathname;
  if (path.startsWith('/payment') || path.includes('/payment')) {
    return 'payment';
  }
  if (path === '/verify-email-change') return 'verify-email-change';
  if (path === '/explore') return 'chat';
  return PATH_VIEWS[path] || 'home';
}

// Get path from view
function getPathFromView(view) {
  return VIEW_PATHS[view] || '/';
}

function App() {
  // Initialize view from URL or localStorage
  const getInitialView = () => {
    const pathView = getViewFromPath();
    if (pathView !== 'home') {
      return pathView;
    }
    const savedView = localStorage.getItem("app_view");
    if (!savedView) return "home";
    // Protected views require login — if not logged in, show home to avoid blank screen
    const protectedViews = ['chat', 'profile', 'bookings', 'payment', 'flights', 'hotels', 'car-rentals', 'settings'];
    const savedIsLoggedIn = localStorage.getItem("is_logged_in") === "true";
    if (protectedViews.includes(savedView) && !savedIsLoggedIn) {
      return "home";
    }
    return savedView;
  };

  const [view, setView] = useState(getInitialView); // 'home' | 'login' | 'register' | 'chat' | 'profile' | 'bookings' | 'profile'
  const [isLoggedIn, setIsLoggedIn] = useState(false);
  const [user, setUser] = useState(null);
  const [notificationCount, setNotificationCount] = useState(0);
  const [notifications, setNotifications] = useState([]);
  const [pendingPrompt, setPendingPrompt] = useState("");
  const [isAuthChecking, setIsAuthChecking] = useState(true); // Loading state for auth check
  const [loadingData, setLoadingData] = useState(loadingAnimation); // Lottie animation data

  // Format date for notification
  const formatNotificationDate = (dateString) => {
    if (!dateString) return 'เมื่อไม่นานมานี้';
    try {
      const date = new Date(dateString);
      const now = new Date();
      const diffMs = now - date;
      const diffMins = Math.floor(diffMs / 60000);
      const diffHours = Math.floor(diffMs / 3600000);
      const diffDays = Math.floor(diffMs / 86400000);
      
      if (diffMins < 1) return 'เมื่อสักครู่';
      if (diffMins < 60) return `เมื่อ ${diffMins} นาทีที่แล้ว`;
      if (diffHours < 24) return `เมื่อ ${diffHours} ชั่วโมงที่แล้ว`;
      if (diffDays === 1) return 'เมื่อวาน';
      if (diffDays < 7) return `เมื่อ ${diffDays} วันที่แล้ว`;
      
      return date.toLocaleDateString('th-TH', { 
        year: 'numeric', 
        month: 'short', 
        day: 'numeric',
        hour: '2-digit',
        minute: '2-digit'
      });
    } catch (e) {
      return 'เมื่อไม่นานมานี้';
    }
  };

  // ✅ Fetch notification count and details from notification API
  const fetchNotificationCount = useCallback(async () => {
    if (!user) {
      setNotificationCount(0);
      setNotifications([]);
      return;
    }
    
    try {
      const headers = { 'Content-Type': 'application/json' };
      const userIdToSend = user?.user_id || user?.id;
      if (userIdToSend) {
        headers['X-User-ID'] = userIdToSend;
      }
      
      // ✅ Fetch from notification API (X-User-ID ให้ตรงกับ booking create/list)
      const res = await fetch(`${API_BASE_URL}/api/notification/list`, {
        headers,
        credentials: 'include',
      });
      const data = await res.json();
      
      if (data.ok && Array.isArray(data.notifications)) {
        setNotificationCount(data.unread_count || 0);
        
        // ✅ Map notifications to frontend format — เก็บ created_at ไว้คำนวณ time แบบ live
        const notificationsList = data.notifications.map((notif) => ({
          id: notif.id,
          type: notif.type || 'info',
          title: notif.title || 'แจ้งเตือน',
          message: notif.message || '',
          created_at: notif.created_at || new Date().toISOString(),
          isRead: notif.read === true,
          bookingId: notif.booking_id,
          metadata: notif.metadata || {}
        }));
        
        setNotifications(notificationsList);
      }
      // ถ้า !data.ok ไม่ reset เป็น [] เพื่อไม่ให้ notification หายเมื่อ API error ชั่วคราว
    } catch (error) {
      console.error("Failed to fetch notifications:", error);
      setNotificationCount(0);
      setNotifications([]);
    }
  }, [user]);

  // ✅ Handle mark notification as read
  const handleMarkNotificationAsRead = useCallback(async (notificationId) => {
    try {
      const headers = { 'Content-Type': 'application/json' };
      const uid = user?.user_id || user?.id;
      if (uid) headers['X-User-ID'] = uid;
      
      // ✅ Mark as read in backend
      await fetch(`${API_BASE_URL}/api/notification/mark-read?notification_id=${notificationId}`, {
        method: 'POST',
        headers,
        credentials: 'include',
      });
      
      // ✅ Update local state
      setNotifications(prev => 
        prev.map(notif => 
          notif.id === notificationId ? { ...notif, isRead: true } : notif
        )
      );
      // ✅ Update notification count
      setNotificationCount(prev => Math.max(0, prev - 1));
    } catch (error) {
      console.error("Failed to mark notification as read:", error);
    }
  }, [user]);

  // ล้างทั้งหมด = mark-all-read (ไม่ลบ เพื่อให้ยังดูประวัติได้)
  const handleMarkAllNotificationsAsRead = useCallback(async () => {
    try {
      const headers = { 'Content-Type': 'application/json' };
      const uid = user?.user_id || user?.id;
      if (uid) headers['X-User-ID'] = uid;
      await fetch(`${API_BASE_URL}/api/notification/mark-all-read`, {
        method: 'POST',
        headers,
        credentials: 'include',
      });
      // อัปเดต local state ทันที — mark ทุกอันเป็น read แต่ไม่ลบ
      setNotifications(prev => prev.map(n => ({ ...n, isRead: true })));
      setNotificationCount(0);
    } catch (error) {
      console.error("Failed to mark all notifications as read:", error);
    }
  }, [user]);

  // ── Real-time notifications via SSE ──────────────────────────────────────
  // โหลดครั้งแรกด้วย fetchNotificationCount แล้ว subscribe SSE สำหรับ push ทันที
  useEffect(() => {
    if (!isLoggedIn || !user) {
      setNotificationCount(0);
      setNotifications([]);
      return;
    }

    // โหลดรายการ notification ครั้งแรก
    fetchNotificationCount();

    // สร้าง SSE connection
    const userIdToSend = user?.user_id || user?.id;
    const headers = userIdToSend ? `&user_id=${encodeURIComponent(userIdToSend)}` : '';
    const sseUrl = `${API_BASE_URL}/api/notification/stream?_uid=${encodeURIComponent(userIdToSend || '')}`;

    let es;
    let reconnectTimer;
    let retryDelay = 2000;

    const connect = () => {
      es = new EventSource(sseUrl, { withCredentials: true });

      es.onopen = () => {
        retryDelay = 2000; // reset backoff
      };

      es.onmessage = (event) => {
        try {
          const msg = JSON.parse(event.data);
          if (msg.type === 'new_notification') {
            const notif = msg.notification;
            // เพิ่ม notification ใหม่เข้า state ทันที
            const formatted = {
              id: notif.id || notif._id,
              type: notif.type || 'info',
              title: notif.title || 'แจ้งเตือน',
              message: notif.message || '',
              created_at: notif.created_at || new Date().toISOString(),
              isRead: false,
              bookingId: notif.booking_id,
              metadata: notif.metadata || {}
            };
            setNotifications(prev => [formatted, ...prev]);
            setNotificationCount(prev => prev + 1);
          }
          // heartbeat และ connected ไม่ต้องทำอะไร
        } catch (e) {
          console.error('SSE parse error:', e);
        }
      };

      es.onerror = () => {
        es.close();
        // reconnect with exponential backoff (max 30s)
        reconnectTimer = setTimeout(() => {
          retryDelay = Math.min(retryDelay * 2, 30000);
          connect();
        }, retryDelay);
      };
    };

    connect();

    // fallback poll ทุก 5 นาที (กรณี SSE หลุด)
    const fallbackInterval = setInterval(fetchNotificationCount, 300000);

    return () => {
      if (es) es.close();
      if (reconnectTimer) clearTimeout(reconnectTimer);
      clearInterval(fallbackInterval);
    };
  }, [isLoggedIn, user?.id]);

  // Navigate without changing browser URL (path stays the same on all pages)
  const navigateToView = useCallback((newView, replace = false) => {
    setView(newView);
    // Save view to localStorage (but not login/register pages)
    if (newView !== 'login' && newView !== 'register' && newView !== 'reset-password') {
      localStorage.setItem("app_view", newView);
    }
  }, []);

  // Keep browser URL always at / (no path change on any page)
  // ยกเว้น verify-email-change — ต้องเก็บ query string (?token=) ไว้ให้ component อ่านได้
  useEffect(() => {
    if (window.history.replaceState && window.location.pathname !== '/' && view !== 'verify-email-change') {
      window.history.replaceState({ view }, '', '/');
    }
  }, [view]);

  // Optional: handle browser back
  useEffect(() => {
    const handlePopState = (event) => {
      const newView = event.state?.view || 'home';
      setView(newView);
      if (newView !== 'login' && newView !== 'register' && newView !== 'reset-password') {
        localStorage.setItem("app_view", newView);
      }
    };
    window.addEventListener('popstate', handlePopState);
    return () => window.removeEventListener('popstate', handlePopState);
  }, []);

  useEffect(() => {
    // Save view to localStorage whenever it changes
    // Don't save login/register views, usually want to go to home or previous intent
    if (view !== 'login' && view !== 'register' && view !== 'reset-password') {
      localStorage.setItem("app_view", view);
    }
  }, [view]);

  const googleInitRef = useRef(false);

  // Check if user has required profile information
  const hasRequiredProfileInfo = useCallback((userData) => {
    if (!userData) return true;
    // Check if user has basic info: first_name or full_name
    // Also check if email exists (should always exist for logged in users)
    const hasName = !!(userData.first_name || userData.full_name || userData.name);
    const hasEmail = !!userData.email;
    return hasName && hasEmail;
  }, []);

  // Restore session from localStorage immediately on mount (for instant UI)
  useEffect(() => {
    const savedIsLoggedIn = localStorage.getItem("is_logged_in") === "true";
    const savedUserData = localStorage.getItem("user_data");
    const savedTimestamp = localStorage.getItem("session_timestamp");
    
    if (savedIsLoggedIn && savedUserData) {
      try {
        // Check if saved data is not too old (max 30 days)
        const maxAge = 30 * 24 * 60 * 60 * 1000; // 30 days in milliseconds
        if (savedTimestamp) {
          const age = Date.now() - parseInt(savedTimestamp, 10);
          if (age > maxAge) {
            // Data too old, clear it
            localStorage.removeItem("is_logged_in");
            localStorage.removeItem("user_data");
            localStorage.removeItem("session_timestamp");
            return;
          }
        }
        
        const userData = JSON.parse(savedUserData);
        // ✅ SECURITY: Clear trips data when restoring user (in case user changed)
        const currentUserId = userData?.id || userData?.user_id;
        const savedTrips = localStorage.getItem("ai_travel_trips_v1");
        if (savedTrips) {
          try {
            const trips = JSON.parse(savedTrips);
            const firstTripUserId = trips[0]?.userId || trips[0]?.user_id;
            // ✅ If trips belong to different user, clear them
            if (firstTripUserId && firstTripUserId !== currentUserId) {
              console.warn(`🚨 SECURITY: Clearing trips from different user (${firstTripUserId} vs ${currentUserId})`);
              localStorage.removeItem("ai_travel_trips_v1");
              localStorage.removeItem("ai_travel_active_trip_id_v1");
              sessionStorage.removeItem("ai_travel_loaded_trips");
            }
          } catch (e) {
            console.warn("Failed to check trips user_id:", e);
          }
        }
        // ✅ Normalize: ใช้ user_id เป็น id หลักเสมอ
        const normalizedUserData = { ...userData, id: userData.user_id || userData.id };
        setIsLoggedIn(true);
        setUser(normalizedUserData);
      } catch (e) {
        console.error("Failed to parse saved user data:", e);
        localStorage.removeItem("is_logged_in");
        localStorage.removeItem("user_data");
        localStorage.removeItem("session_timestamp");
      }
    }
  }, []); // Only run once on mount

  const refreshMe = useCallback(async () => {
    try {
      const res = await fetch(`${API_BASE_URL}/api/auth/me`, { credentials: "include" });
      const data = await res.json();
      if (data?.user) {
        // ✅ SECURITY: Check if user changed and clear ALL data if needed
        const newUserId = data.user.id || data.user.user_id;
        const currentUserId = user?.id || user?.user_id;
        
        if (currentUserId && newUserId && currentUserId !== newUserId) {
          console.warn(`🚨 SECURITY: User changed from ${currentUserId} to ${newUserId}, clearing ALL data`);
          clearAllUserData();
        } else {
          // ✅ Also check localStorage for user_id mismatch
          checkAndClearIfUserChanged(newUserId);
        }
        
        // ✅ Normalize: ใช้ user_id เป็น id หลักเสมอ (ป้องกัน MongoDB _id หลุดมาเป็น id)
        const normalizedUser = { ...data.user, id: data.user.user_id || data.user.id };
        setIsLoggedIn(true);
        setUser(normalizedUser);
        // Save to localStorage with timestamp for persistent login
        localStorage.setItem("is_logged_in", "true");
        localStorage.setItem("user_data", JSON.stringify(normalizedUser));
        localStorage.setItem("session_timestamp", Date.now().toString());
        // Don't auto-redirect to profile page
        // Let users navigate freely - they can complete their profile when they want
        // Only check profile completeness when they try to access features that require it
      } else {
        // Session expired or invalid - clear local state
        setIsLoggedIn(false);
        setUser(null);
        localStorage.removeItem("is_logged_in");
        localStorage.removeItem("user_data");
        localStorage.removeItem("session_timestamp");
        // If on protected view but not logged in, redirect to home
        // Allow public views to stay when not logged in
        const currentView = getViewFromPath();
        const publicViews = ['home', 'login', 'register', 'reset-password', 'verify-email-change'];
        if (!publicViews.includes(currentView)) {
          navigateToView("home");
        }
      }
    } catch (e) {
      // If backend is down or CORS fails, keep local state if available
      // This allows offline usage with cached data
      const savedIsLoggedIn = localStorage.getItem("is_logged_in") === "true";
      if (!savedIsLoggedIn) {
        setIsLoggedIn(false);
        setUser(null);
        localStorage.removeItem("is_logged_in");
        localStorage.removeItem("user_data");
        localStorage.removeItem("session_timestamp");
        // Allow public views to stay when not logged in
        const currentView = getViewFromPath();
        const publicViews = ['home', 'login', 'register', 'reset-password', 'verify-email-change'];
        if (!publicViews.includes(currentView)) {
          navigateToView("home");
        }
      }
      // If we have saved state, keep it (user might be offline)
      // The next refreshMe() call will verify the session when backend is available
    } finally {
      setIsAuthChecking(false);
    }
  }, [hasRequiredProfileInfo, navigateToView]);

  useEffect(() => {
    // Verify session with backend after restoring from localStorage
    refreshMe();
    
    // Refresh session periodically (every 5 minutes) to keep user logged in
    // This extends the session cookie expiry as long as user is active
    const refreshInterval = setInterval(() => {
      // Check localStorage first to see if user should be logged in
      const savedIsLoggedIn = localStorage.getItem("is_logged_in") === "true";
      if (savedIsLoggedIn || isLoggedIn) {
        refreshMe();
      }
    }, 5 * 60 * 1000); // 5 minutes
    
    return () => clearInterval(refreshInterval);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [isLoggedIn]); // Run when isLoggedIn changes or on mount

  const goHome = () => navigateToView("home");

  // ---- OTP Verification Dialog ----
  const showOTPDialog = async (email) => {
    let otpValue = '';

    const buildHTML = (err = '') => `
      <p style="color:#6366f1;font-weight:600;font-size:14px;margin:0 0 16px;word-break:break-all;">${email}</p>
      <p style="color:#4b5563;font-size:14px;margin:0 0 16px;line-height:1.6;">
        เราได้ส่งรหัส OTP 6 หลักไปที่อีเมลของคุณแล้ว<br>
        <span style="color:#9ca3af;font-size:12px;">ไม่พบอีเมล? ตรวจสอบโฟลเดอร์ Spam</span>
      </p>
      <div id="otp-inputs" style="display:flex;gap:8px;justify-content:center;margin:0 0 8px;">
        ${[0,1,2,3,4,5].map(i => `
          <input id="otp-${i}" type="text" inputmode="numeric" maxlength="1"
            style="width:44px;height:52px;text-align:center;font-size:24px;font-weight:700;
                   border:2px solid ${err ? '#ef4444' : '#a5b4fc'};border-radius:10px;
                   color:#4f46e5;background:#f5f3ff;outline:none;" />`).join('')}
      </div>
      ${err ? `<p style="color:#ef4444;font-size:13px;margin:4px 0 0;">${err}</p>` : ''}
      <p style="color:#f59e0b;font-size:12px;margin:12px 0 0;">⏰ รหัสหมดอายุใน <strong>10 นาที</strong></p>
    `;

    const setupInputs = () => {
      for (let i = 0; i < 6; i++) {
        const el = document.getElementById(`otp-${i}`);
        if (!el) continue;
        el.addEventListener('input', (e) => {
          e.target.value = e.target.value.replace(/\D/g, '').slice(0, 1);
          if (e.target.value && i < 5) document.getElementById(`otp-${i+1}`)?.focus();
          otpValue = Array.from({length:6}, (_,j) => document.getElementById(`otp-${j}`)?.value || '').join('');
        });
        el.addEventListener('keydown', (e) => {
          if (e.key === 'Backspace' && !e.target.value && i > 0) document.getElementById(`otp-${i-1}`)?.focus();
        });
        el.addEventListener('paste', (e) => {
          e.preventDefault();
          const pasted = (e.clipboardData.getData('text') || '').replace(/\D/g, '').slice(0, 6);
          pasted.split('').forEach((ch, j) => {
            const inp = document.getElementById(`otp-${j}`);
            if (inp) inp.value = ch;
          });
          otpValue = pasted.padEnd(6, '').slice(0, 6);
          document.getElementById(`otp-${Math.min(pasted.length, 5)}`)?.focus();
        });
      }
      document.getElementById('otp-0')?.focus();
    };

    // loop จนกว่าจะยืนยันสำเร็จหรือ cancel
    while (true) {
      otpValue = '';
      const result = await Swal.fire({
        title: 'กรอกรหัส OTP 📧',
        html: buildHTML(),
        showCancelButton: true,
        confirmButtonText: 'ยืนยัน',
        confirmButtonColor: '#6366f1',
        cancelButtonText: 'ยกเลิก',
        cancelButtonColor: '#e5e7eb',
        allowOutsideClick: false,
        focusConfirm: false,
        didOpen: setupInputs,
        preConfirm: () => {
          otpValue = Array.from({length:6}, (_,i) => document.getElementById(`otp-${i}`)?.value || '').join('');
          if (otpValue.length < 6 || /\D/.test(otpValue)) {
            Swal.showValidationMessage('กรุณากรอกรหัส OTP ให้ครบ 6 หลัก');
            return false;
          }
          return otpValue;
        },
      });

      if (!result.isConfirmed) {
        // user กด cancel → ไปหน้า login
        navigateToView('login');
        return false;
      }

      // เรียก API verify
      try {
        const res = await fetch(`${API_BASE_URL}/api/auth/verify-email`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ email, otp: result.value }),
        });
        const data = await res.json().catch(() => ({}));

        if (res.ok && data.ok) {
          await Swal.fire({
            icon: 'success',
            title: data.already_verified ? 'อีเมลยืนยันแล้ว ✅' : 'ยืนยันอีเมลสำเร็จ! 🎉',
            html: `<p style="color:#4b5563;margin:0 0 4px;">อีเมลของคุณได้รับการยืนยันเรียบร้อยแล้ว</p>
                   <p style="color:#6366f1;font-weight:600;margin:0;">พร้อมใช้งาน AI Travel Agent แล้ว!</p>`,
            confirmButtonText: 'เข้าสู่ระบบ',
            confirmButtonColor: '#6366f1',
            allowOutsideClick: false,
          });
          navigateToView('login');
          return true;
        } else {
          const errMsg = typeof data.detail === 'string' ? data.detail : 'รหัส OTP ไม่ถูกต้อง';
          // แสดง error แล้ว loop ใหม่
          await Swal.fire({
            icon: 'error',
            title: 'OTP ไม่ถูกต้อง',
            html: `<p style="color:#4b5563;margin:0 0 4px;">${errMsg}</p>
                   <p style="color:#9ca3af;font-size:12px;margin:0;">กรุณาตรวจสอบอีเมลและกรอกรหัสใหม่</p>`,
            confirmButtonText: 'ลองใหม่',
            confirmButtonColor: '#6366f1',
            showDenyButton: true,
            denyButtonText: 'ขอรหัสใหม่',
            denyButtonColor: '#e5e7eb',
          });
          if (result.isDenied) {
            // ขอ OTP ใหม่
            await fetch(`${API_BASE_URL}/api/auth/send-verification-email`, {
              method: 'POST',
              headers: { 'Content-Type': 'application/json' },
              body: JSON.stringify({ email }),
              credentials: 'include',
            });
          }
          // loop ต่อ
        }
      } catch {
        await Swal.fire({ icon: 'error', title: 'เกิดข้อผิดพลาด', text: 'ไม่สามารถเชื่อมต่อได้ กรุณาลองใหม่', confirmButtonText: 'ตกลง', confirmButtonColor: '#6366f1' });
      }
    }
  };

  const handleRegister = async (registerData) => {
    try {
      const passwordHash = await sha256Password(registerData.password);
      const payload = { ...registerData, password: passwordHash };
      const res = await fetch(`${API_BASE_URL}/api/auth/register`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "X-Password-Encoding": "sha256",
        },
        credentials: "include",
        body: JSON.stringify(payload)
      });
      
      if (!res.ok) {
        const errorData = await res.json().catch(() => ({ detail: `HTTP ${res.status}: ${res.statusText}` }));
        throw new Error(errorData.detail || `Registration failed: ${res.status} ${res.statusText}`);
      }
      
      const data = await res.json();
      if (data.ok) {
        // Backend ส่ง OTP ไปทางอีเมลแล้ว — เปิด OTP dialog
        if (!data.email_verified && data.verification_email_sent) {
          const emailDisplay = data.email || registerData.email || "";
          await showOTPDialog(emailDisplay);
        }
        return data;
      } else {
        throw new Error(data.detail || "Registration failed");
      }
    } catch (e) {
      if (import.meta.env.DEV) {
        console.error("Registration failed", e?.message ?? "Unknown error");
      }
      throw new Error(e?.message || String(e));
    }
  };

  const handleSignIn = async (email, password, rememberMe = false) => {
    // If no email provided, just navigate to login page
    if (!email) {
      navigateToView("login");
      return;
    }

    // 1. If it's a dev bypass from the dashed button
    if (email === "dev_user" && window.location.hostname === 'localhost') {
      try {
        const res = await fetch(`${API_BASE_URL}/api/auth/dev-login`, { 
          method: "POST",
          credentials: "include" 
        });
        const data = await res.json();
        if (data.ok) {
          setIsLoggedIn(true);
          setUser(data.user);
          // ✅ Save to localStorage if rememberMe is checked
          if (rememberMe) {
            localStorage.setItem("is_logged_in", "true");
            localStorage.setItem("user_data", JSON.stringify(data.user));
            localStorage.setItem("session_timestamp", Date.now().toString());
          }
          navigateToView("chat");
          return;
        }
      } catch (e) {
        console.error("Dev login failed", e);
      }
    }

    // 2. Standard Email login (send SHA-256 of password so plain password never appears in Payload/DevTools)
    if (email && email.includes('@')) {
      try {
        const passwordHash = await sha256Password(password);
        const res = await fetch(`${API_BASE_URL}/api/auth/login`, {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
            "X-Password-Encoding": "sha256",
          },
          credentials: "include",
          body: JSON.stringify({ email, password: passwordHash, remember_me: rememberMe })
        });
        
        // ✅ Check if response is ok before parsing JSON
        if (!res.ok) {
          const errorData = await res.json().catch(() => ({ detail: `HTTP ${res.status}: ${res.statusText}` }));
          // อีเมลยังไม่ยืนยัน → ส่ง Firebase verification email แล้วไปหน้า verify-email-sent
          if (res.status === 403 && errorData?.detail?.code === "EMAIL_NOT_VERIFIED") {
            const detail = errorData.detail;
            const emailDisplay = detail.email || email || "";
            // เปิด OTP dialog ทันที (backend ส่ง OTP ใหม่ให้แล้วพร้อมกับ 403)
            await showOTPDialog(emailDisplay);
            return;
          }
          const detailMsg = typeof errorData.detail === "object" ? errorData.detail?.message : errorData.detail;
          throw new Error(detailMsg || `Login failed: ${res.status} ${res.statusText}`);
        }
        
        const data = await res.json();
        if (data.ok) {
          const newUserId = data.user?.id || data.user?.user_id;
          const currentUserId = user?.id || user?.user_id;
          
          // ✅ SECURITY: Only clear data if user changed
          const userChanged = currentUserId && newUserId && currentUserId !== newUserId;
          
          if (userChanged) {
            // User changed - clear all data
            setIsLoggedIn(false);
            setUser(null);
            setNotificationCount(0);
            setNotifications([]);
            
            // ✅ Clear all localStorage data (including trips and sessions)
            localStorage.removeItem("is_logged_in");
            localStorage.removeItem("user_data");
            localStorage.removeItem("session_timestamp");
            localStorage.removeItem("app_view");
            localStorage.removeItem("ai_travel_trips_v1"); // ✅ Clear trips data
            localStorage.removeItem("ai_travel_active_trip_id_v1"); // ✅ Clear active trip
            
            // ✅ Clear all sessionStorage data
            sessionStorage.removeItem("ai_travel_loaded_trips"); // ✅ Clear loaded trips cache
          } else {
            // Same user - just update user data, keep trips (will be synced from backend)
            // Only clear notification state
            setNotificationCount(0);
            setNotifications([]);
          }
          
          // Set new user data
          setIsLoggedIn(true);
          setUser(data.user);
          
          // ✅ Save to localStorage for persistent login (always save, but backend will set longer cookie if remember_me=true)
          localStorage.setItem("is_logged_in", "true");
          localStorage.setItem("user_data", JSON.stringify(data.user));
          localStorage.setItem("session_timestamp", Date.now().toString());
          
          // ✅ Don't clear trips data - let AITravelChat fetch from backend and merge
          // The backend is the source of truth, frontend will sync automatically
          
          navigateToView("chat");
          return;
        } else {
          // Throw error so LoginPage can handle it (show red border and shake)
          const errorMessage = data.detail || "Login failed";
          throw new Error(errorMessage);
        }
      } catch (e) {
        if (import.meta.env.DEV) {
          console.error("Login failed", e?.message ?? "Unknown error");
        }
        throw e;
      }
    }

    // Default: just show login screen
    if (view !== "login") navigateToView("login");
  };

  const handleNavigateToLogin = () => {
    navigateToView("login");
  };

  const handleSignOut = async () => {
    try {
      await fetch(`${API_BASE_URL}/api/auth/logout`, { method: "POST", credentials: "include" });
    } catch (e) {}
    
    // ✅ SECURITY: Clear ALL user data and state using utility function
    clearAllUserData();
    setIsLoggedIn(false);
    setUser(null);
    setNotificationCount(0);
    setNotifications([]);
    
    // Clear any other cached data
    navigateToView("home");
  };

  const postIdTokenToBackend = async (idToken) => {
    try {
      const res = await fetch(`${API_BASE_URL}/api/auth/google`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        credentials: "include",
        body: JSON.stringify({ id_token: idToken }),
      });
      
      // ✅ Check if response is ok
      if (!res.ok) {
        const errorData = await res.json().catch(() => ({ detail: `HTTP ${res.status}: ${res.statusText}` }));
        throw new Error(errorData.detail || `Google login failed: ${res.status} ${res.statusText}`);
      }
      
      const data = await res.json();
      if (!data?.ok || !data?.user) {
        throw new Error(data?.detail || "Login failed: Invalid response from server");
      }
      
      // ✅ SECURITY: Clear ALL previous user data before setting new user
      clearAllUserData();
      setIsLoggedIn(false);
      setUser(null);
      setNotificationCount(0);
      setNotifications([]);
      
      // Set new user data — ใช้ user_id เป็น id หลัก; ถ้า backend ไม่ส่งรูปแต่ id_token มี picture ให้ดึงมาใช้
      let userData = { ...data.user, id: data.user.user_id || data.user.id };
      if (!userData.profile_image && !userData.picture && idToken) {
        try {
          const payload = JSON.parse(decodeURIComponent(escape(atob(idToken.split('.')[1]))));
          const picture = payload.picture || payload.picture_url || payload.photoURL;
          if (picture) {
            userData = { ...userData, profile_image: picture };
            await fetch(`${API_BASE_URL}/api/auth/profile`, {
              method: "PUT",
              headers: { "Content-Type": "application/json", ...(userData.id && { "X-User-ID": userData.id }) },
              credentials: "include",
              body: JSON.stringify({ profile_image: picture }),
            }).catch(() => {});
          }
        } catch (_) { /* ignore decode errors */ }
      }
      setIsLoggedIn(true);
      setUser(userData);
      // Save to localStorage for persistent login
      localStorage.setItem("is_logged_in", "true");
      localStorage.setItem("user_data", JSON.stringify(userData));
      localStorage.setItem("session_timestamp", Date.now().toString());
      
      // Check if profile is complete, if not redirect to profile edit
      if (!hasRequiredProfileInfo(userData)) {
        navigateToView("profile");
      } else {
        navigateToView("chat");
      }
    } catch (e) {
      console.error("Error posting ID token to backend:", e);
      const errorMessage = e?.message || String(e);
      
      // ✅ Provide helpful error messages
      if (errorMessage.includes("Invalid token") || errorMessage.includes("Invalid Google token")) {
        throw new Error("Google token verification failed. Please try logging in again.");
      } else if (errorMessage.includes("not configured") || errorMessage.includes("GOOGLE_CLIENT_ID")) {
        throw new Error("Google login is not configured on the server. Please contact administrator.");
      } else {
        throw new Error(`Google login failed: ${errorMessage}`);
      }
    }
  };

  // ---- Google Login (GIS) ----
  const waitForGoogleScript = () => {
    return new Promise((resolve, reject) => {
      // Check if already loaded
      if (window.google?.accounts?.id) {
        return resolve();
      }

      // Wait for script to load (max 10 seconds)
      const maxWait = 10000;
      const startTime = Date.now();
      const checkInterval = setInterval(() => {
        if (window.google?.accounts?.id) {
          clearInterval(checkInterval);
          resolve();
        } else if (Date.now() - startTime > maxWait) {
          clearInterval(checkInterval);
          reject(new Error("Google Identity Services script failed to load within 10 seconds"));
        }
      }, 100);
    });
  };

  const ensureGoogleInitialized = async () => {
    if (googleInitRef.current) return;
    if (!GOOGLE_CLIENT_ID) {
      throw new Error("Missing VITE_GOOGLE_CLIENT_ID in frontend/.env");
    }
    
    // Wait for Google script to load
    await waitForGoogleScript();
    
    if (!window.google?.accounts?.id) {
      throw new Error(
        "Google Identity Services not loaded. Check index.html includes https://accounts.google.com/gsi/client"
      );
    }
    window.google.accounts.id.initialize({
      client_id: GOOGLE_CLIENT_ID,
      callback: () => {}, // we attach callback per-prompt to get a fresh Promise
      auto_select: false,
      cancel_on_tap_outside: false,
      use_fedcm: true, // ✅ Enable FedCM migration (required for future compatibility)
    });
    googleInitRef.current = true;
  };

  const getGoogleIdTokenViaPrompt = async () => {
    await ensureGoogleInitialized();

    return await new Promise((resolve, reject) => {
      let resolved = false;
      const timeout = setTimeout(() => {
        if (!resolved) {
          resolved = true;
          reject(new Error("Google sign-in timeout. Please try again."));
        }
      }, 60000); // 60 second timeout

      // ✅ Initialize with callback and FedCM support
      window.google.accounts.id.initialize({
        client_id: GOOGLE_CLIENT_ID,
        callback: (resp) => {
          if (resolved) return;
          resolved = true;
          clearTimeout(timeout);
          
          if (resp?.credential) {
            console.log("✅ Google ID token received successfully");
            return resolve(resp.credential);
          }
          return reject(new Error("No credential returned from Google"));
        },
        auto_select: false,
        cancel_on_tap_outside: false,
        use_fedcm: true, // ✅ Enable FedCM migration
      });

      // ✅ Use prompt method with FedCM-compatible event handling
      try {
        window.google.accounts.id.prompt((notification) => {
          if (resolved) return;
          
          // ✅ FedCM-compatible: Use displayMoment event instead of isNotDisplayed
          if (notification.getMomentType?.() === "display") {
            // Display moment - prompt is shown (FedCM compatible)
            console.log("Google prompt displayed");
            // Don't resolve here - wait for user interaction
            return;
          }
          
          // ✅ Legacy support: Check isNotDisplayed for non-FedCM browsers
          if (notification.isNotDisplayed?.()) {
            const reason = notification.getNotDisplayedReason?.();
            console.warn("Google prompt not displayed:", reason);
            
            clearTimeout(timeout);
            resolved = true;
            
            if (reason === "browser_not_supported" || reason === "invalid_client") {
              return reject(
                new Error(
                  `Google sign-in not available: ${reason}. Please check your Google Client ID configuration and ensure your origin is registered in Google Cloud Console.`
                )
              );
            }
            
            // For other reasons, provide helpful error message
            return reject(
              new Error(
                `Google sign-in not displayed: ${reason || "unknown"}. Try enabling third-party cookies or check browser settings.`
              )
            );
          }
          
          // ✅ FedCM-compatible: Use skippedMoment event
          if (notification.getMomentType?.() === "skipped") {
            const reason = notification.getSkippedReason?.();
            console.warn("Google prompt skipped:", reason);
            clearTimeout(timeout);
            resolved = true;
            return reject(
              new Error(
                `Google sign-in skipped: ${reason || "unknown"}. Please try clicking the button again.`
              )
            );
          }
          
          // ✅ Legacy support: Check isSkippedMoment for non-FedCM browsers
          if (notification.isSkippedMoment?.()) {
            const reason = notification.getSkippedReason?.();
            console.warn("Google prompt skipped:", reason);
            clearTimeout(timeout);
            resolved = true;
            return reject(
              new Error(
                `Google sign-in skipped: ${reason || "unknown"}. Please try clicking the button again.`
              )
            );
          }
          
          // ✅ Legacy support: Check isDismissedMoment for non-FedCM browsers
          if (notification.isDismissedMoment?.()) {
            const reason = notification.getDismissedReason?.();
            console.warn("Google prompt dismissed:", reason);
            clearTimeout(timeout);
            resolved = true;
            return reject(
              new Error(
                `Google sign-in dismissed: ${reason || "unknown"}. Please try again.`
              )
            );
          }
        });
      } catch (promptError) {
        if (!resolved) {
          resolved = true;
          clearTimeout(timeout);
          reject(new Error(`Failed to show Google sign-in prompt: ${promptError.message || "Unknown error"}`));
        }
      }
    });
  };

  // ✅ Improved Google login using One Tap + Button fallback
  const getGoogleIdTokenViaOneTap = async () => {
    await ensureGoogleInitialized();

    return await new Promise((resolve, reject) => {
      let resolved = false;
      const timeout = setTimeout(() => {
        if (!resolved) {
          resolved = true;
          reject(new Error("Google sign-in timeout. Please try clicking the button again."));
        }
      }, 30000); // 30 second timeout

      // ✅ Initialize with callback and FedCM support
      window.google.accounts.id.initialize({
        client_id: GOOGLE_CLIENT_ID,
        callback: (resp) => {
          if (resolved) return;
          resolved = true;
          clearTimeout(timeout);
          
          if (resp?.credential) {
            console.log("✅ Google ID token received successfully");
            return resolve(resp.credential);
          }
          return reject(new Error("No credential returned from Google"));
        },
        auto_select: false,
        cancel_on_tap_outside: false,
        use_fedcm: true, // ✅ Enable FedCM migration
      });

      // ✅ Try One Tap first (better UX) with FedCM-compatible event handling
      window.google.accounts.id.prompt((notification) => {
        if (resolved) return;
        
        // ✅ FedCM-compatible: Use displayMoment event
        if (notification.getMomentType?.() === "display") {
          console.log("One Tap displayed");
          // Don't resolve - wait for user interaction
          return;
        }
        
        // ✅ Legacy support: Check isNotDisplayed for non-FedCM browsers
        if (notification.isNotDisplayed?.()) {
          const reason = notification.getNotDisplayedReason?.();
          console.log("One Tap not displayed, reason:", reason);
          
          // ✅ If One Tap fails, user can still use the button (don't reject here)
          // The button will handle the sign-in
          if (reason === "browser_not_supported" || reason === "invalid_client") {
            clearTimeout(timeout);
            resolved = true;
            return reject(
              new Error(
                `Google sign-in not available: ${reason}. Please check your Google Client ID configuration.`
              )
            );
          }
          
          // For other reasons, don't reject - let button handle it
          console.log("One Tap not available, will use button method");
          return;
        }
        
        // ✅ FedCM-compatible: Use skippedMoment event
        if (notification.getMomentType?.() === "skipped") {
          const reason = notification.getSkippedReason?.();
          console.log("One Tap skipped:", reason);
          // Don't reject - user can use button
          return;
        }
        
        // ✅ Legacy support: Check isSkippedMoment for non-FedCM browsers
        if (notification.isSkippedMoment?.()) {
          const reason = notification.getSkippedReason?.();
          console.log("One Tap skipped:", reason);
          // Don't reject - user can use button
          return;
        }
        
        // ✅ Legacy support: Check isDismissedMoment for non-FedCM browsers
        if (notification.isDismissedMoment?.()) {
          const reason = notification.getDismissedReason?.();
          console.log("One Tap dismissed:", reason);
          // Don't reject - user can use button
          return;
        }
      });
    });
  };

  // This is what LoginPage's "Login with Google" button calls (no args)
  // Firebase Google Sign-In handler
  const handleFirebaseGoogleLogin = async () => {
    try {
      // Dynamic import Firebase config to avoid loading if not needed
      const { auth, googleProvider, signInWithPopup } = await import('./config/firebase.js');
      
      if (!auth || !googleProvider || !signInWithPopup) {
        throw new Error("Firebase is not configured. Please contact administrator.");
      }
      
      // Sign in with Google popup
      const result = await signInWithPopup(auth, googleProvider);
      const user = result.user;
      
      // Get ID token
      const idToken = await user.getIdToken();
      
      // Send to backend Firebase endpoint
      const res = await fetch(`${API_BASE_URL}/api/auth/firebase`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        credentials: "include",
        body: JSON.stringify({ idToken }),
      });
      
      if (!res.ok) {
        const errorData = await res.json().catch(() => ({ detail: `HTTP ${res.status}: ${res.statusText}` }));
        throw new Error(errorData.detail || `Firebase login failed: ${res.status} ${res.statusText}`);
      }
      
      const data = await res.json();
      if (!data?.ok || !data?.user) {
        throw new Error(data?.detail || "Login failed: Invalid response from server");
      }
      
      // Clear previous user data
      clearAllUserData();
      setIsLoggedIn(false);
      setUser(null);
      setNotificationCount(0);
      setNotifications([]);
      
      // Set new user data — ถ้า backend ไม่ส่งรูปแต่ Firebase มี photoURL ให้ใช้และบันทึกลง backend
      const photoURL = result.user?.photoURL || result.user?.photoUrl;
      let userData = { ...data.user, id: data.user.user_id || data.user.id };
      if (photoURL && !userData.profile_image && !userData.picture) {
        userData = { ...userData, profile_image: photoURL };
        try {
          await fetch(`${API_BASE_URL}/api/auth/profile`, {
            method: "PUT",
            headers: { "Content-Type": "application/json", ...(userData.id && { "X-User-ID": userData.id }) },
            credentials: "include",
            body: JSON.stringify({ profile_image: photoURL }),
          });
        } catch (_) { /* ignore */ }
      }
      setUser(userData);
      localStorage.setItem("is_logged_in", "true");
      localStorage.setItem("user_data", JSON.stringify(userData));
      localStorage.setItem("session_timestamp", Date.now().toString());
      
      // Check if profile is complete
      if (!hasRequiredProfileInfo(userData)) {
        navigateToView("profile");
      } else {
        navigateToView("chat");
      }
    } catch (e) {
      console.error("Firebase Google login error:", e);
      const errorMessage = e?.message || String(e);
      
      if (errorMessage.includes("not configured") || errorMessage.includes("Firebase")) {
        throw new Error("Firebase authentication is not configured. Please contact administrator.");
      } else if (errorMessage.includes("popup") || errorMessage.includes("cancelled")) {
        throw new Error("Sign-in was cancelled. Please try again.");
      } else {
        throw new Error(`Firebase login failed: ${errorMessage}`);
      }
    }
  };

  const handleGoogleLoginClick = async () => {
    try {
      // ✅ Try Firebase first if enabled, fallback to Google OAuth
      if (FIREBASE_ENABLED) {
        try {
          console.log("Trying Firebase Google Sign-In...");
          await handleFirebaseGoogleLogin();
          return; // Success, exit early
        } catch (firebaseError) {
          console.warn("Firebase login failed, trying Google OAuth:", firebaseError);
          // Fall through to Google OAuth as fallback
        }
      }
      
      // ✅ Fallback to Google OAuth (original implementation)
      // Check if GOOGLE_CLIENT_ID is set
      if (!GOOGLE_CLIENT_ID) {
        throw new Error("VITE_GOOGLE_CLIENT_ID ไม่ได้ตั้งค่าในไฟล์ .env\n\nกรุณาเพิ่ม VITE_GOOGLE_CLIENT_ID=your-client-id ในไฟล์ frontend/.env");
      }

      // Get current origin for debugging
      const currentOrigin = window.location.origin;
      console.log("Starting Google OAuth login...", { 
        hasClientId: !!GOOGLE_CLIENT_ID,
        currentOrigin: currentOrigin,
        clientId: GOOGLE_CLIENT_ID.substring(0, 20) + "..."
      });
      
      // ✅ Try One Tap first, fallback to button method
      let idToken;
      try {
        idToken = await getGoogleIdTokenViaOneTap();
      } catch (oneTapError) {
        // If One Tap fails, use button method
        console.log("One Tap failed, using button method:", oneTapError);
        try {
          idToken = await getGoogleIdTokenViaPrompt();
        } catch (promptError) {
          // If both methods fail, provide helpful error
          console.error("Both One Tap and Prompt methods failed:", { oneTapError, promptError });
          throw new Error(
            `Google sign-in failed: ${promptError.message || oneTapError.message || "Unknown error"}. ` +
            `Please check that:\n` +
            `1. VITE_GOOGLE_CLIENT_ID is set in frontend/.env\n` +
            `2. Your origin (${currentOrigin}) is registered in Google Cloud Console\n` +
            `3. Third-party cookies are enabled in your browser`
          );
        }
      }
      
      console.log("Got Google ID token, sending to backend...");
      await postIdTokenToBackend(idToken);
    } catch (e) {
      console.error("Google login failed:", e);
      const errorMessage = e?.message || String(e);
      const currentOrigin = window.location.origin;
      
      let userMessage = `Google login ไม่สำเร็จ: ${errorMessage}`;
      
      // Add helpful tips based on error type
      if (errorMessage.includes("not loaded") || errorMessage.includes("failed to load")) {
        userMessage += "\n\nทิป:\n";
        userMessage += "1. ตรวจสอบว่าเปิด third-party cookies ในเบราว์เซอร์\n";
        userMessage += "2. ลองปิด adblock ชั่วคราว\n";
        userMessage += "3. ลองรีเฟรชหน้าเว็บ (F5)\n";
        userMessage += "4. ตรวจสอบ Console (F12) สำหรับ error เพิ่มเติม";
      } else if (errorMessage.includes("VITE_GOOGLE_CLIENT_ID")) {
        userMessage += "\n\nทิป:\n";
        userMessage += "1. ตรวจสอบไฟล์ frontend/.env มี VITE_GOOGLE_CLIENT_ID\n";
        userMessage += "2. รีสตาร์ท dev server (npm run dev) หลังจากแก้ไข .env";
      } else if (errorMessage.includes("not available") || errorMessage.includes("invalid_client") || errorMessage.includes("unregistered_origin") || errorMessage.includes("unknown_reason")) {
        userMessage += "\n\n⚠️ ปัญหา: Origin ไม่ได้ลงทะเบียนใน Google Cloud Console\n\n";
        userMessage += "📋 ขั้นตอนแก้ไข:\n";
        userMessage += "1. ไปที่: https://console.cloud.google.com/apis/credentials\n";
        userMessage += "2. เลือกโปรเจกต์ของคุณ\n";
        userMessage += "3. คลิก OAuth 2.0 Client ID ที่มี Client ID: " + GOOGLE_CLIENT_ID.substring(0, 20) + "...\n";
        userMessage += "4. ในส่วน 'Authorized JavaScript origins' ให้เพิ่ม:\n";
        userMessage += `   ✅ ${currentOrigin}\n`;
        if (currentOrigin.includes("localhost")) {
          userMessage += "   ✅ http://localhost:5173\n";
          userMessage += "   ✅ http://localhost:8000 (ถ้ามี)\n";
        }
        userMessage += "5. คลิก 'SAVE' ที่ด้านล่าง\n";
        userMessage += "6. รอ 1-2 นาทีให้การเปลี่ยนแปลงมีผล\n";
        userMessage += "7. รีเฟรชหน้าเว็บ (F5) แล้วลองใหม่\n\n";
        userMessage += `📍 Origin ปัจจุบัน: ${currentOrigin}`;
      }
      
      alert(userMessage);
    }
  };

  const handleGetStarted = (promptOrQuery = "") => {
    const q = (promptOrQuery || "").toString();
    if (!isLoggedIn) {
      setPendingPrompt(q);
      navigateToView("login");
      return;
    }
    setPendingPrompt(q);
    navigateToView("chat");
  };

  const handleLoginSuccess = async () => {
    await refreshMe();
    // refreshMe will check profile and redirect if needed
  };

  const handleSaveProfile = async (profileData) => {
    try {
      const res = await fetch(`${API_BASE_URL}/api/auth/profile`, {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        credentials: "include",
        body: JSON.stringify(profileData),
      });
      const data = await res.json();
      if (!data?.ok) {
        throw new Error(data?.detail || "Failed to save profile");
      }
      // ✅ Update user state with new profile data (including profile_image and address)
      const updatedUser = { ...user, ...data.user };
      setUser(updatedUser);
      
      // ✅ Update localStorage to persist profile (image, address, etc.)
      localStorage.setItem("user_data", JSON.stringify(updatedUser));
      
      // ✅ ไม่ redirect ไปหน้า Agent — ให้อยู่หน้าแก้ไขโปรไฟล์ต่อ (SweetAlert แสดง "บันทึกสำเร็จ" แล้วผู้ใช้กดตกลงอยู่หน้าเดิม)
    } catch (error) {
      throw error;
    }
  };

  const handleCancelProfile = () => {
    // If user cancels and doesn't have required info, they can't proceed
    // But we'll let them go to chat anyway (they can edit later)
    if (hasRequiredProfileInfo(user)) {
      navigateToView("chat");
    } else {
      // Still allow them to proceed, but warn them
      navigateToView("chat");
    }
  };

  const handleNavigateToProfile = () => {
    navigateToView("profile");
  };

  const handleNavigateToSettings = () => {
    navigateToView("settings");
  };

  if (isAuthChecking) {
    return (
      <div style={{ 
        display: 'flex', 
        flexDirection: 'column',
        justifyContent: 'center', 
        alignItems: 'center', 
        height: '100vh', 
        background: 'linear-gradient(to bottom right, #eff6ff, #ecfeff)',
        gap: '20px'
      }}>
        {loadingData ? (
          <Lottie 
            animationData={loadingData}
            style={{ width: 237, height: 237 }}
            loop={true}
            autoplay={true}
          />
        ) : (
          <div style={{ width: 237, height: 237, display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
            <div style={{ fontSize: '3rem' }}>⏳</div>
          </div>
        )}
      </div>
    );
  }

  return (
    <LanguageProvider user={user}>
    <ThemeProvider user={user}>
    <FontSizeProvider user={user}>
    <div>
      {view === "home" && (
        <HomePage
          isLoggedIn={isLoggedIn}
          user={user}
          onSignIn={handleNavigateToLogin}
          onSignOut={handleSignOut}
          onGetStarted={handleGetStarted}
          onNavigateToHome={() => navigateToView("home")}
        />
      )}

      {view === "login" && (
        <LoginPage
          onLogin={handleSignIn}
          onGoogleLogin={handleGoogleLoginClick}
          onNavigateToRegister={() => navigateToView("register")}
          onNavigateToResetPassword={() => navigateToView("reset-password")}
          onNavigateToHome={() => navigateToView("home")}
        />
      )}

      {view === "reset-password" && (
        <ResetPasswordPage
          onNavigateToLogin={() => navigateToView("login")}
          onNavigateToHome={() => navigateToView("home")}
          onNavigateToRegister={() => navigateToView("register")}
        />
      )}

      {view === "verify-email-change" && (
        <VerifyEmailChangePage
          onNavigateToHome={() => navigateToView("home")}
          onNavigateToSettings={() => navigateToView("settings")}
        />
      )}

      {view === "chat" && isLoggedIn && (
        <Suspense
          fallback={
            <div className="chat-loading-fallback" style={{
              display: 'flex',
              flexDirection: 'column',
              alignItems: 'center',
              justifyContent: 'center',
              minHeight: '60vh',
              gap: '16px',
              color: 'var(--text-primary, #1f2937)',
            }}>
              <div style={{
                width: 40,
                height: 40,
                border: '3px solid #e5e7eb',
                borderTopColor: '#2563eb',
                borderRadius: '50%',
                animation: 'chat-loading-spin 0.7s linear infinite',
              }} />
              <p style={{ margin: 0, fontSize: '1rem' }}>กำลังโหลดเอเย่นต์...</p>
            </div>
          }
        >
          <AITravelChat 
            user={user} 
            onLogout={handleSignOut} 
            onSignIn={handleNavigateToLogin}
            initialPrompt={pendingPrompt}
            onNavigateToBookings={() => navigateToView("bookings")}
            onNavigateToFlights={() => navigateToView("flights")}
            onNavigateToHotels={() => navigateToView("hotels")}
            onNavigateToCarRentals={() => navigateToView("car-rentals")}
            onNavigateToProfile={handleNavigateToProfile}
            onNavigateToSettings={handleNavigateToSettings}
            onNavigateToHome={() => navigateToView("home")}
            onRefreshNotifications={fetchNotificationCount}
            notificationCount={notificationCount}
            notifications={notifications}
            onMarkNotificationAsRead={handleMarkNotificationAsRead}
            onClearAllNotifications={handleMarkAllNotificationsAsRead}
          />
        </Suspense>
      )}


      {view === "profile" && isLoggedIn && (
        <UserProfileEditPage
          user={user}
          onSave={handleSaveProfile}
          onCancel={handleCancelProfile}
          onNavigateToHome={goHome}
          onNavigateToBookings={() => navigateToView("bookings")}
          onNavigateToAI={() => navigateToView("chat")}
          onNavigateToFlights={() => navigateToView("flights")}
          onNavigateToHotels={() => navigateToView("hotels")}
          onNavigateToCarRentals={() => navigateToView("car-rentals")}
          onLogout={handleSignOut}
          onNavigateToProfile={handleNavigateToProfile}
          onNavigateToSettings={handleNavigateToSettings}
          notificationCount={notificationCount}
          notifications={notifications}
          onMarkNotificationAsRead={handleMarkNotificationAsRead}
          onClearAllNotifications={handleMarkAllNotificationsAsRead}
          onRefreshUser={refreshMe}
        />
      )}

      {view === "register" && (
        <RegisterPage
          onRegister={handleRegister}
          onNavigateToLogin={() => navigateToView("login")}
          onGoogleLogin={handleGoogleLoginClick}
          onNavigateToHome={() => navigateToView("home")}
        />
      )}

      {view === "bookings" && isLoggedIn && (
        <MyBookingsPage
          key={`bookings-${user?.id || user?.user_id || 'anonymous'}`}
          user={user}
          isActive={true}
          onBack={() => setView("chat")}
          onLogout={handleSignOut}
          onSignIn={handleNavigateToLogin}
          onNavigateToProfile={handleNavigateToProfile}
          onNavigateToSettings={handleNavigateToSettings}
          onNavigateToHome={() => navigateToView("home")}
          onNavigateToPayment={(bookingId) => {
            if (window.history && window.history.pushState) {
              window.history.pushState({}, '', `/payment?booking_id=${bookingId}`);
            }
            navigateToView("payment");
          }}
          onNavigateToAI={(tripId, chatId, initialMessage) => {
            // Navigate to chat and set initial message
            if (initialMessage) {
              setPendingPrompt(initialMessage);
            }
            // ✅ Store trip_id and chat_id for chat to use (using correct key from AITravelChat)
            const LS_ACTIVE_TRIP_KEY = 'ai_travel_active_trip_id_v1';
            if (chatId) {
              localStorage.setItem(LS_ACTIVE_TRIP_KEY, chatId); // ✅ ใช้ chatId เป็น activeTripId
            } else if (tripId) {
              localStorage.setItem(LS_ACTIVE_TRIP_KEY, tripId);
            }
            navigateToView("chat");
          }}
          notificationCount={notificationCount}
          notifications={notifications}
          onMarkNotificationAsRead={handleMarkNotificationAsRead}
          onClearAllNotifications={handleMarkAllNotificationsAsRead}
        />
      )}

      {view === "payment" && isLoggedIn && (() => {
        // Extract booking_id from URL query params
        const urlParams = new URLSearchParams(window.location.search);
        const bookingId = urlParams.get('booking_id') || urlParams.get('id');
        
        return (
          <PaymentPage
            bookingId={bookingId}
            user={user}
            onBack={() => navigateToView("bookings")}
            onPaymentSuccess={(bookingId, chargeData) => {
              navigateToView("bookings");
              setTimeout(() => {
                Swal.fire({
                  icon: 'success',
                  title: 'ชำระเงินสำเร็จ',
                  text: 'การชำระเงินของคุณดำเนินการเรียบร้อยแล้ว คุณสามารถดูรายการจองได้ที่ My Bookings',
                  confirmButtonText: 'ตกลง',
                  confirmButtonColor: '#2563eb'
                });
              }, 400);
            }}
            onNavigateToHome={() => navigateToView("home")}
            onNavigateToProfile={handleNavigateToProfile}
            onNavigateToSettings={handleNavigateToSettings}
            onLogout={handleSignOut}
            onSignIn={handleNavigateToLogin}
          />
        );
      })()}

      {view === "flights" && isLoggedIn && (
        <FlightsPage
          user={user}
          onLogout={handleSignOut}
          onSignIn={handleNavigateToLogin}
          onNavigateToBookings={() => setView("bookings")}
          onNavigateToAI={() => navigateToView("chat")}
          onNavigateToFlights={() => navigateToView("flights")}
          onNavigateToHotels={() => navigateToView("hotels")}
          onNavigateToCarRentals={() => navigateToView("car-rentals")}
          onNavigateToHome={() => navigateToView("home")}
          onNavigateToProfile={handleNavigateToProfile}
          onNavigateToSettings={handleNavigateToSettings}
          notificationCount={notificationCount}
          notifications={notifications}
          onMarkNotificationAsRead={handleMarkNotificationAsRead}
          onClearAllNotifications={handleMarkAllNotificationsAsRead}
        />
      )}

      {view === "hotels" && isLoggedIn && (
        <HotelsPage
          user={user}
          onLogout={handleSignOut}
          onSignIn={handleNavigateToLogin}
          onNavigateToBookings={() => setView("bookings")}
          onNavigateToAI={() => setView("chat")}
          onNavigateToFlights={() => setView("flights")}
          onNavigateToHotels={() => navigateToView("hotels")}
          onNavigateToCarRentals={() => setView("car-rentals")}
          onNavigateToHome={() => navigateToView("home")}
          onNavigateToProfile={handleNavigateToProfile}
          onNavigateToSettings={handleNavigateToSettings}
          notificationCount={notificationCount}
          notifications={notifications}
          onMarkNotificationAsRead={handleMarkNotificationAsRead}
          onClearAllNotifications={handleMarkAllNotificationsAsRead}
        />
      )}

      {view === "car-rentals" && isLoggedIn && (
        <CarRentalsPage
          user={user}
          onLogout={handleSignOut}
          onSignIn={handleNavigateToLogin}
          onNavigateToBookings={() => setView("bookings")}
          onNavigateToAI={() => navigateToView("chat")}
          onNavigateToFlights={() => navigateToView("flights")}
          onNavigateToHotels={() => navigateToView("hotels")}
          onNavigateToCarRentals={() => navigateToView("car-rentals")}
          onNavigateToProfile={handleNavigateToProfile}
          onNavigateToSettings={handleNavigateToSettings}
          onNavigateToHome={() => navigateToView("home")}
          notificationCount={notificationCount}
          notifications={notifications}
          onMarkNotificationAsRead={handleMarkNotificationAsRead}
          onClearAllNotifications={handleMarkAllNotificationsAsRead}
        />
      )}

      {view === "settings" && isLoggedIn && (
        <SettingsPage
          user={user}
          onLogout={handleSignOut}
          onNavigateToHome={() => navigateToView("home")}
          onNavigateToProfile={handleNavigateToProfile}
          onNavigateToBookings={() => navigateToView("bookings")}
          onNavigateToAI={() => navigateToView("chat")}
          onNavigateToFlights={() => navigateToView("flights")}
          onNavigateToHotels={() => navigateToView("hotels")}
          onNavigateToCarRentals={() => navigateToView("car-rentals")}
          notificationCount={notificationCount}
          notifications={notifications}
          onMarkNotificationAsRead={handleMarkNotificationAsRead}
          onClearAllNotifications={handleMarkAllNotificationsAsRead}
          onSendVerificationEmailSuccess={(email) => {
            const emailDisplay = email || user?.email || "อีเมลของคุณ";
            const html = `
              <p style="color:#6366f1; font-weight:600; margin:0 0 1rem; word-break:break-all;">${emailDisplay}</p>
              <p style="color:#4b5563; margin:0 0 0.75rem; line-height:1.6;">
                เราได้ส่งลิงก์ยืนยันอีเมลไปที่กล่องจดหมายของคุณแล้ว<br/>
                กรุณาคลิกปุ่ม <strong>「ยืนยันอีเมล」</strong> ในอีเมลเพื่อดำเนินการต่อ
              </p>
              <p style="color:#9ca3af; font-size:0.9rem; margin:0;">ไม่พบอีเมล? ตรวจสอบโฟลเดอร์ Spam หรือ Junk</p>
            `;
            Swal.fire({
              icon: 'info',
              title: 'กรุณาตรวจสอบอีเมล',
              html,
              showConfirmButton: true,
              confirmButtonText: 'ตกลง',
              confirmButtonColor: '#6366f1',
              allowOutsideClick: true,
              allowEscapeKey: true,
            });
          }}
          onUpdateEmailSuccess={(email) => {
            const emailDisplay = email || "อีเมลของคุณ";
            const html = `
              <p style="color:#6366f1; font-weight:600; margin:0 0 1rem; word-break:break-all;">${emailDisplay}</p>
              <p style="color:#4b5563; margin:0 0 0.75rem; line-height:1.6;">
                เราได้ส่งลิงก์ยืนยันอีเมลไปที่กล่องจดหมายของคุณแล้ว<br/>
                กรุณาคลิกปุ่ม <strong>「ยืนยันอีเมล」</strong> ในอีเมลเพื่อดำเนินการต่อ
              </p>
              <p style="color:#9ca3af; font-size:0.9rem; margin:0;">ไม่พบอีเมล? ตรวจสอบโฟลเดอร์ Spam หรือ Junk</p>
            `;
            Swal.fire({
              icon: 'info',
              title: 'กรุณาตรวจสอบอีเมล',
              html,
              showConfirmButton: true,
              confirmButtonText: 'ตกลง',
              confirmButtonColor: '#6366f1',
              allowOutsideClick: true,
              allowEscapeKey: true,
            });
          }}
          onRefreshUser={async () => {
            // Refresh user data
            try {
              const res = await fetch(`${API_BASE_URL}/api/auth/me`, {
                credentials: 'include',
              });
              if (res.ok) {
                const data = await res.json();
                if (data.user) {
                  setUser(data.user);
                  localStorage.setItem("user_data", JSON.stringify(data.user));
                }
              }
            } catch (error) {
              console.error("Failed to refresh user:", error);
            }
          }}
        />
      )}
    </div>
    </FontSizeProvider>
    </ThemeProvider>
    </LanguageProvider>
  );
}

export default App;
