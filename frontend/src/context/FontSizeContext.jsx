import React, { createContext, useContext, useState, useEffect } from 'react';

const FontSizeContext = createContext('medium');

export function FontSizeProvider({ user, children }) {
  const [fontSize, setFontSize] = useState(() => {
    if (typeof window !== 'undefined') {
      return localStorage.getItem('app_font_size') ?? 'medium';
    }
    return 'medium';
  });

  // Sync from user preferences (MongoDB)
  useEffect(() => {
    const pref = user?.preferences?.fontSize;
    if (pref && ['small', 'medium', 'large'].includes(pref)) {
      setFontSize(pref);
      localStorage.setItem('app_font_size', pref);
    }
  }, [user?.preferences?.fontSize]);

  // Listen for font size change events from SettingsPage
  useEffect(() => {
    const handler = (e) => {
      const val = e.detail ?? localStorage.getItem('app_font_size') ?? 'medium';
      if (['small', 'medium', 'large'].includes(val)) {
        setFontSize(val);
      }
    };
    window.addEventListener('app-font-size-change', handler);
    return () => window.removeEventListener('app-font-size-change', handler);
  }, []);

  return (
    <FontSizeContext.Provider value={fontSize}>
      {children}
    </FontSizeContext.Provider>
  );
}

export function useFontSize() {
  return useContext(FontSizeContext);
}
