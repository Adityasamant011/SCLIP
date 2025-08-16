import { useState, useEffect } from "react";
import { UserPreferences } from "../types/preferences";

const PREFS_KEY = "sclip_user_preferences";

export function usePreferences() {
  const [preferences, setPreferences] = useState<UserPreferences | null>(null);

  // Load from localStorage on mount
  useEffect(() => {
    const raw = localStorage.getItem(PREFS_KEY);
    if (raw) setPreferences(JSON.parse(raw));
  }, []);

  // Save to localStorage on change
  useEffect(() => {
    if (preferences) localStorage.setItem(PREFS_KEY, JSON.stringify(preferences));
  }, [preferences]);

  function updatePreferences(newPrefs: Partial<UserPreferences>) {
    setPreferences((prev) => ({ ...prev, ...newPrefs } as UserPreferences));
  }

  return { preferences, setPreferences: updatePreferences };
} 