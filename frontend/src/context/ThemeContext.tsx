import React, { createContext, useContext, useEffect, useState } from 'react';

export type ThemeMode = 'light' | 'dark' | 'system';

const THEME_STORAGE_KEY = 'placement_theme';
const PREFS_STORAGE_KEY = 'placement_ui_preferences';

interface UIPreferences {
  compactMode: boolean;
  reducedMotion: boolean;
  confirmActions: boolean;
}

interface ThemeContextType {
  theme: ThemeMode;
  resolvedTheme: 'light' | 'dark';
  setTheme: (mode: ThemeMode) => void;
  toggleTheme: () => void;
  compactMode: boolean;
  setCompactMode: (value: boolean) => void;
  reducedMotion: boolean;
  setReducedMotion: (value: boolean) => void;
  confirmActions: boolean;
  setConfirmActions: (value: boolean) => void;
}

const ThemeContext = createContext<ThemeContextType | undefined>(undefined);

const getStoredTheme = (): ThemeMode => {
  try {
    const raw = localStorage.getItem(THEME_STORAGE_KEY);
    if (raw === 'light' || raw === 'dark' || raw === 'system') {
      return raw;
    }
  } catch {
    // Ignore storage access errors
  }
  return 'light';
};

const getStoredPrefs = (): UIPreferences => {
  try {
    const raw = localStorage.getItem(PREFS_STORAGE_KEY);
    if (raw) {
      const parsed = JSON.parse(raw);
      return {
        compactMode: Boolean(parsed.compactMode),
        reducedMotion: Boolean(parsed.reducedMotion),
        confirmActions: parsed.confirmActions !== undefined ? Boolean(parsed.confirmActions) : true,
      };
    }
  } catch {
    // Ignore parse errors
  }
  return {
    compactMode: false,
    reducedMotion: false,
    confirmActions: true,
  };
};

const resolveSystemTheme = (): 'light' | 'dark' => {
  if (typeof window !== 'undefined' && window.matchMedia?.('(prefers-color-scheme: dark)').matches) {
    return 'dark';
  }
  return 'light';
};

export const ThemeProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [theme, setThemeState] = useState<ThemeMode>(getStoredTheme);
  const [systemTheme, setSystemTheme] = useState<'light' | 'dark'>(resolveSystemTheme);
  const [prefs, setPrefs] = useState<UIPreferences>(getStoredPrefs);

  const resolvedTheme: 'light' | 'dark' = theme === 'system' ? systemTheme : theme;

  // Track OS color-scheme changes when in system mode
  useEffect(() => {
    if (!window.matchMedia) return;
    const media = window.matchMedia('(prefers-color-scheme: dark)');
    const onChange = (e: MediaQueryListEvent) => setSystemTheme(e.matches ? 'dark' : 'light');
    media.addEventListener('change', onChange);
    return () => media.removeEventListener('change', onChange);
  }, []);

  // Apply theme class to <html>
  useEffect(() => {
    const root = document.documentElement;
    root.classList.toggle('dark', resolvedTheme === 'dark');
    root.style.colorScheme = resolvedTheme;
    try {
      localStorage.setItem(THEME_STORAGE_KEY, theme);
    } catch {
      // Ignore storage failures
    }
  }, [theme, resolvedTheme]);

  // Apply UI preference classes to <html>
  useEffect(() => {
    const root = document.documentElement;
    root.classList.toggle('compact-ui', prefs.compactMode);
    root.classList.toggle('reduce-motion', prefs.reducedMotion);
    try {
      localStorage.setItem(PREFS_STORAGE_KEY, JSON.stringify(prefs));
    } catch {
      // Ignore storage failures
    }
  }, [prefs]);

  const setTheme = (mode: ThemeMode) => {
    setThemeState(mode);
  };

  const toggleTheme = () => {
    setThemeState((prev) => {
      const current = prev === 'system' ? systemTheme : prev;
      return current === 'dark' ? 'light' : 'dark';
    });
  };

  const setCompactMode = (compactMode: boolean) => setPrefs((p) => ({ ...p, compactMode }));
  const setReducedMotion = (reducedMotion: boolean) => setPrefs((p) => ({ ...p, reducedMotion }));
  const setConfirmActions = (confirmActions: boolean) => setPrefs((p) => ({ ...p, confirmActions }));

  return (
    <ThemeContext.Provider
      value={{
        theme,
        resolvedTheme,
        setTheme,
        toggleTheme,
        compactMode: prefs.compactMode,
        setCompactMode,
        reducedMotion: prefs.reducedMotion,
        setReducedMotion,
        confirmActions: prefs.confirmActions,
        setConfirmActions,
      }}
    >
      {children}
    </ThemeContext.Provider>
  );
};

export const useTheme = (): ThemeContextType => {
  const ctx = useContext(ThemeContext);
  if (!ctx) {
    throw new Error('useTheme must be used within a ThemeProvider');
  }
  return ctx;
};

