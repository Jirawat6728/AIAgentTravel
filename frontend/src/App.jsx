import React, { useEffect, useState, useCallback, useRef } from "react";
import LoginPage from "./components/LoginPage.jsx";
import AITravelChat from "./components/AITravelChat.jsx";
import HomePage from "./components/HomePage.jsx";

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || "http://localhost:8000";
const GOOGLE_CLIENT_ID = import.meta.env.VITE_GOOGLE_CLIENT_ID || "";
// Temporary: bypass auth (guest mode). Set VITE_AUTH_BYPASS=0 to re-enable real auth.
const AUTH_BYPASS = (import.meta.env.VITE_AUTH_BYPASS || "1").toString() === "1";

function App() {
  const [view, setView] = useState("home"); // 'home' | 'login' | 'chat'
  const [isLoggedIn, setIsLoggedIn] = useState(AUTH_BYPASS);
  const [user, setUser] = useState(AUTH_BYPASS ? { id: "guest", name: "Guest" } : null);
  const [pendingPrompt, setPendingPrompt] = useState("");

  const googleInitRef = useRef(false);

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
      } else {
        setIsLoggedIn(false);
        setUser(null);
      }
    } catch (e) {
      // If backend is down or CORS fails, just treat as logged out.
      setIsLoggedIn(false);
      setUser(null);
    }
  }, []);

  useEffect(() => {
    refreshMe();
  }, [refreshMe]);

  const goHome = () => setView("home");

  const handleSignIn = () => {
    if (AUTH_BYPASS) {
      setIsLoggedIn(true);
      setUser({ id: "guest", name: "Guest" });
      setView("chat");
      return;
    }
    setView("login");
  };

  const handleSignOut = async () => {
    if (AUTH_BYPASS) {
      // In guest mode, "sign out" just returns home.
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
    setUser({ ...data.user, id: data.user.id });
    setView("chat");
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
      cancel_on_tap_outside: true,
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
        cancel_on_tap_outside: true,
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
      // No Google login for now: bypass straight to chat.
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
    setView("chat");
  };

  return (
    <div>
      {view === "home" && (
        <HomePage
          isLoggedIn={isLoggedIn}
          onSignIn={handleSignIn}
          onSignOut={handleSignOut}
          onGetStarted={handleGetStarted}
        />
      )}

      {view === "login" && (
        <LoginPage
          onBack={goHome}
          onGoogleLogin={handleGoogleLoginClick}
          onLoginSuccess={handleLoginSuccess}
        />
      )}

      {view === "chat" && isLoggedIn && (
        <AITravelChat user={user} onLogout={handleSignOut} initialPrompt={pendingPrompt} />
      )}

      {view === "chat" && !isLoggedIn && AUTH_BYPASS && (
        <AITravelChat user={{ id: "guest", name: "Guest" }} onLogout={handleSignOut} initialPrompt={pendingPrompt} />
      )}
    </div>
  );
}

export default App;
