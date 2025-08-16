import React, { useRef, useState } from "react";
import { useRealtimeStore } from "../hooks/useRealtimeStore";

const BASE_URL = "http://localhost:8001";

async function uploadFile(sessionId: string, file: File): Promise<any> {
  const formData = new FormData();
  formData.append("file", file);
  const res = await fetch(`${BASE_URL}/api/files/upload?session_id=${sessionId}`, {
    method: "POST",
    body: formData,
  });
  if (!res.ok) throw new Error(await res.text());
  return res.json();
}

const FileUploadPanel: React.FC = () => {
  const sessionId = useRealtimeStore((s) => {
    const last = [...s.messages].reverse().find((m) => m.session_id);
    return last?.session_id || "";
  });
  const [uploading, setUploading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  async function handleFiles(files: FileList | null) {
    if (!files || !sessionId) return;
    setUploading(true);
    setError(null);
    try {
      for (let i = 0; i < files.length; i++) {
        await uploadFile(sessionId, files[i]);
      }
      // Optionally: refresh files in the store (could call listSessionFiles and update store)
      alert("Files uploaded!");
    } catch (e: any) {
      setError(e.message || "Upload failed");
    } finally {
      setUploading(false);
    }
  }

  function handleDrop(e: React.DragEvent) {
    e.preventDefault();
    handleFiles(e.dataTransfer.files);
  }

  function handleInputChange(e: React.ChangeEvent<HTMLInputElement>) {
    handleFiles(e.target.files);
  }

  return (
    <div style={{ padding: 16, border: "2px dashed #4f8cff", borderRadius: 8, margin: 8, textAlign: "center" }}
      onDrop={handleDrop}
      onDragOver={e => e.preventDefault()}
    >
      <div style={{ marginBottom: 8 }}>Drag & drop files here, or <button onClick={() => fileInputRef.current?.click()}>browse</button></div>
      <input
        type="file"
        multiple
        style={{ display: "none" }}
        ref={fileInputRef}
        onChange={handleInputChange}
      />
      {uploading && <div style={{ color: "#4f8cff" }}>Uploading...</div>}
      {error && <div style={{ color: "#a00" }}>{error}</div>}
    </div>
  );
};

export default FileUploadPanel; 