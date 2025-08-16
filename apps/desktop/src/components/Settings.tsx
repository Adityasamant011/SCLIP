import React, { useState } from "react";
import { usePreferences } from "../hooks/usePreferences";

const BASE_URL = "http://localhost:8001";

async function updatePreferencesOnBackend(prefs: any) {
  await fetch(`${BASE_URL}/api/preferences`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(prefs),
  });
}

const Settings: React.FC = () => {
  const { preferences, setPreferences } = usePreferences();
  const [saved, setSaved] = useState(false);

  if (!preferences) return <div>Loading preferences...</div>;

  async function handleChange(e: React.ChangeEvent<HTMLSelectElement>) {
    const newPrefs = { [e.target.name]: e.target.value };
    setPreferences(newPrefs);
    await updatePreferencesOnBackend({ ...preferences, ...newPrefs });
    setSaved(true);
    setTimeout(() => setSaved(false), 1200);
  }

  return (
    <div style={{ padding: 16 }}>
      <h3>User Preferences</h3>
      <label>
        Approval Mode:
        <select name="approval_mode" value={preferences.approval_mode} onChange={handleChange}>
          <option value="auto_approve">Auto Approve</option>
          <option value="major_steps_only">Major Steps Only</option>
          <option value="every_step">Every Step</option>
        </select>
      </label>
      {/* Add more settings as needed */}
      {saved && <span style={{ color: "#4f8cff", marginLeft: 8 }}>Saved!</span>}
    </div>
  );
};

export default Settings; 