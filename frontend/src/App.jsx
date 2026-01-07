import React, { useEffect, useState, useCallback, useRef } from "react";
import LoginPage from "./components/LoginPage.jsx";
import AITravelChat from "./components/AITravelChat.jsx";
import HomePage from "./components/HomePage.jsx";
import UserProfileEditPage from "./components/UserProfileEditPage.jsx";
import MyBookingsPage from "./components/MyBookingsPage.jsx";
import FlightsPage from "./components/FlightsPage.jsx";
import HotelsPage from "./components/HotelsPage.jsx";
import CarRentalsPage from "./components/CarRentalsPage.jsx";

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || "http://localhost:8000";
const GOOGLE_CLIENT_ID = import.meta.env.VITE_GOOGLE_CLIENT_ID || "";
// Set VITE_AUTH_BYPASS=1 to enable guest mode (bypass auth)
const AUTH_BYPASS = (import.meta.env.VITE_AUTH_BYPASS || "1").toString() === "1";

function App() {
  const [view, setView] = useState("home"); // 'home' | 'login' | 'chat' | 'profile' | 'bookings' | 'profile'
  const [isLoggedIn, setIsLoggedIn] = useState(AUTH_BYPASS);
  const [user, setUser] = useState(AUTH_BYPASS ? { id: "guest", name: "Guest" } : null);
  const [pendingPrompt, setPendingPrompt] = useState("");

  const googleInitRef = useRef(false);

  // Check if user has required profile information
  const hasRequiredProfileInfo = useCallback((userData) => {
    if (!userData || AUTH_BYPASS) return true; // Guest mode always passes
    return !!(
      userData.first_name &&
      userData.last_name &&
      userData.email &&
      userData.phone
    );
  }, []);

  const refreshMe = useCallback(async () => {
    if (AUTH_BYPASS) {
      setIsLoggedIn(true);
      setUser({ id: "guest", name: "Guest" });
      return;
    }
    try {
      const res = await fetch(`${API_BASE_URL}/api/auth/me`, { credentials: "include" });
      const data = await res.json();
      if (data?.user) {
        setIsLoggedIn(true);
        setUser(data.user);
        // Check if profile is complete, if not redirect to profile edit
        if (!hasRequiredProfileInfo(data.user) && view !== "profile") {
          setView("profile");
        }
      } else {
        setIsLoggedIn(false);
        setUser(null);
      }
    } catch (e) {
      // If backend is down or CORS fails, just treat as logged out.
      setIsLoggedIn(false);
      setUser(null);
    }
  }, [hasRequiredProfileInfo, view]);

  useEffect(() => {
    refreshMe();
  }, [refreshMe]);

  const goHome = () => setView("home");

  const handleSignIn = async (email, password) => {
    if (AUTH_BYPASS) {
      setIsLoggedIn(true);
      setUser({ id: "guest", name: "Guest" });
      setView("chat");
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
          setView("chat");
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
          body: JSON.stringify({ email, password })
        });
        const data = await res.json();
        if (data.ok) {
          setIsLoggedIn(true);
          setUser(data.user);
          setView("chat");
          return;
        } else {
          alert(data.detail || "Login failed");
        }
      } catch (e) {
        console.error("Login failed", e);
        alert("Could not connect to server");
      }
    }

    // Default: just show login screen
    if (view !== "login") setView("login");
  };

  const handleSignOut = async () => {
    if (AUTH_BYPASS) {
      setIsLoggedIn(false);
      setUser(null);
      setView("home");
      return;
    }
    try {
      await fetch(`${API_BASE_URL}/api/auth/logout`, { method: "POST", credentials: "include" });
    } catch (e) {}
    setIsLoggedIn(false);
    setUser(null);
    setView("home");
  };

  const postIdTokenToBackend = async (idToken) => {
    if (AUTH_BYPASS) {
      setIsLoggedIn(true);
      setUser({ id: "guest", name: "Guest" });
      setView("chat");
      return;
    }
    const res = await fetch(`${API_BASE_URL}/api/auth/google`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      credentials: "include",
      body: JSON.stringify({ id_token: idToken }),
    });
    const data = await res.json();
    if (!data?.ok || !data?.user) {
      throw new Error(data?.detail || "Login failed");
    }
    setIsLoggedIn(true);
    const userData = { ...data.user, id: data.user.id };
    setUser(userData);
    
    // Check if profile is complete, if not redirect to profile edit
    if (!hasRequiredProfileInfo(userData)) {
      setView("profile");
    } else {
      setView("chat");
    }
  };

  // ---- Google Login (GIS) ----
  const ensureGoogleInitialized = () => {
    if (googleInitRef.current) return;
    if (!GOOGLE_CLIENT_ID) {
      throw new Error("Missing VITE_GOOGLE_CLIENT_ID in frontend/.env");
    }
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
    });
    googleInitRef.current = true;
  };

  const getGoogleIdTokenViaPrompt = async () => {
    ensureGoogleInitialized();

    return await new Promise((resolve, reject) => {
      // Re-initialize with our callback (safe; GIS overwrites)
      window.google.accounts.id.initialize({
        client_id: GOOGLE_CLIENT_ID,
        callback: (resp) => {
          if (resp?.credential) return resolve(resp.credential);
          return reject(new Error("No credential returned from Google"));
        },
        auto_select: false,
        cancel_on_tap_outside: false,
      });

      window.google.accounts.id.prompt((notification) => {
        // If prompt not displayed or skipped, we should surface a useful error
        if (notification.isNotDisplayed?.()) {
          return reject(
            new Error(
              `Google prompt not displayed: ${notification.getNotDisplayedReason?.() || "unknown"}`
            )
          );
        }
        if (notification.isSkippedMoment?.()) {
          return reject(
            new Error(
              `Google prompt skipped: ${notification.getSkippedReason?.() || "unknown"}`
            )
          );
        }
        if (notification.isDismissedMoment?.()) {
          return reject(
            new Error(
              `Google prompt dismissed: ${notification.getDismissedReason?.() || "unknown"}`
            )
          );
        }
      });
    });
  };

  // This is what LoginPage's "Login with Google" button calls (no args)
  const handleGoogleLoginClick = async () => {
    if (AUTH_BYPASS) {
      setIsLoggedIn(true);
      setUser({ id: "guest", name: "Guest" });
      setView("chat");
      return;
    }
    try {
      const idToken = await getGoogleIdTokenViaPrompt();
      await postIdTokenToBackend(idToken);
    } catch (e) {
      console.error("Google login failed:", e);
      alert(
        `Google login ไม่สำเร็จ: ${e?.message || e}\n\nทิป: ถ้าใช้ localhost ให้ลองเปิดผ่าน http://localhost:5173 และเปิด third-party cookies หรือปิด adblock ชั่วคราว`
      );
    }
  };

  const handleGetStarted = (promptOrQuery = "") => {
    const q = (promptOrQuery || "").toString();
    if (AUTH_BYPASS) {
      setIsLoggedIn(true);
      setUser({ id: "guest", name: "Guest" });
      setPendingPrompt(q);
      setView("chat");
      return;
    }
    if (!isLoggedIn) {
      setPendingPrompt(q);
      setView("login");
      return;
    }
    setPendingPrompt(q);
    setView("chat");
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
      // Update user state
      setUser({ ...user, ...data.user });
      // Redirect to chat
      setView("chat");
    } catch (error) {
      throw error;
    }
  };

  const handleCancelProfile = () => {
    // If user cancels and doesn't have required info, they can't proceed
    // But we'll let them go to chat anyway (they can edit later)
    if (hasRequiredProfileInfo(user)) {
      setView("chat");
    } else {
      // Still allow them to proceed, but warn them
      setView("chat");
    }
  };

  return (
    <div>
      {view === "home" && (
        <HomePage
          isLoggedIn={isLoggedIn}
          user={user}
          onSignIn={handleSignIn}
          onSignOut={handleSignOut}
          onGetStarted={handleGetStarted}
        />
      )}

      {view === "login" && (
        <LoginPage
          onLogin={handleSignIn}
          onGoogleLogin={handleGoogleLoginClick}
        />
      )}

      {view === "chat" && isLoggedIn && (
        <AITravelChat 
          user={user} 
          onLogout={handleSignOut} 
          onSignIn={handleSignIn}
          initialPrompt={pendingPrompt}
          onNavigateToBookings={() => setView("bookings")}
          onNavigateToFlights={() => setView("flights")}
          onNavigateToHotels={() => setView("hotels")}
          onNavigateToCarRentals={() => setView("car-rentals")}
        />
      )}

      {view === "chat" && !isLoggedIn && AUTH_BYPASS && (
        <AITravelChat 
          user={{ id: "guest", name: "Guest" }} 
          onLogout={handleSignOut} 
          onSignIn={handleSignIn}
          initialPrompt={pendingPrompt}
          onNavigateToBookings={() => setView("bookings")}
          onNavigateToFlights={() => setView("flights")}
          onNavigateToHotels={() => setView("hotels")}
          onNavigateToCarRentals={() => setView("car-rentals")}
        />
      )}

      {view === "profile" && isLoggedIn && (
        <UserProfileEditPage
          user={user}
          onSave={handleSaveProfile}
          onCancel={handleCancelProfile}
        />
      )}

      {view === "bookings" && (isLoggedIn || AUTH_BYPASS) && (
        <MyBookingsPage
          user={user || { id: "guest", name: "Guest" }}
          onBack={() => setView("chat")}
          onLogout={handleSignOut}
          onSignIn={handleSignIn}
        />
      )}

      {view === "flights" && (isLoggedIn || AUTH_BYPASS) && (
        <FlightsPage
          user={user || { id: "guest", name: "Guest" }}
          onLogout={handleSignOut}
          onSignIn={handleSignIn}
          onNavigateToBookings={() => setView("bookings")}
          onNavigateToAI={() => setView("chat")}
          onNavigateToFlights={() => setView("flights")}
          onNavigateToHotels={() => setView("hotels")}
          onNavigateToCarRentals={() => setView("car-rentals")}
        />
      )}

      {view === "hotels" && (isLoggedIn || AUTH_BYPASS) && (
        <HotelsPage
          user={user || { id: "guest", name: "Guest" }}
          onLogout={handleSignOut}
          onSignIn={handleSignIn}
          onNavigateToBookings={() => setView("bookings")}
          onNavigateToAI={() => setView("chat")}
          onNavigateToFlights={() => setView("flights")}
          onNavigateToCarRentals={() => setView("car-rentals")}
        />
      )}

      {view === "car-rentals" && (isLoggedIn || AUTH_BYPASS) && (
        <CarRentalsPage
          user={user || { id: "guest", name: "Guest" }}
          onLogout={handleSignOut}
          onSignIn={handleSignIn}
          onNavigateToBookings={() => setView("bookings")}
          onNavigateToAI={() => setView("chat")}
          onNavigateToFlights={() => setView("flights")}
          onNavigateToHotels={() => setView("hotels")}
        />
      )}
    </div>
  );
}

export default App;
