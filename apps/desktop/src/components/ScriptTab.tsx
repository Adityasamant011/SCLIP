import React, { useState, useEffect } from "react";
import { useRealtimeStore } from "../hooks/useRealtimeStore";

// Stub for script update API
async function updateScript(sessionId: string, scriptText: string) {
  // TODO: Implement real backend call (POST /api/scripts/update or similar)
  // For now, just simulate a delay
  await new Promise((res) => setTimeout(res, 500));
  return { success: true };
}

const ScriptTab: React.FC = () => {
  // Get the latest script from toolResults and scripts
  const script = useRealtimeStore((s) => {
    // First try to get from toolResults
    const scriptResult = [...s.toolResults].reverse().find(
      (msg) => msg.tool === "script_writer" && msg.result?.script_text
    );
    
    if (scriptResult?.result?.script_text) {
      console.log("Found script in toolResults:", scriptResult.result.script_text.substring(0, 100));
      return scriptResult.result.script_text;
    }
    
    // Fallback to scripts array
    if (s.scripts.length > 0) {
      const latestScript = s.scripts[s.scripts.length - 1];
      console.log("Found script in scripts array:", latestScript.content.substring(0, 100));
      return latestScript.content;
    }
    
    return "";
  });
  
  const scripts = useRealtimeStore((s) => s.scripts);
  const toolResults = useRealtimeStore((s) => s.toolResults);
  const isGenerating = useRealtimeStore((s) => 
    s.toolCalls.some(call => call.tool === "script_writer")
  );
  
  // Debug logging
  console.log("ScriptTab - script:", script ? script.substring(0, 100) + "..." : "No script");
  console.log("ScriptTab - scripts array length:", scripts.length);
  console.log("ScriptTab - toolResults length:", toolResults.length);
  console.log("ScriptTab - toolResults:", toolResults.map(tr => ({ tool: tr.tool, hasScript: !!tr.result?.script_text })));
  
  // Get sessionId for updates
  const sessionId = useRealtimeStore((s) => {
    const last = [...s.messages].reverse().find((m) => m.session_id);
    return last?.session_id || "";
  });
  
  // Local state for editing
  const [editValue, setEditValue] = useState(script);
  const [saving, setSaving] = useState(false);
  const [saved, setSaved] = useState(false);
  
  // Clear any existing script files from project files on mount
  const clearScriptFiles = useRealtimeStore((s) => s.clearScriptFiles);
  useEffect(() => {
    clearScriptFiles();
  }, [clearScriptFiles]);
  
  useEffect(() => { 
    if (script && script !== editValue) {
      console.log("Updating editValue with new script");
      setEditValue(script); 
    }
  }, [script, editValue]);

  async function handleSave() {
    if (!sessionId) return;
    setSaving(true);
    setSaved(false);
    await updateScript(sessionId, editValue);
    setSaving(false);
    setSaved(true);
    setTimeout(() => setSaved(false), 1200);
    // Optionally: update the store or show a confirmation
  }

  return (
    <div style={{ padding: 16, height: "100%", display: "flex", flexDirection: "column" }}>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 16 }}>
        <h3 style={{ margin: 0, color: "#fff" }}>Video Script</h3>
        {isGenerating && (
          <div style={{ display: "flex", alignItems: "center", color: "#4facfe" }}>
            <div style={{ 
              width: 16, 
              height: 16, 
              border: "2px solid #4facfe", 
              borderTop: "2px solid transparent", 
              borderRadius: "50%", 
              animation: "spin 1s linear infinite",
              marginRight: 8 
            }}></div>
            AI is generating script...
          </div>
        )}
      </div>
      
      {scripts.length > 0 && (
        <div style={{ marginBottom: 16 }}>
          <h4 style={{ color: "#fff", marginBottom: 8 }}>Script History</h4>
          <div style={{ display: "flex", gap: 8, overflowX: "auto", paddingBottom: 8 }}>
            {scripts.map((scriptItem, index) => (
              <button
                key={scriptItem.id}
                onClick={() => setEditValue(scriptItem.content)}
                style={{
                  padding: "8px 12px",
                  background: "linear-gradient(135deg, #667eea 0%, #764ba2 100%)",
                  border: "none",
                  borderRadius: "6px",
                  color: "white",
                  cursor: "pointer",
                  fontSize: "12px",
                  whiteSpace: "nowrap"
                }}
              >
                Script {index + 1} ({new Date(scriptItem.timestamp).toLocaleTimeString()})
              </button>
            ))}
          </div>
        </div>
      )}
      
      <div style={{ flex: 1, display: "flex", flexDirection: "column" }}>
        {editValue && (
          <div style={{ 
            marginBottom: 8, 
            padding: "8px 12px", 
            background: "linear-gradient(135deg, #51cf66 0%, #40c057 100%)", 
            borderRadius: "6px", 
            color: "white", 
            fontSize: "12px",
            display: "flex",
            alignItems: "center",
            gap: "8px"
          }}>
            <span>✅</span>
            <span>Script loaded successfully! You can edit it below.</span>
          </div>
        )}
        
      <textarea
        value={editValue}
        onChange={e => setEditValue(e.target.value)}
          placeholder={editValue ? "Edit your script here..." : "AI will generate your script here as it works..."}
          style={{ 
            flex: 1,
            width: "100%", 
            fontFamily: "monospace", 
            fontSize: 14,
            background: "#1a1a2e",
            color: "#fff",
            border: "1px solid #333",
            borderRadius: "8px",
            padding: "12px",
            resize: "none",
            outline: "none"
          }}
      />
        
        <div style={{ marginTop: 12, display: "flex", justifyContent: "space-between", alignItems: "center" }}>
          <div>
            <button 
              onClick={handleSave} 
              disabled={saving || !editValue}
              style={{
                padding: "8px 16px",
                background: saving ? "#666" : "linear-gradient(135deg, #4facfe 0%, #00f2fe 100%)",
                border: "none",
                borderRadius: "6px",
                color: "white",
                cursor: saving ? "not-allowed" : "pointer",
                fontSize: "14px"
              }}
            >
              {saving ? "Saving..." : "Save Script"}
            </button>
            {saved && (
              <span style={{ color: "#51cf66", marginLeft: 8, fontSize: "14px" }}>
                ✅ Saved!
              </span>
            )}
          </div>
          
          {editValue && (
            <div style={{ color: "#888", fontSize: "12px" }}>
              {editValue.split('\n').length} lines • {editValue.length} characters
            </div>
          )}
        </div>
      </div>
      
      {editValue && (
        <div style={{ marginTop: 16 }}>
          <h4 style={{ color: "#fff", marginBottom: 8 }}>Preview</h4>
          <pre style={{ 
            background: "#181818", 
            color: "#fff", 
            padding: 12, 
            borderRadius: 8,
            fontSize: "13px",
            lineHeight: "1.5",
            overflow: "auto",
            maxHeight: "200px"
          }}>
            {editValue}
          </pre>
        </div>
      )}
    </div>
  );
};

export default ScriptTab; 