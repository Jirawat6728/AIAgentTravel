import React, { createContext, useContext, useMemo, useState, useEffect } from 'react';

const ThemeContext = createContext({ theme: 'light' });

export function ThemeProvider({ user, children }) {
  const [systemDark, setSystemDark] = useState(() =>
    typeof window !== 'undefined' && window.matchMedia?.('(prefers-color-scheme: dark)')?.matches
  );

  useEffect(() => {
    const mq = window.matchMedia?.('(prefers-color-scheme: dark)');
    if (!mq) return;
    const handler = (e) => setSystemDark(e.matches);
    mq.addEventListener('change', handler);
    return () => mq.removeEventListener('change', handler);
  }, []);

  const pref = user?.preferences?.theme ?? localStorage.getItem('app_theme') ?? 'light';
  const theme = useMemo(() => {
    if (pref === 'auto') return systemDark ? 'dark' : 'light';
    return pref === 'dark' ? 'dark' : 'light';
  }, [pref, systemDark]);

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
