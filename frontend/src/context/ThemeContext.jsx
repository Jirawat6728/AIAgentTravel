import React, { createContext, useContext, useMemo, useState, useEffect } from 'react';

const ThemeContext = createContext({ theme: 'light' });

// กลางวัน 06:00–18:00 = light, นอกนั้น = dark
function isTimeLight() {
  const hour = new Date().getHours();
  return hour >= 6 && hour < 18;
}

export function ThemeProvider({ user, children }) {
  const [timeDark, setTimeDark] = useState(() => !isTimeLight());

  const [localPref, setLocalPref] = useState(() =>
    typeof window !== 'undefined' ? (localStorage.getItem('app_theme') ?? 'light') : 'light'
  );

  // อัปเดตทุกนาที เพื่อให้เปลี่ยนธีมตรงเวลา
  useEffect(() => {
    const tick = () => setTimeDark(!isTimeLight());
    tick();
    const id = setInterval(tick, 60 * 1000);
    return () => clearInterval(id);
  }, []);

  useEffect(() => {
    const handleStorage = (e) => {
      if (e.key === 'app_theme') {
        setLocalPref(e.newValue ?? 'light');
      }
    };
    window.addEventListener('storage', handleStorage);
    return () => window.removeEventListener('storage', handleStorage);
  }, []);

  useEffect(() => {
    const handleThemeUpdate = (e) => {
      setLocalPref(e.detail ?? localStorage.getItem('app_theme') ?? 'light');
    };
    window.addEventListener('app-theme-change', handleThemeUpdate);
    return () => window.removeEventListener('app-theme-change', handleThemeUpdate);
  }, []);

  useEffect(() => {
    if (user?.preferences?.theme) {
      setLocalPref(user.preferences.theme);
      localStorage.setItem('app_theme', user.preferences.theme);
    }
  }, [user?.preferences?.theme]);

  const pref = localPref;
  const theme = useMemo(() => {
    if (pref === 'auto') return timeDark ? 'dark' : 'light';
    return pref === 'dark' ? 'dark' : 'light';
  }, [pref, timeDark]);

  const value = useMemo(() => ({ theme }), [theme]);

  return (
    <ThemeContext.Provider value={value}>
      {children}
    </ThemeContext.Provider>
  );
}

export function useTheme() {
  const ctx = useContext(ThemeContext);
  return ctx?.theme ?? 'light';
}
