import React, { useEffect, useState, useCallback, useRef } from "react";
import LoginPage from "./pages/auth/LoginPage.jsx";
import RegisterPage from "./pages/auth/RegisterPage.jsx";
import ResetPasswordPage from "./pages/auth/ResetPasswordPage.jsx";
import AITravelChat from "./pages/chat/AITravelChat.jsx";
import HomePage from "./pages/home/HomePage.jsx";
import UserProfileEditPage from "./pages/profile/UserProfileEditPage.jsx";
import MyBookingsPage from "./pages/bookings/MyBookingsPage.jsx";
import PaymentPage from "./pages/bookings/PaymentPage.jsx";
import FlightsPage from "./pages/search/FlightsPage.jsx";
import HotelsPage from "./pages/search/HotelsPage.jsx";
import CarRentalsPage from "./pages/search/CarRentalsPage.jsx";
import Lottie from "lottie-react";
import loadingAnimation from "./assets/loading.json";
import { clearAllUserData, checkAndClearIfUserChanged } from "./utils/userDataManager.js";

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || "http://localhost:8000";
const GOOGLE_CLIENT_ID = import.meta.env.VITE_GOOGLE_CLIENT_ID || "";

// URL path mapping
const VIEW_PATHS = {
  'home': '/',
  'login': '/login',
  'register': '/register',
  'reset-password': '/reset-password',
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

// Get view from URL path
function getViewFromPath() {
  const path = window.location.pathname;
  // Check for payment page with booking_id
  if (path.startsWith('/payment') || path.includes('/payment')) {
    return 'payment';
  }
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
    return savedView || "home";
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
      if (diffMins < 60) return `${diffMins} นาทีที่แล้ว`;
      if (diffHours < 24) return `${diffHours} ชั่วโมงที่แล้ว`;
      if (diffDays < 7) return `${diffDays} วันที่แล้ว`;
      
      return date.toLocaleDateString('th-TH', { 
        year: 'numeric', 
        month: 'short', 
        day: 'numeric' 
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
      if (user?.id) {
        headers['X-User-ID'] = user.id;
      }
      
      // ✅ Fetch from notification API
      const res = await fetch(`${API_BASE_URL}/api/notification/list`, {
        headers,
        credentials: 'include',
      });
      const data = await res.json();
      
      if (data.ok && Array.isArray(data.notifications)) {
        setNotificationCount(data.unread_count || 0);
        
        // ✅ Map notifications to frontend format
        const notificationsList = data.notifications.map((notif) => {
          return {
            id: notif.id,
            type: notif.type === 'booking_created' ? 'task' : 'info',
            title: notif.title || 'แจ้งเตือน',
            message: notif.message || '',
            time: formatNotificationDate(notif.created_at),
            isRead: notif.read || false,
            bookingId: notif.booking_id,
            metadata: notif.metadata || {}
          };
        });
        
        setNotifications(notificationsList);
      } else {
        setNotificationCount(0);
        setNotifications([]);
      }
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
      if (user?.id) {
        headers['X-User-ID'] = user.id;
      }
      
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

  // Fetch notifications on mount and when user/view changes
  useEffect(() => {
    if (isLoggedIn) {
      fetchNotificationCount();
      // Optional: Polling every minute
      const interval = setInterval(fetchNotificationCount, 60000);
      return () => clearInterval(interval);
    } else {
      setNotificationCount(0);
      setNotifications([]);
    }
  }, [isLoggedIn, user, fetchNotificationCount, view]);

  // Sync view with URL and browser history
  const navigateToView = useCallback((newView, replace = false) => {
    const path = getPathFromView(newView);
    const currentPath = window.location.pathname;
    
    if (path !== currentPath) {
      if (replace) {
        window.history.replaceState({ view: newView }, '', path);
      } else {
        window.history.pushState({ view: newView }, '', path);
      }
    }
    
    setView(newView);
    
    // Save view to localStorage (but not login/register pages)
    if (newView !== 'login' && newView !== 'register' && newView !== 'reset-password') {
      localStorage.setItem("app_view", newView);
    }
  }, []);

  // Handle browser back/forward buttons
  useEffect(() => {
    const handlePopState = (event) => {
      const newView = event.state?.view || getViewFromPath();
      // Use setView directly here (not navigateToView) to avoid pushing new history entry
      setView(newView);
      if (newView !== 'login' && newView !== 'register' && newView !== 'reset-password') {
        localStorage.setItem("app_view", newView);
      }
    };

    window.addEventListener('popstate', handlePopState);
    
    // Initialize URL on mount
    const currentPath = window.location.pathname;
    const currentView = getViewFromPath();
    if (currentView !== view) {
      // URL doesn't match current view, update URL
      window.history.replaceState({ view }, '', getPathFromView(view));
    } else {
      // URL matches, ensure state is set
      window.history.replaceState({ view }, '', currentPath);
    }

    return () => {
      window.removeEventListener('popstate', handlePopState);
    };
  }, [view]); // Re-run when view changes to sync URL

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
        setIsLoggedIn(true);
        setUser(userData);
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
        
        setIsLoggedIn(true);
        setUser(data.user);
        // Save to localStorage with timestamp for persistent login
        localStorage.setItem("is_logged_in", "true");
        localStorage.setItem("user_data", JSON.stringify(data.user));
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
        // Allow 'register' and 'login' views to stay when not logged in
        const currentView = getViewFromPath();
        if (currentView !== 'home' && currentView !== 'login' && currentView !== 'register' && currentView !== 'reset-password') {
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
        // Allow 'register' and 'login' views to stay when not logged in
        const currentView = getViewFromPath();
        if (currentView !== 'home' && currentView !== 'login' && currentView !== 'register' && currentView !== 'reset-password') {
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

  const handleRegister = async (registerData) => {
    try {
      const res = await fetch(`${API_BASE_URL}/api/auth/register`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        credentials: "include",
        body: JSON.stringify(registerData)
      });
      
      // Check if response is ok
      if (!res.ok) {
        const errorData = await res.json().catch(() => ({ detail: `HTTP ${res.status}: ${res.statusText}` }));
        throw new Error(errorData.detail || `Registration failed: ${res.status} ${res.statusText}`);
      }
      
      const data = await res.json();
      if (data.ok) {
        // Don't set login state automatically - user needs to login after registration
        // Don't navigate automatically - let RegisterPage handle the success state and navigation
        // The RegisterPage will show success checkmark and navigate to login after 1.5 seconds
        return data;
      } else {
        throw new Error(data.detail || "Registration failed");
      }
    } catch (e) {
      console.error("Registration failed", e);
      // Re-throw with more detailed error message
      const errorMessage = e?.message || String(e);
      throw new Error(errorMessage);
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

    // 2. Standard Email login
    if (email && email.includes('@')) {
      try {
        const res = await fetch(`${API_BASE_URL}/api/auth/login`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          credentials: "include",
          body: JSON.stringify({ email, password, remember_me: rememberMe })
        });
        
        // ✅ Check if response is ok before parsing JSON
        if (!res.ok) {
          const errorData = await res.json().catch(() => ({ detail: `HTTP ${res.status}: ${res.statusText}` }));
          throw new Error(errorData.detail || `Login failed: ${res.status} ${res.statusText}`);
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
        console.error("Login failed", e);
        // Re-throw error so LoginPage can handle it
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
      
      // Set new user data
      setIsLoggedIn(true);
      const userData = { ...data.user, id: data.user.id };
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
  const handleGoogleLoginClick = async () => {
    try {
      // Check if GOOGLE_CLIENT_ID is set
      if (!GOOGLE_CLIENT_ID) {
        throw new Error("VITE_GOOGLE_CLIENT_ID ไม่ได้ตั้งค่าในไฟล์ .env\n\nกรุณาเพิ่ม VITE_GOOGLE_CLIENT_ID=your-client-id ในไฟล์ frontend/.env");
      }

      // Get current origin for debugging
      const currentOrigin = window.location.origin;
      console.log("Starting Google login...", { 
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
      } else if (errorMessage.includes("not available") || errorMessage.includes("invalid_client") || errorMessage.includes("unregistered_origin")) {
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
      // ✅ Update user state with new profile data (including profile_image)
      const updatedUser = { ...user, ...data.user };
      setUser(updatedUser);
      
      // ✅ Update localStorage to persist profile_image
      localStorage.setItem("user_data", JSON.stringify(updatedUser));
      
      // Redirect to chat
      navigateToView("chat");
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
    // TODO: Create Settings page component
    // For now, we can navigate to profile or show a message
    alert("หน้าตั้งค่าจะเปิดใช้งานเร็วๆ นี้");
    // setView("settings");
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

      {view === "chat" && isLoggedIn && (
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
        />
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
          key={`bookings-${user?.id || 'anonymous'}-${Date.now()}`} // ✅ Force refresh when user changes or time updates
          user={user}
          onBack={() => setView("chat")}
          onLogout={handleSignOut}
          onSignIn={handleNavigateToLogin}
          onNavigateToProfile={handleNavigateToProfile}
          onNavigateToSettings={handleNavigateToSettings}
          onNavigateToHome={() => navigateToView("home")}
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
              // Reload bookings and show success
              navigateToView("bookings");
              // Show success message after a short delay
              setTimeout(() => {
                alert('✅ ชำระเงินสำเร็จ!');
              }, 500);
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
          onNavigateToCarRentals={() => setView("car-rentals")}
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
        />
      )}
    </div>
  );
}

export default App;
