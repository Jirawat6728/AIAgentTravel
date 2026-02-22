import React, { createContext, useContext, useState, useEffect, useCallback } from 'react';
import th from '../translations/th';
import en from '../translations/en';

const translations = { th, en };

const LanguageContext = createContext({ lang: 'th', t: (key) => key });

export function LanguageProvider({ user, children }) {
  const [lang, setLang] = useState(() => {
    if (typeof window !== 'undefined') {
      return localStorage.getItem('app_lang') ?? 'th';
    }
    return 'th';
  });

  // Sync from user preferences
  useEffect(() => {
    if (user?.preferences?.language) {
      setLang(user.preferences.language);
      localStorage.setItem('app_lang', user.preferences.language);
    }
  }, [user?.preferences?.language]);

  // Listen for language change events from SettingsPage
  useEffect(() => {
    const handler = (e) => {
      const newLang = e.detail ?? localStorage.getItem('app_lang') ?? 'th';
      setLang(newLang);
    };
    window.addEventListener('app-lang-change', handler);
    return () => window.removeEventListener('app-lang-change', handler);
  }, []);

  const t = useCallback((key) => {
    const dict = translations[lang] ?? translations.th;
    // Support dot notation: t('nav.flights')
    const parts = key.split('.');
    let val = dict;
    for (const part of parts) {
      val = val?.[part];
      if (val === undefined) break;
    }
    return val ?? key;
  }, [lang]);

  return (
    <LanguageContext.Provider value={{ lang, t }}>
      {children}
    </LanguageContext.Provider>
  );
}

export function useLanguage() {
  return useContext(LanguageContext);
}
